from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract
from ..database import get_db
from ..models import Job, Invoice, Expense, PurchaseBill, FixedCost, Inventory, Staff, JobService, JobPart
from ..schemas import DashboardStats, PaymentAlert
from ..auth import get_current_user
from ..models import User

router = APIRouter(tags=["reports"])

TERMINAL_STATUSES = {"completed", "invoiced", "delivered"}
OPEN_STATUSES = {"pending", "inprogress", "waitingparts", "qc", "ready"}


@router.get("/reports/dashboard", response_model=DashboardStats)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    month_start = today.replace(day=1)
    next_30 = today + timedelta(days=30)

    # Revenue from paid invoices
    rev_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.subtotal), 0)).where(Invoice.paid == True)
    )
    total_revenue = Decimal(str(rev_result.scalar()))

    # Revenue today
    rev_today_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.subtotal), 0)).where(
            and_(Invoice.paid == True, Invoice.date_issued == today)
        )
    )
    revenue_today = Decimal(str(rev_today_result.scalar()))

    # Revenue this month
    rev_month_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.subtotal), 0)).where(
            and_(
                Invoice.paid == True,
                Invoice.date_issued >= month_start,
                Invoice.date_issued <= today,
            )
        )
    )
    revenue_this_month = Decimal(str(rev_month_result.scalar()))

    # Total expenses
    exp_result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0))
    )
    total_expenses = Decimal(str(exp_result.scalar()))

    net_profit = total_revenue - total_expenses

    # Open jobs count
    open_jobs_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.status.in_(OPEN_STATUSES))
    )
    open_jobs = open_jobs_result.scalar()

    # Urgent jobs
    urgent_result = await db.execute(
        select(func.count()).select_from(Job).where(
            and_(Job.priority == "urgent", Job.status.in_(OPEN_STATUSES))
        )
    )
    urgent_jobs = urgent_result.scalar()

    # Overdue jobs (date_out < today, not terminal)
    overdue_result = await db.execute(
        select(Job).where(
            and_(
                Job.date_out < today,
                Job.date_out.isnot(None),
                Job.status.notin_(TERMINAL_STATUSES),
            )
        )
    )
    overdue_jobs_list = overdue_result.scalars().all()
    overdue_jobs = [
        {
            "id": j.id,
            "status": j.status,
            "date_out": str(j.date_out),
            "customer_id": j.customer_id,
            "vehicle_id": j.vehicle_id,
        }
        for j in overdue_jobs_list
    ]

    # Ready jobs
    ready_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.status == "ready")
    )
    ready_jobs = ready_result.scalar()

    # Waiting parts
    wp_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.status == "waitingparts")
    )
    waiting_parts_jobs = wp_result.scalar()

    # Completed this month
    ctm_result = await db.execute(
        select(func.count()).select_from(Job).where(
            and_(
                Job.status.in_(TERMINAL_STATUSES),
                Job.completed_at >= month_start,
                Job.completed_at <= today,
            )
        )
    )
    completed_this_month = ctm_result.scalar()

    # Total completed
    tc_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.status.in_(TERMINAL_STATUSES))
    )
    total_completed = tc_result.scalar()

    # Unpaid invoices
    unpaid_result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.subtotal), 0),
            func.count(),
        ).where(Invoice.paid == False)
    )
    unpaid_row = unpaid_result.one()
    unpaid_invoices_amount = Decimal(str(unpaid_row[0]))
    unpaid_invoices_count = unpaid_row[1]

    # Supplier due amount (unpaid bills)
    sup_due_result = await db.execute(
        select(func.coalesce(func.sum(
            select(func.sum(
                # We'll compute this differently using a subquery join
            ))
        ), 0))
    )
    # Simplified: sum amounts via bill items
    from sqlalchemy import text
    sup_amount_result = await db.execute(
        text("""
            SELECT COALESCE(SUM(i.qty * i.cost_price), 0), COUNT(DISTINCT b.id)
            FROM purchase_bills b
            JOIN purchase_bill_items i ON i.bill_id = b.id
            WHERE b.paid = false AND b.due_date IS NOT NULL AND b.due_date < :today
        """),
        {"today": today},
    )
    sup_row = sup_amount_result.one()
    supplier_due_amount = Decimal(str(sup_row[0]))
    supplier_overdue_count = sup_row[1]

    # Fixed cost due/overdue next 30 days
    fc_result = await db.execute(
        select(FixedCost).where(
            and_(
                FixedCost.active == True,
                FixedCost.next_due_date.isnot(None),
                FixedCost.next_due_date <= next_30,
            )
        )
    )
    fc_items = fc_result.scalars().all()
    fc_due_amount = sum(Decimal(str(f.amount)) for f in fc_items)
    fc_overdue_count = sum(1 for f in fc_items if f.next_due_date < today)

    # Payment alerts
    payment_alerts = []
    # Bills
    bills_result = await db.execute(
        select(PurchaseBill).where(
            and_(PurchaseBill.paid == False, PurchaseBill.due_date.isnot(None))
        )
    )
    bills = bills_result.scalars().all()
    for b in bills:
        if b.due_date and b.due_date <= next_30:
            days = (b.due_date - today).days
            # Need total amount from items
            items_result = await db.execute(
                text("SELECT COALESCE(SUM(qty * cost_price), 0) FROM purchase_bill_items WHERE bill_id = :bid"),
                {"bid": b.id},
            )
            bill_total = Decimal(str(items_result.scalar()))
            payment_alerts.append(
                PaymentAlert(
                    type="bill",
                    id=b.id,
                    name=f"Bill {b.bill_no or b.id[:8]}",
                    amount=bill_total,
                    due_date=b.due_date,
                    overdue=b.due_date < today,
                    days_until_due=days,
                )
            )

    for f in fc_items:
        if f.next_due_date:
            days = (f.next_due_date - today).days
            payment_alerts.append(
                PaymentAlert(
                    type="fixed_cost",
                    id=f.id,
                    name=f.name,
                    amount=Decimal(str(f.amount)),
                    due_date=f.next_due_date,
                    overdue=f.next_due_date < today,
                    days_until_due=days,
                )
            )

    # Revenue by month (last 6 months)
    revenue_by_month: dict = {}
    expenses_by_month: dict = {}
    for i in range(5, -1, -1):
        d = today - timedelta(days=i * 30)
        key = d.strftime("%Y-%m")
        m_start = d.replace(day=1)
        if d.month == 12:
            m_end = d.replace(year=d.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = d.replace(month=d.month + 1, day=1) - timedelta(days=1)

        r = await db.execute(
            select(func.coalesce(func.sum(Invoice.subtotal), 0)).where(
                and_(Invoice.paid == True, Invoice.date_issued >= m_start, Invoice.date_issued <= m_end)
            )
        )
        revenue_by_month[key] = float(r.scalar())

        e = await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                and_(Expense.date >= m_start, Expense.date <= m_end)
            )
        )
        expenses_by_month[key] = float(e.scalar())

    # Dept revenue this month
    dept_result = await db.execute(
        select(Job.department, func.coalesce(func.sum(Invoice.subtotal), 0))
        .join(Invoice, Invoice.job_id == Job.id)
        .where(
            and_(
                Invoice.paid == True,
                Invoice.date_issued >= month_start,
                Invoice.date_issued <= today,
                Job.department.isnot(None),
            )
        )
        .group_by(Job.department)
    )
    dept_revenue = {row[0]: float(row[1]) for row in dept_result.all()}

    return DashboardStats(
        total_revenue=total_revenue,
        revenue_today=revenue_today,
        revenue_this_month=revenue_this_month,
        total_expenses=total_expenses,
        net_profit=net_profit,
        open_jobs=open_jobs,
        urgent_jobs=urgent_jobs,
        overdue_jobs=overdue_jobs,
        ready_jobs=ready_jobs,
        waiting_parts_jobs=waiting_parts_jobs,
        completed_this_month=completed_this_month,
        total_completed=total_completed,
        unpaid_invoices_amount=unpaid_invoices_amount,
        unpaid_invoices_count=unpaid_invoices_count,
        supplier_due_amount=supplier_due_amount,
        supplier_overdue_count=supplier_overdue_count,
        fc_due_amount=fc_due_amount,
        fc_overdue_count=fc_overdue_count,
        payment_alerts=payment_alerts,
        revenue_by_month=revenue_by_month,
        expenses_by_month=expenses_by_month,
        dept_revenue=dept_revenue,
    )


