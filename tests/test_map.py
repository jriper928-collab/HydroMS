"""Integration tests for the GeoJSON map endpoint (Phase 5)."""

import io

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video import Video, VideoStatus

VALID_MP4_HEADER = b"\x00\x00\x00\x08ftypisom" + b"\x00" * 100


async def _register(async_client: AsyncClient, email: str) -> str:
    payload = {"email": email, "password": "strongpass123", "full_name": "Ali Farmer"}
    r = await async_client.post("/api/v1/auth/register", json=payload)
    return r.json()["access_token"]


async def _upload(
    async_client: AsyncClient,
    token: str,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    files = {"file": ("test.mp4", io.BytesIO(VALID_MP4_HEADER), "video/mp4")}
    headers = {"Authorization": f"Bearer {token}"}
    data: dict = {}
    if lat is not None:
        data["latitude"] = str(lat)
    if lon is not None:
        data["longitude"] = str(lon)
    r = await async_client.post(
        "/api/v1/videos/upload", files=files, data=data, headers=headers
    )
    return r.json()


async def _set_published(db: AsyncSession, video_id: str) -> None:
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one()
    video.status = VideoStatus.PUBLISHED
    await db.commit()


@pytest.mark.asyncio
async def test_geojson_empty(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/map/geojson")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert data["features"] == []


@pytest.mark.asyncio
async def test_geojson_structure(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/map/geojson")
    assert resp.status_code == 200
    data = resp.json()
    assert "type" in data
    assert "features" in data
    if data["features"]:
        feature = data["features"][0]
        assert feature["type"] == "Feature"
        assert "geometry" in feature
        assert "properties" in feature
        assert feature["geometry"]["type"] == "Point"
        assert len(feature["geometry"]["coordinates"]) == 2


@pytest.mark.asyncio
async def test_geojson_published_with_gps(async_client: AsyncClient, db: AsyncSession):
    token = await _register(async_client, "gps_pub@test.com")
    upload_data = await _upload(async_client, token, lat=40.4093, lon=49.8671)
    await _set_published(db, upload_data["id"])

    resp = await async_client.get("/api/v1/map/geojson")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["features"]) == 1

    feature = data["features"][0]
    coords = feature["geometry"]["coordinates"]
    assert coords[0] == pytest.approx(49.8671)
    assert coords[1] == pytest.approx(40.4093)

    props = feature["properties"]
    assert "farmer_name" in props
    assert "video_title_en" in props
    assert "instagram_url" in props


@pytest.mark.asyncio
async def test_geojson_no_gps_excluded(async_client: AsyncClient, db: AsyncSession):
    token = await _register(async_client, "no_gps@test.com")
    upload_data = await _upload(async_client, token)
    await _set_published(db, upload_data["id"])

    resp = await async_client.get("/api/v1/map/geojson")
    assert resp.status_code == 200
    assert resp.json()["features"] == []


@pytest.mark.asyncio
async def test_geojson_unpublished_excluded(async_client: AsyncClient):
    token = await _register(async_client, "unpub_gps@test.com")
    await _upload(async_client, token, lat=40.4093, lon=49.8671)

    resp = await async_client.get("/api/v1/map/geojson")
    assert resp.status_code == 200
    assert resp.json()["features"] == []
