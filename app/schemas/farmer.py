"""Pydantic schemas for farmer profile requests and responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FarmerResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FarmerUpdateRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=100)
