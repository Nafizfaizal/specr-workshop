from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..database import get_db
from ..models import PurchaseBill, PurchaseBillItem, User
from ..schemas import PurchaseBillCreate, PurchaseBillUpdate, PurchaseBillResponse
from ..auth import get_current_user, require_superadmin

router = APIRouter(tags=["purchase_bills"])


def _bill_options():
    return [
        selectinload(PurchaseBill.supplier),
        selectinload(PurchaseBill.items),
    ]


@router.get("/purchase-bills", response_model=List[PurchaseBillResponse])
async def list_bills(
    supplier_id: Optional[str] = None,
    paid: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(PurchaseBill).options(*_bill_options())
    if supplier_id:
        q = q.where(PurchaseBill.supplier_id == supplier_id)
    if paid is not None:
        q = q.where(PurchaseBill.paid == paid)
    result = await db.execute(q.order_by(PurchaseBill.bill_date.desc()))
    return result.scalars().all()


@router.get("/purchase-bills/{bill_id}", response_model=PurchaseBillResponse)
async def get_bill(
    bill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseBill).options(*_bill_options()).where(PurchaseBill.id == bill_id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Purchase bill not found")
    return bill


@router.post("/purchase-bills", response_model=PurchaseBillResponse, status_code=201)
async def create_bill(
    data: PurchaseBillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bill_data = data.model_dump(exclude={"items"})
    bill = PurchaseBill(**bill_data)
    db.add(bill)
    await db.flush()

    for item in data.items:
        db.add(PurchaseBillItem(bill_id=bill.id, **item.model_dump()))

    await db.commit()
    result = await db.execute(
        select(PurchaseBill).options(*_bill_options()).where(PurchaseBill.id == bill.id)
    )
    return result.scalar_one()


@router.put("/purchase-bills/{bill_id}", response_model=PurchaseBillResponse)
async def update_bill(
    bill_id: str,
    data: PurchaseBillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(PurchaseBill).where(PurchaseBill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Purchase bill not found")

    update_data = data.model_dump(exclude_unset=True, exclude={"items"})
    for field, value in update_data.items():
        setattr(bill, field, value)

    if data.items is not None:
        existing = await db.execute(
            select(PurchaseBillItem).where(PurchaseBillItem.bill_id == bill_id)
        )
        for item in existing.scalars().all():
            await db.delete(item)
        for item in data.items:
            db.add(PurchaseBillItem(bill_id=bill_id, **item.model_dump()))

    await db.commit()
    result = await db.execute(
        select(PurchaseBill).options(*_bill_options()).where(PurchaseBill.id == bill_id)
    )
    return result.scalar_one()


@router.put("/purchase-bills/{bill_id}/mark-paid", response_model=PurchaseBillResponse)
async def mark_bill_paid(
    bill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(PurchaseBill).where(PurchaseBill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Purchase bill not found")
    bill.paid = True
    await db.commit()
    result = await db.execute(
        select(PurchaseBill).options(*_bill_options()).where(PurchaseBill.id == bill_id)
    )
    return result.scalar_one()


@router.delete("/purchase-bills/{bill_id}", status_code=204)
async def delete_bill(
    bill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    result = await db.execute(select(PurchaseBill).where(PurchaseBill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Purchase bill not found")
    await db.delete(bill)
    await db.commit()
