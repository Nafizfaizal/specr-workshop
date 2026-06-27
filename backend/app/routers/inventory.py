from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from ..database import get_db
from ..models import Inventory, User
from ..schemas import InventoryCreate, InventoryUpdate, InventoryResponse, InventoryAdjust
from ..auth import get_current_user, require_superadmin

router = APIRouter(tags=["inventory"])


@router.get("/inventory", response_model=List[InventoryResponse])
async def list_inventory(
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Inventory)
    if category:
        q = q.where(Inventory.category == category)
    if search:
        like = f"%{search}%"
        q = q.where(
            or_(
                Inventory.name.ilike(like),
                Inventory.part_no.ilike(like),
                Inventory.category.ilike(like),
            )
        )
    result = await db.execute(q.order_by(Inventory.name))
    return result.scalars().all()


@router.get("/inventory/{item_id}", response_model=InventoryResponse)
async def get_inventory_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Inventory).where(Inventory.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.post("/inventory", response_model=InventoryResponse, status_code=201)
async def create_inventory_item(
    data: InventoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = Inventory(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/inventory/{item_id}", response_model=InventoryResponse)
async def update_inventory_item(
    item_id: str,
    data: InventoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Inventory).where(Inventory.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/inventory/{item_id}", status_code=204)
async def delete_inventory_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    result = await db.execute(select(Inventory).where(Inventory.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    await db.delete(item)
    await db.commit()


@router.post("/inventory/{item_id}/adjust", response_model=InventoryResponse)
async def adjust_inventory(
    item_id: str,
    data: InventoryAdjust,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Inventory).where(Inventory.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    adj_qty = Decimal(str(data.qty))
    current_qty = Decimal(str(item.qty))

    if data.type == "add":
        item.qty = current_qty + adj_qty
    elif data.type == "remove":
        if current_qty < adj_qty:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        item.qty = current_qty - adj_qty
    elif data.type == "set":
        item.qty = adj_qty
    else:
        raise HTTPException(status_code=400, detail="type must be add, remove, or set")

    await db.commit()
    await db.refresh(item)
    return item