@router.get("/reports/tax")
async def tax_report(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    period_start = date(year, month, 1)
    period_end = date(year, month, last_day)

    VAT_RATE = Decimal("0.05")

    # Invoices for period
    inv_result = await db.execute(
        select(Invoice).where(
            and_(Invoice.date_issued >= period_start, Invoice.date_issued <= period_end)
        )
    )
    invoices = inv_result.scalars().all()
    invoice_total = sum(Decimal(str(i.subtotal)) for i in invoices)
    output_vat = invoice_total * VAT_RATE

    # Expenses for period (exclude Salaries, Rent for input VAT)
    exp_result = await db.execute(
        select(Expense).where(
            and_(Expense.date >= period_start, Expense.date <= period_end)
        )
    )
    expenses = exp_result.scalars().all()
    total_expenses = sum(Decimal(str(e.amount)) for e in expenses)

    vat_eligible_expenses = sum(
        Decimal(str(e.amount))
        for e in expenses
        if e.category not in ("Salaries", "Rent")
    )
    input_vat = vat_eligible_expenses * VAT_RATE
    net_vat = output_vat - input_vat

    # Expense breakdown by category
    exp_by_cat: dict = {}
    for e in expenses:
        cat = e.category or "Uncategorized"
        exp_by_cat[cat] = float(Decimal(str(exp_by_cat.get(cat, 0))) + Decimal(str(e.amount)))

    return {
        "period": f"{year}-{month:02d}",
        "invoices": [{"id": i.id, "inv_num": i.inv_num, "subtotal": float(i.subtotal), "date_issued": str(i.date_issued)} for i in invoices],
        "invoice_total": float(invoice_total),
        "output_vat": float(output_vat),
        "vat_eligible_expenses": float(vat_eligible_expenses),
        "input_vat": float(input_vat),
        "net_vat": float(net_vat),
        "total_expenses": float(total_expenses),
        "expense_breakdown": exp_by_cat,
    }


@router.get("/reports/profitability")
async def profitability_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import text

    # Monthly P&L (last 12 months)
    monthly_pnl_result = await db.execute(
        text("""
            SELECT
                TO_CHAR(date_issued, 'YYYY-MM') as month,
                COALESCE(SUM(subtotal), 0) as revenue
            FROM invoices
            WHERE paid = true
            AND date_issued >= NOW() - INTERVAL '12 months'
            GROUP BY month
            ORDER BY month
        """)
    )
    monthly_revenue = {row[0]: float(row[1]) for row in monthly_pnl_result.all()}

    monthly_exp_result = await db.execute(
        text("""
            SELECT
                TO_CHAR(date, 'YYYY-MM') as month,
                COALESCE(SUM(amount), 0) as expenses
            FROM expenses
            WHERE date >= NOW() - INTERVAL '12 months'
            GROUP BY month
            ORDER BY month
        """)
    )
    monthly_expenses = {row[0]: float(row[1]) for row in monthly_exp_result.all()}

    all_months = sorted(set(list(monthly_revenue.keys()) + list(monthly_expenses.keys())))
    monthly_pnl = [
        {
            "month": m,
            "revenue": monthly_revenue.get(m, 0),
            "expenses": monthly_expenses.get(m, 0),
            "profit": monthly_revenue.get(m, 0) - monthly_expenses.get(m, 0),
        }
        for m in all_months
    ]

    # Staff productivity
    staff_result = await db.execute(
        text("""
            SELECT s.name, COUNT(j.id) as jobs_count,
                   COALESCE(SUM(inv.subtotal), 0) as revenue
            FROM staff s
            LEFT JOIN jobs j ON j.staff_id = s.id
            LEFT JOIN invoices inv ON inv.job_id = j.id AND inv.paid = true
            GROUP BY s.id, s.name
            ORDER BY revenue DESC
        """)
    )
    staff_productivity = [
        {"name": row[0], "jobs_count": row[1], "revenue": float(row[2])}
        for row in staff_result.all()
    ]

    # Dept revenue all-time
    dept_result = await db.execute(
        text("""
            SELECT j.department, COALESCE(SUM(inv.subtotal), 0) as revenue, COUNT(j.id) as jobs
            FROM jobs j
            JOIN invoices inv ON inv.job_id = j.id AND inv.paid = true
            WHERE j.department IS NOT NULL
            GROUP BY j.department
            ORDER BY revenue DESC
        """)
    )
    dept_revenue = [
        {"department": row[0], "revenue": float(row[1]), "jobs": row[2]}
        for row in dept_result.all()
    ]

    return {
        "monthly_pnl": monthly_pnl,
        "staff_productivity": staff_productivity,
        "dept_revenue": dept_revenue,
    }


@router.get("/reports/inventory")
async def inventory_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Inventory).order_by(Inventory.name))
    items = result.scalars().all()

    low_stock = [i for i in items if Decimal(str(i.qty)) <= Decimal(str(i.reorder_qty))]
    reorder_list = [i for i in low_stock if Decimal(str(i.reorder_qty)) > 0]

    total_value = sum(Decimal(str(i.qty)) * Decimal(str(i.cost_price)) for i in items)

    return {
        "total_items": len(items),
        "total_value": float(total_value),
        "low_stock_count": len(low_stock),
        "low_stock": [
            {
                "id": i.id,
                "name": i.name,
                "part_no": i.part_no,
                "qty": float(i.qty),
                "reorder_qty": float(i.reorder_qty),
                "unit": i.unit,
            }
            for i in low_stock
        ],
        "reorder_list": [
            {
                "id": i.id,
                "name": i.name,
                "part_no": i.part_no,
                "qty": float(i.qty),
                "reorder_qty": float(i.reorder_qty),
                "cost_price": float(i.cost_price),
            }
            for i in reorder_list
        ],
    }


