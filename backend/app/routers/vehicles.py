from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..database import get_db
from ..models import Vehicle
from ..schemas import VehicleCreate, VehicleUpdate, VehicleResponse
from ..auth import get_current_user, require_superadmin
from ..models import User

router = APIRouter(tags=["vehicles"])


@router.get("/vehicles", response_model=List[VehicleResponse])
async def list_vehicles(
    customer_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Vehicle).options(selectinload(Vehicle.customer))
    if customer_id:
        q = q.where(Vehicle.customer_id == customer_id)
    result = await db.execute(q.order_by(Vehicle.created_at.desc()))
    return result.scalars().all()


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Vehicle).options(selectinload(Vehicle.customer)).where(Vehicle.id == vehicle_id)
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
async def create_vehicle(
    data: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vehicle = Vehicle(**data.model_dump())
    db.add(vehicle)
    await db.commit()
    result = await db.execute(
        select(Vehicle).options(selectinload(Vehicle.customer)).where(Vehicle.id == vehicle.id)
    )
    return result.scalar_one()


@router.put("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: str,
    data: VehicleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    await db.commit()
    result = await db.execute(
        select(Vehicle).options(selectinload(Vehicle.customer)).where(Vehicle.id == vehicle_id)
    )
    return result.scalar_one()


@router.delete("/vehicles/{vehicle_id}", status_code=204)
async def delete_vehicle(
    vehicle_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    await db.delete(vehicle)
    await db.commit()
