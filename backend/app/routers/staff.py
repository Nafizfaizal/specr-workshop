from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Staff, User
from ..schemas import StaffCreate, StaffUpdate, StaffResponse
from ..auth import get_current_user, require_superadmin

router = APIRouter(tags=["staff"])


@router.get("/staff", response_model=List[StaffResponse])
async def list_staff(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Staff).order_by(Staff.name))
    return result.scalars().all()


@router.get("/staff/{staff_id}", response_model=StaffResponse)
async def get_staff(
    staff_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.post("/staff", response_model=StaffResponse, status_code=201)
async def create_staff(
    data: StaffCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    staff = Staff(**data.model_dump())
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff


@router.put("/staff/{staff_id}", response_model=StaffResponse)
async def update_staff(
    staff_id: str,
    data: StaffUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(staff, field, value)
    await db.commit()
    await db.refresh(staff)
    return staff


@router.delete("/staff/{staff_id}", status_code=204)
async def delete_staff(
    staff_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    await db.delete(staff)
    await db.commit()
