"""Aggregates all v1 API routers under a single APIRouter prefix."""

from fastapi import APIRouter

from app.api.v1 import auth, farmers, map, videos

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth.router)
v1_router.include_router(farmers.router)
v1_router.include_router(videos.router)
v1_router.include_router(map.router)
