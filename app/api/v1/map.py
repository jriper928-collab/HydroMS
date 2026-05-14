"""Map endpoints — returns GeoJSON FeatureCollection of published video locations."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.map import GeoJSONFeatureCollection
from app.services.map_service import get_geojson

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/geojson", response_model=GeoJSONFeatureCollection)
async def get_map_geojson(
    db: AsyncSession = Depends(get_db),
):
    return await get_geojson(db)
