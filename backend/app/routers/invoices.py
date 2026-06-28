from typing import List, Optional
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from ..database import get_db
from ..models import Invoice, Job, JobService, JobPart, User
from ..schemas import InvoiceCreate, InvoiceResponse
from ..auth import get_current_user, require_superadmin
from .jobs import _load_options as job_load_options
import uuid

router = APIRouter(tags=["invoices"])


def _invoice_options():
    return [
        selectinload(Invoice.job).options(*job_load_options()),
        selectinload(Invoice.customer),
        selectinload(Invoice.vehicle),
    ]


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Invoice).options(*_invoice_options()).order_by(Invoice.created_at.desc())
    )
    return result.scalars().all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Invoice).options(*_invoice_options()).where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Load job with services and parts
    from .jobs import _load_options
    result = await db.execute(
        select(Job).options(*_load_options()).where(Job.id == data.job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if invoice already exists
    existing = await db.execute(select(Invoice).where(Invoice.job_id == data.job_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invoice already exists for this job")

    services_total = sum(Decimal(str(s.rate)) for s in job.services)
    parts_total = sum(Decimal(str(p.qty)) * Decimal(str(p.rate)) for p in job.parts)
    subtotal = services_total + parts_total - Decimal(str(job.discount))

    count_result = await db.execute(select(func.count()).select_from(Invoice))
    inv_count = count_result.scalar() + 1
    inv_num = f"INV-{inv_count:05d}"

    invoice = Invoice(
        id=str(uuid.uuid4()),
        job_id=data.job_id,
        customer_id=job.customer_id,
        vehicle_id=job.vehicle_id,
        inv_num=inv_num,
        date_issued=data.date_issued or date.today(),
        subtotal=subtotal,
        paid=False,
    )
    db.add(invoice)
    job.status = "invoiced"
    if job.completed_at is None:
        job.completed_at = date.today()

    await db.commit()

    result = await db.execute(
        select(Invoice).options(*_invoice_options()).where(Invoice.id == invoice.id)
    )
    return result.scalar_one()


class MarkPaidRequest(BaseModel):
    payment_method: Optional[str] = None

@router.put("/invoices/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: str,
    body: MarkPaidRequest = MarkPaidRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice.paid = True
    invoice.payment_method = body.payment_method
    invoice.date_paid = date.today()
    await db.commit()
    result = await db.execute(
        select(Invoice).options(*_invoice_options()).where(Invoice.id == invoice_id)
    )
    return result.scalar_one()


@router.delete("/invoices/{invoice_id}", status_code=204)
async def delete_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Reset job status
    job_result = await db.execute(select(Job).where(Job.id == invoice.job_id))
    job = job_result.scalar_one_or_none()
    if job:
        job.status = "completed"

    await db.delete(invoice)
    await db.commit()
