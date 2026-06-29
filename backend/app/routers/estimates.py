from typing import List, Optional
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from ..database import get_db
from ..models import Estimate, EstimateService, EstimatePart, Job, JobService, JobPart, User
from ..auth import get_current_user, require_superadmin
from ..schemas import JobCreate
import uuid

router = APIRouter(tags=["estimates"])

TAX_RATE = Decimal("5.00")


class EstimateServiceIn(BaseModel):
    description: str
    department: Optional[str] = None
    rate: Decimal


class EstimatePartIn(BaseModel):
    description: str
    part_no: Optional[str] = None
    qty: Decimal
    rate: Decimal


class EstimateServiceOut(EstimateServiceIn):
    id: str
    estimate_id: str
    class Config: from_attributes = True


class EstimatePartOut(EstimatePartIn):
    id: str
    estimate_id: str
    class Config: from_attributes = True


class EstimateCreate(BaseModel):
    customer_id: str
    vehicle_id: str
    staff_id: Optional[str] = None
    date_issued: date
    valid_until: Optional[date] = None
    notes: Optional[str] = None
    discount: Decimal = Decimal("0")
    services: List[EstimateServiceIn] = []
    parts: List[EstimatePartIn] = []


class EstimateUpdate(BaseModel):
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    staff_id: Optional[str] = None
    date_issued: Optional[date] = None
    valid_until: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    discount: Optional[Decimal] = None
    services: Optional[List[EstimateServiceIn]] = None
    parts: Optional[List[EstimatePartIn]] = None


class EstimateOut(BaseModel):
    id: str
    customer_id: str
    vehicle_id: str
    staff_id: Optional[str]
    est_num: str
    date_issued: date
    valid_until: Optional[date]
    status: str
    notes: Optional[str]
    discount: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    services: List[EstimateServiceOut] = []
    parts: List[EstimatePartOut] = []
    customer: Optional[dict] = None
    vehicle: Optional[dict] = None
    class Config: from_attributes = True


def _load_opts():
    return [
        selectinload(Estimate.services),
        selectinload(Estimate.parts),
        selectinload(Estimate.customer),
        selectinload(Estimate.vehicle),
        selectinload(Estimate.staff),
    ]


def _calc_totals(services, parts, discount):
    svc_total = sum(Decimal(str(s.rate)) for s in services)
    prt_total = sum(Decimal(str(p.qty)) * Decimal(str(p.rate)) for p in parts)
    subtotal = max(Decimal("0.00"), svc_total + prt_total - Decimal(str(discount)))
    tax_amount = (subtotal * TAX_RATE / 100).quantize(Decimal("0.01"))
    return subtotal, tax_amount, subtotal + tax_amount


async def _get_or_404(db, est_id):
    result = await db.execute(select(Estimate).options(*_load_opts()).where(Estimate.id == est_id))
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(404, "Estimate not found")
    return est


@router.get("/estimates", response_model=List[EstimateOut])
async def list_estimates(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Estimate).options(*_load_opts()).order_by(Estimate.created_at.desc()))
    return result.scalars().all()


@router.get("/estimates/{est_id}", response_model=EstimateOut)
async def get_estimate(est_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await _get_or_404(db, est_id)


@router.post("/estimates", response_model=EstimateOut, status_code=201)
async def create_estimate(data: EstimateCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    count_result = await db.execute(select(func.count()).select_from(Estimate))
    est_num = f"EST-{count_result.scalar() + 1:05d}"

    est = Estimate(
        id=str(uuid.uuid4()),
        customer_id=data.customer_id,
        vehicle_id=data.vehicle_id,
        staff_id=data.staff_id or None,
        est_num=est_num,
        date_issued=data.date_issued,
        valid_until=data.valid_until,
        status="draft",
        notes=data.notes,
        discount=data.discount,
        subtotal=Decimal("0"),
        tax_amount=Decimal("0"),
        grand_total=Decimal("0"),
    )
    db.add(est)
    await db.flush()

    for s in data.services:
        db.add(EstimateService(estimate_id=est.id, **s.model_dump()))
    for p in data.parts:
        db.add(EstimatePart(estimate_id=est.id, **p.model_dump()))

    await db.flush()
    fresh = await _get_or_404(db, est.id)
    sub, tax, grand = _calc_totals(fresh.services, fresh.parts, data.discount)
    fresh.subtotal, fresh.tax_amount, fresh.grand_total = sub, tax, grand

    await db.commit()
    return await _get_or_404(db, est.id)


@router.put("/estimates/{est_id}", response_model=EstimateOut)
async def update_estimate(est_id: str, data: EstimateUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    est = await _get_or_404(db, est_id)

    for field, val in data.model_dump(exclude_unset=True, exclude={"services", "parts"}).items():
        setattr(est, field, val)

    if data.services is not None:
        for s in est.services:
            await db.delete(s)
        for s in data.services:
            db.add(EstimateService(estimate_id=est_id, **s.model_dump()))

    if data.parts is not None:
        for p in est.parts:
            await db.delete(p)
        for p in data.parts:
            db.add(EstimatePart(estimate_id=est_id, **p.model_dump()))

    await db.flush()
    fresh = await _get_or_404(db, est_id)
    discount = data.discount if data.discount is not None else est.discount
    sub, tax, grand = _calc_totals(fresh.services, fresh.parts, discount)
    fresh.subtotal, fresh.tax_amount, fresh.grand_total = sub, tax, grand

    await db.commit()
    return await _get_or_404(db, est_id)


@router.post("/estimates/{est_id}/convert", status_code=201)
async def convert_to_job(est_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Convert an approved estimate into a job card."""
    est = await _get_or_404(db, est_id)
    if est.status == "converted":
        raise HTTPException(400, "Estimate already converted")

    from .jobs import _load_options as job_load_opts
    job = Job(
        id=str(uuid.uuid4()),
        customer_id=est.customer_id,
        vehicle_id=est.vehicle_id,
        staff_id=est.staff_id,
        status="pending",
        priority="normal",
        date_in=date.today(),
        notes=est.notes,
        discount=est.discount,
    )
    db.add(job)
    await db.flush()

    for s in est.services:
        db.add(JobService(job_id=job.id, description=s.description, department=s.department, rate=s.rate))
    for p in est.parts:
        db.add(JobPart(job_id=job.id, description=p.description, part_no=p.part_no, qty=p.qty, rate=p.rate))

    est.status = "converted"
    await db.commit()

    result = await db.execute(
        select(Job).options(*job_load_opts()).where(Job.id == job.id)
    )
    return result.scalar_one()


@router.delete("/estimates/{est_id}", status_code=204)
async def delete_estimate(est_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_superadmin)):
    est = await _get_or_404(db, est_id)
    await db.delete(est)
    await db.commit()
