"""Builds a GeoJSON FeatureCollection from published video locations."""

from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.video import Video, VideoStatus
from app.schemas.map import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONGeometry,
    GeoJSONProperties,
    MediaItem,
)

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

_DEMO_VIDEO_INSTAGRAM = "https://www.instagram.com/agrovibe.az/"
_DEMO_IMAGE_INSTAGRAM = "https://www.instagram.com/agrovibe.az/"


def _is_image(raw_path: str | None) -> bool:
    if not raw_path:
        return False
    return Path(raw_path).suffix.lower() in _IMAGE_EXTS


def _demo_instagram_url(is_img: bool) -> str:
    return _DEMO_IMAGE_INSTAGRAM if is_img else _DEMO_VIDEO_INSTAGRAM


async def get_geojson(db: AsyncSession) -> GeoJSONFeatureCollection:
    result = await db.execute(
        select(Video)
        .options(joinedload(Video.farmer))
        .where(
            Video.status == VideoStatus.PUBLISHED,
            Video.latitude.is_not(None),
            Video.longitude.is_not(None),
        )
        .order_by(Video.created_at.desc())
    )
    videos = result.scalars().all()

    # Group by (farmer_id, lat bucket, lng bucket) — 3-decimal precision clusters nearby pins
    groups: dict[tuple, list[Video]] = defaultdict(list)
    for video in videos:
        key = (
            video.farmer_id,
            round(video.latitude, 3),
            round(video.longitude, 3),
        )
        groups[key].append(video)

    features: list[GeoJSONFeature] = []
    for (farmer_id, lat, lng), group_videos in groups.items():
        first = group_videos[0]
        farmer_name = first.farmer.full_name if first.farmer else "Unknown Farmer"

        media_items = [
            MediaItem(
                thumbnail_url=v.thumbnail_path,
                media_url=v.processed_path,
                is_image=_is_image(v.raw_path),
                title_en=v.title_en,
                instagram_url=v.instagram_permalink or _demo_instagram_url(_is_image(v.raw_path)),
            )
            for v in group_videos
        ]

        first_is_image = _is_image(first.raw_path)
        features.append(
            GeoJSONFeature(
                geometry=GeoJSONGeometry(coordinates=[lng, lat]),
                properties=GeoJSONProperties(
                    farmer_name=farmer_name,
                    farmer_id=farmer_id,
                    video_title_en=first.title_en,
                    thumbnail_url=first.thumbnail_path,
                    instagram_url=_demo_instagram_url(first_is_image),
                    media_items=media_items,
                ),
            )
        )

    return GeoJSONFeatureCollection(features=features)
