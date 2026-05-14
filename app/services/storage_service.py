"""Local filesystem storage — chunked write for raw uploads, file path utilities."""

import shutil
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

settings.MEDIA_RAW_DIR.mkdir(parents=True, exist_ok=True)
settings.MEDIA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 1024 * 1024


async def save_raw_video(file: UploadFile, filename: str) -> str:
    dest = settings.MEDIA_RAW_DIR / filename
    with dest.open("wb") as buffer:
        while chunk := await file.read(CHUNK_SIZE):
            buffer.write(chunk)
    return f"media/raw/{filename}"


def save_processed_video(source_path: str, filename: str) -> str:
    dest = settings.MEDIA_PROCESSED_DIR / filename
    shutil.copy2(source_path, str(dest))
    return f"/static/media/processed/{filename}"


def build_raw_filename(video_id: str, original_filename: str) -> str:
    dot = original_filename.rfind(".")
    ext = original_filename[dot:] if dot != -1 else ".mp4"
    return f"{video_id}{ext}"


def get_raw_path(filename: str) -> Path:
    return settings.MEDIA_RAW_DIR / filename
