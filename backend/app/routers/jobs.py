from typing import List, Optional
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from ..database import get_db
from ..models import Job, JobService, JobPart, Invoice, User
from ..schemas import JobCreate, JobUpdate, JobResponse, InvoiceResponse
from ..auth import get_current_user, require_superadmin
import uuid

router = APIRouter(tags=["jobs"])

TERMINAL_STATUSES = {"completed", "invoiced", "delivered"}


def _load_options():
    return [
        selectinload(Job.services),
        selectinload(Job.parts),
        selectinload(Job.customer),
        selectinload(Job.vehicle),
        selectinload(Job.staff),
    ]


async def _get_job_or_404(db: AsyncSession, job_id: str) -> Job:
    result = await db.execute(
        select(Job).options(*_load_options()).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = None,
    department: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Job).options(*_load_options())
    if status:
        q = q.where(Job.status == status)
    if department:
        q = q.where(Job.department == department)
    if search:
        # Join customer for name search
        from ..models import Customer, Vehicle
        q = q.join(Customer, Job.customer_id == Customer.id).join(
            Vehicle, Job.vehicle_id == Vehicle.id
        ).where(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Vehicle.plate.ilike(f"%{search}%"),
                Vehicle.make.ilike(f"%{search}%"),
                Vehicle.model.ilike(f"%{search}%"),
            )
        )
    result = await db.execute(q.order_by(Job.created_at.desc()))
    return result.scalars().all()


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_job_or_404(db, job_id)


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count_result = await db.execute(select(func.count()).select_from(Job))
    job_num = f"JOB-{count_result.scalar() + 1:05d}"

    job_data = data.model_dump(exclude={"services", "parts"})
    job = Job(**job_data, job_num=job_num)
    db.add(job)
    await db.flush()

    for svc in data.services:
        db.add(JobService(job_id=job.id, **svc.model_dump()))
    for part in data.parts:
        db.add(JobPart(job_id=job.id, **part.model_dump()))

    await db.commit()
    return await _get_job_or_404(db, job.id)


@router.put("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    data: JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    update_data = data.model_dump(exclude_unset=True, exclude={"services", "parts"})

    # Auto-set completed_at when transitioning to terminal status
    new_status = update_data.get("status")
    if new_status and new_status in TERMINAL_STATUSES and job.completed_at is None:
        job.completed_at = date.today()

    for field, value in update_data.items():
        setattr(job, field, value)

    # Replace services if provided
    if data.services is not None:
        await db.execute(
            select(JobService).where(JobService.job_id == job_id)
        )
        # Delete existing
        existing_svcs = await db.execute(select(JobService).where(JobService.job_id == job_id))
        for svc in existing_svcs.scalars().all():
            await db.delete(svc)
        for svc in data.services:
            db.add(JobService(job_id=job_id, **svc.model_dump()))

    # Replace parts if provided
    if data.parts is not None:
        existing_parts = await db.execute(select(JobPart).where(JobPart.job_id == job_id))
        for part in existing_parts.scalars().all():
            await db.delete(part)
        for part in data.parts:
            db.add(JobPart(job_id=job_id, **part.model_dump()))

    await db.commit()
    return await _get_job_or_404(db, job_id)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    await db.commit()


@router.post("/jobs/{job_id}/invoice", response_model=InvoiceResponse)
async def generate_invoice_from_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_job_or_404(db, job_id)

    # Check if invoice already exists
    existing = await db.execute(select(Invoice).where(Invoice.job_id == job_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invoice already exists for this job")

    # Calculate subtotal, VAT and grand total
    services_total = sum(Decimal(str(s.rate)) for s in job.services)
    parts_total = sum(Decimal(str(p.qty)) * Decimal(str(p.rate)) for p in job.parts)
    subtotal = max(Decimal("0.00"), services_total + parts_total - Decimal(str(job.discount)))
    tax_rate = Decimal("5.00")
    tax_amount = (subtotal * tax_rate / 100).quantize(Decimal("0.01"))
    grand_total = subtotal + tax_amount

    # Generate invoice number
    count_result = await db.execute(select(func.count()).select_from(Invoice))
    inv_count = count_result.scalar() + 1
    inv_num = f"INV-{inv_count:05d}"

    invoice = Invoice(
        id=str(uuid.uuid4()),
        job_id=job_id,
        customer_id=job.customer_id,
        vehicle_id=job.vehicle_id,
        inv_num=inv_num,
        date_issued=date.today(),
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        grand_total=grand_total,
        paid=False,
    )
    db.add(invoice)

    # Update job status
    job.status = "invoiced"
    if job.completed_at is None:
        job.completed_at = date.today()

    await db.commit()

    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.job).options(*_load_options()),
            selectinload(Invoice.customer),
            selectinload(Invoice.vehicle),
        )
        .where(Invoice.id == invoice.id)
    )
    return result.scalar_one()
