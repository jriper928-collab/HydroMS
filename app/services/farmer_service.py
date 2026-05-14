"""Farmer profile business logic — get/update current user, public profile lookup."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundException
from app.models.user import User
from app.schemas.farmer import FarmerResponse, FarmerUpdateRequest


async def get_me(db: AsyncSession, user: User) -> FarmerResponse:
    return FarmerResponse.model_validate(user)


async def update_me(
    db: AsyncSession, user: User, data: FarmerUpdateRequest
) -> FarmerResponse:
    if data.full_name is not None:
        user.full_name = data.full_name
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return FarmerResponse.model_validate(user)


async def get_farmer_by_id(db: AsyncSession, farmer_id: str) -> FarmerResponse:
    result = await db.execute(select(User).where(User.id == farmer_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UserNotFoundException()
    return FarmerResponse.model_validate(user)
