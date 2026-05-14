"""Pipeline Step 3 — frame extraction and OpenRouter vision API metadata generation."""

import asyncio
import base64
import json
import re

import cv2
from openai import OpenAI

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

FALLBACK: dict = {
    "title_en": "Azerbaijan Rural Life — Traditional Farming",
    "title_az": "Azərbaycan Kənd Həyatı — Ənənəvi Əkinçilik",
    "title_ar": "",
    "hashtags_en": "azerbaijan, farming, agriculture, rural, nature, caucasus, organic, harvest, village, countryside",
    "hashtags_az": "azərbaycan, əkinçilik, kənd, təbiət, ferma, kəndli",
    "hashtags_ar": "",
}

_SYSTEM = (
    "You are an agricultural social media specialist for AgroVibe AZ. "
    "Generate Instagram metadata for farming videos from Azerbaijan. "
    "Respond with valid JSON only, no markdown, no explanation."
)

_USER = (
    "Analyze this farming video frame from Azerbaijan.\n"
    "Respond ONLY with this exact JSON, nothing else:\n"
    "{\n"
    '  "scene_description": "2-3 sentences about what you see",\n'
    '  "title_en": "catchy English title max 10 words",\n'
    '  "title_az": "Azerbaijani title in Latin script",\n'
    '  "hashtags_en": "10 hashtags comma-separated no # symbol",\n'
    '  "hashtags_az": "6 hashtags comma-separated no # symbol"\n'
    "}\n"
    "Focus on: agriculture, Azerbaijan, rural life, farming, nature."
)


def _extract_frame_b64(media_path: str) -> str | None:
    """Extract a frame from video or load image as base64 JPEG. CPU-bound, runs in executor."""
    from pathlib import Path
    ext = Path(media_path).suffix.lower()

    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        frame = cv2.imread(media_path)
        if frame is None:
            return None
    else:
        cap = cv2.VideoCapture(media_path)
        if not cap.isOpened():
            return None
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return None

    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if not ok:
        return None
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _parse_json_response(text: str) -> dict | None:
    """Strip optional markdown fences and parse JSON. Returns None on failure."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip())
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def _call_openrouter(b64: str) -> str:
    """Blocking OpenRouter vision API call. Confirmed working with sync client."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
    )
    resp = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": f"{_SYSTEM}\n\n{_USER}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }],
        max_tokens=512,
    )
    return resp.choices[0].message.content or ""


async def generate_metadata(video_id: str, media_path_override: str | None = None) -> dict:
    """Extract a video frame, call OpenRouter vision API, return metadata dict.

    Falls back to hardcoded values if the API key is missing or the call fails.
    Always returns a dict with keys: title_en, title_az, title_ar,
    hashtags_en, hashtags_az, hashtags_ar.
    """
    video_path = media_path_override or str(settings.MEDIA_PROCESSED_DIR / f"{video_id}_audio.mp4")
    loop = asyncio.get_event_loop()

    # Step 1 — Extract frame (CPU-bound)
    logger.info("metadata_frame_extraction", video_id=video_id, path=video_path)
    b64 = await loop.run_in_executor(None, _extract_frame_b64, video_path)
    if not b64:
        logger.warning("metadata_frame_extraction_failed", video_id=video_id)
        return FALLBACK.copy()

    # Step 2 — Vision API (skip if no key configured)
    if not settings.OPENROUTER_API_KEY:
        logger.info("metadata_vision_api_skipped_no_key", video_id=video_id)
        return FALLBACK.copy()

    logger.info("metadata_vision_api_call", video_id=video_id)
    try:
        raw = await loop.run_in_executor(None, _call_openrouter, b64)
        data = _parse_json_response(raw)
        if data is None:
            logger.warning(
                "metadata_json_parse_failed",
                video_id=video_id,
                raw=raw[:200] if raw else "",
            )
            return FALLBACK.copy()

        result = FALLBACK.copy()
        result["title_en"] = data.get("title_en") or FALLBACK["title_en"]
        result["title_az"] = data.get("title_az") or FALLBACK["title_az"]
        result["hashtags_en"] = data.get("hashtags_en") or FALLBACK["hashtags_en"]
        result["hashtags_az"] = data.get("hashtags_az") or FALLBACK["hashtags_az"]
        logger.info("metadata_saved", video_id=video_id, title_en=result["title_en"])
        return result

    except Exception as exc:
        logger.warning("metadata_vision_api_failed", video_id=video_id, error=str(exc))
        return FALLBACK.copy()
