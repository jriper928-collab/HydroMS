"""Meta Graph API integration — creates and publishes Instagram Reels."""

from fastapi import HTTPException
from httpx import AsyncClient

from app.config import settings

_BASE = f"{settings.META_BASE_URL}/{settings.META_API_VERSION}"


async def create_media_container(video_url: str, caption: str) -> str:
    """POST to Meta API to create a Reels media container. Returns container ID."""
    url = f"{_BASE}/{settings.META_INSTAGRAM_ID}/media"
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": settings.META_ACCESS_TOKEN,
    }
    async with AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, params=params)
    data = resp.json()
    if resp.status_code != 200 or "id" not in data:
        raise HTTPException(
            status_code=502,
            detail=f"Instagram media container creation failed: {data}",
        )
    return data["id"]


async def publish_container(container_id: str) -> str:
    """POST to Meta API to publish a container. Returns permalink URL."""
    url = f"{_BASE}/{settings.META_INSTAGRAM_ID}/media_publish"
    params = {
        "creation_id": container_id,
        "access_token": settings.META_ACCESS_TOKEN,
    }
    async with AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, params=params)
    data = resp.json()
    if resp.status_code != 200 or "id" not in data:
        raise HTTPException(
            status_code=502,
            detail=f"Instagram container publish failed: {data}",
        )
    return f"https://www.instagram.com/reel/{data['id']}"
