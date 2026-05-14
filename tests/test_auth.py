"""Integration tests for authentication endpoints — covers all 7 scenarios."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(async_client: AsyncClient):
    payload = {
        "email": "farmer@test.com",
        "password": "strongpass123",
        "full_name": "Test Farmer",
    }
    resp = await async_client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate(async_client: AsyncClient):
    payload = {
        "email": "dup@test.com",
        "password": "strongpass123",
        "full_name": "Duplicate",
    }
    await async_client.post("/api/v1/auth/register", json=payload)
    resp = await async_client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_login(async_client: AsyncClient):
    register_payload = {
        "email": "login@test.com",
        "password": "strongpass123",
        "full_name": "Login Test",
    }
    await async_client.post("/api/v1/auth/register", json=register_payload)

    login_payload = {
        "email": "login@test.com",
        "password": "strongpass123",
    }
    resp = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient):
    await async_client.post("/api/v1/auth/register",
                            json={"email": "wrong@test.com", "password": "strongpass123", "full_name": "Wrong"})
    payload = {
        "email": "wrong@test.com",
        "password": "wrongpass",
    }
    resp = await async_client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_refresh_token(async_client: AsyncClient):
    register_payload = {
        "email": "refresh@test.com",
        "password": "strongpass123",
        "full_name": "Refresh Test",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=register_payload)
    refresh_token = reg_resp.json()["refresh_token"]

    resp = await async_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    payload = {
        "email": "nobody@test.com",
        "password": "strongpass123",
    }
    resp = await async_client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "invalid.jwt.token"}
    )
    assert resp.status_code == 401
