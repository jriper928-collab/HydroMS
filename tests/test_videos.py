"""Integration tests for video upload and farmer profile endpoints."""

import io

import pytest
from httpx import AsyncClient


async def _register(async_client: AsyncClient, email: str) -> tuple[str, str]:
    payload = {"email": email, "password": "strongpass123", "full_name": "Test User"}
    r = await async_client.post("/api/v1/auth/register", json=payload)
    token = r.json()["access_token"]
    user_id = r.json().get("id", "")
    return token, user_id


async def _upload(async_client: AsyncClient, token: str, content: bytes = b"", filename: str = "test.mp4") -> object:
    files = {"file": (filename, io.BytesIO(content), "video/mp4")}
    headers = {"Authorization": f"Bearer {token}"}
    return await async_client.post("/api/v1/videos/upload", files=files, headers=headers)


VALID_MP4_HEADER = b"\x00\x00\x00\x08ftypisom" + b"\x00" * 100


@pytest.mark.asyncio
async def test_upload_video_success(async_client: AsyncClient):
    token, _ = await _register(async_client, "upload_success@test.com")
    resp = await _upload(async_client, token, content=VALID_MP4_HEADER)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "PENDING"
    assert data["message"] == "Video uploaded. Processing pipeline started."


@pytest.mark.asyncio
async def test_upload_video_invalid_type(async_client: AsyncClient):
    token, _ = await _register(async_client, "upload_invalid@test.com")
    files = {"file": ("notes.txt", io.BytesIO(b"plain text"), "text/plain")}
    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.post("/api/v1/videos/upload", files=files, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_video_invalid_magic_bytes(async_client: AsyncClient):
    token, _ = await _register(async_client, "upload_badmagic@test.com")
    content = b"not a real mp4 file at all"
    resp = await _upload(async_client, token, content=content, filename="test.mp4")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_requires_auth(async_client: AsyncClient):
    files = {"file": ("test.mp4", io.BytesIO(VALID_MP4_HEADER), "video/mp4")}
    resp = await async_client.post("/api/v1/videos/upload", files=files)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_video_not_found(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/videos/nonexistent0000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_video_after_upload(async_client: AsyncClient):
    token, _ = await _register(async_client, "get_video@test.com")
    upload_resp = await _upload(async_client, token, content=VALID_MP4_HEADER)
    video_id = upload_resp.json()["id"]

    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.get(f"/api/v1/videos/{video_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == video_id
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_list_videos_empty(async_client: AsyncClient):
    token, _ = await _register(async_client, "list_empty@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.get("/api/v1/videos", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_videos_after_upload(async_client: AsyncClient):
    token, _ = await _register(async_client, "list_one@test.com")
    await _upload(async_client, token, content=VALID_MP4_HEADER)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.get("/api/v1/videos", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_get_farmer_me(async_client: AsyncClient):
    email = "farmer_me@test.com"
    token, _ = await _register(async_client, email)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.get("/api/v1/farmers/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email


@pytest.mark.asyncio
async def test_patch_farmer_me(async_client: AsyncClient):
    token, _ = await _register(async_client, "patch_me@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.patch(
        "/api/v1/farmers/me",
        json={"full_name": "Updated Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Updated Name"