@router.get("/reports/job-duration")
async def job_duration_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import text

    dept_result = await db.execute(
        text("""
            SELECT department,
                   AVG(EXTRACT(EPOCH FROM (completed_at - date_in)) / 86400) as avg_days,
                   COUNT(*) as job_count
            FROM jobs
            WHERE completed_at IS NOT NULL AND date_in IS NOT NULL AND department IS NOT NULL
            GROUP BY department
            ORDER BY avg_days
        """)
    )
    by_department = [
        {"department": row[0], "avg_days": round(float(row[1]) if row[1] else 0, 2), "job_count": row[2]}
        for row in dept_result.all()
    ]

    tech_result = await db.execute(
        text("""
            SELECT s.name,
                   AVG(EXTRACT(EPOCH FROM (j.completed_at - j.date_in)) / 86400) as avg_days,
                   COUNT(j.id) as job_count
            FROM jobs j
            JOIN staff s ON s.id = j.staff_id
            WHERE j.completed_at IS NOT NULL AND j.date_in IS NOT NULL
            GROUP BY s.id, s.name
            ORDER BY avg_days
        """)
    )
    by_technician = [
        {"technician": row[0], "avg_days": round(float(row[1]) if row[1] else 0, 2), "job_count": row[2]}
        for row in tech_result.all()
    ]

    return {
        "by_department": by_department,
        "by_technician": by_technician,
    }
