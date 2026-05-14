"""FastAPI application factory — lifespan, CORS, static media mount, and health check."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import v1_router
from app.config import settings
from app.core.logging import setup_logging
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db()
    yield


app = FastAPI(
    title="AgroVibe AZ",
    description="AI-powered media automation platform for agricultural producers",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)

settings.MEDIA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
settings.MEDIA_RAW_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static/media",
    StaticFiles(directory=str(settings.MEDIA_PROCESSED_DIR)),
    name="media",
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agrovibe-az"}
