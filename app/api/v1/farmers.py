"""Farmer endpoints — profile retrieval and update, with public lookup."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.farmer import FarmerResponse, FarmerUpdateRequest
from app.services import farmer_service

router = APIRouter(prefix="/farmers", tags=["farmers"])


@router.get("/me", response_model=FarmerResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await farmer_service.get_me(db, current_user)


@router.patch("/me", response_model=FarmerResponse)
async def update_my_profile(
    payload: FarmerUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await farmer_service.update_me(db, current_user, payload)


@router.get("/{farmer_id}", response_model=FarmerResponse)
async def get_farmer_profile(
    farmer_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await farmer_service.get_farmer_by_id(db, farmer_id)
