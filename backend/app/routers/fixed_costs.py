from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dateutil.relativedelta import relativedelta
from ..database import get_db
from ..models import FixedCost, User
from ..schemas import FixedCostCreate, FixedCostUpdate, FixedCostResponse
from ..auth import get_current_user, require_superadmin

router = APIRouter(tags=["fixed_costs"])

FREQUENCY_DELTA = {
    "monthly": relativedelta(months=1),
    "weekly": relativedelta(weeks=1),
    "quarterly": relativedelta(months=3),
    "yearly": relativedelta(years=1),
}


@router.get("/fixed-costs", response_model=List[FixedCostResponse])
async def list_fixed_costs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(FixedCost).order_by(FixedCost.name))
    return result.scalars().all()


@router.post("/fixed-costs", response_model=FixedCostResponse, status_code=201)
async def create_fixed_cost(
    data: FixedCostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fc = FixedCost(**data.model_dump())
    db.add(fc)
    await db.commit()
    await db.refresh(fc)
    return fc


@router.put("/fixed-costs/{fc_id}", response_model=FixedCostResponse)
async def update_fixed_cost(
    fc_id: str,
    data: FixedCostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(FixedCost).where(FixedCost.id == fc_id))
    fc = result.scalar_one_or_none()
    if not fc:
        raise HTTPException(status_code=404, detail="Fixed cost not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(fc, field, value)
    await db.commit()
    await db.refresh(fc)
    return fc


@router.delete("/fixed-costs/{fc_id}", status_code=204)
async def delete_fixed_cost(
    fc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    result = await db.execute(select(FixedCost).where(FixedCost.id == fc_id))
    fc = result.scalar_one_or_none()
    if not fc:
        raise HTTPException(status_code=404, detail="Fixed cost not found")
    await db.delete(fc)
    await db.commit()


@router.put("/fixed-costs/{fc_id}/mark-paid", response_model=FixedCostResponse)
async def mark_fixed_cost_paid(
    fc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(FixedCost).where(FixedCost.id == fc_id))
    fc = result.scalar_one_or_none()
    if not fc:
        raise HTTPException(status_code=404, detail="Fixed cost not found")

    today = date.today()
    fc.last_paid_date = today
    fc.paid = True

    if fc.frequency == "one-time":
        fc.active = False
        fc.next_due_date = None
    else:
        delta = FREQUENCY_DELTA.get(fc.frequency)
        if delta and fc.next_due_date:
            fc.next_due_date = fc.next_due_date + delta
        elif delta:
            fc.next_due_date = today + delta

    await db.commit()
    await db.refresh(fc)
    return fc


@router.put("/fixed-costs/{fc_id}/toggle-active", response_model=FixedCostResponse)
async def toggle_fixed_cost_active(
    fc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(FixedCost).where(FixedCost.id == fc_id))
    fc = result.scalar_one_or_none()
    if not fc:
        raise HTTPException(status_code=404, detail="Fixed cost not found")
    fc.active = not fc.active
    await db.commit()
    await db.refresh(fc)
    return fc
