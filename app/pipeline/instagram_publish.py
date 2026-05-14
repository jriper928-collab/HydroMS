"""Pipeline Step 4 — builds caption and publishes the processed video to Instagram."""

from app.config import settings
from app.core.logging import get_logger
from app.services import instagram_service

logger = get_logger(__name__)


_DEMO_VIDEO_URL = "https://www.instagram.com/agrovibe.az/"
_DEMO_IMAGE_URL = "https://www.instagram.com/agrovibe.az/"


async def publish_to_instagram(
    video_id: str,
    title_en: str,
    hashtags_en: str,
    is_image: bool = False,
) -> str:
    """Build caption, publish to Instagram if credentials exist, return permalink."""
    tags = " #".join(tag.strip() for tag in hashtags_en.split(",") if tag.strip())
    caption = f"{title_en}\n\n#{tags}"

    # /static/media is mounted directly on MEDIA_PROCESSED_DIR — no extra path segment
    video_url = f"{settings.BASE_URL}/static/media/{video_id}_audio.mp4"

    if not settings.META_ACCESS_TOKEN:
        permalink = _DEMO_IMAGE_URL if is_image else _DEMO_VIDEO_URL
        logger.info("instagram_skipped", video_id=video_id, permalink=permalink)
        return permalink

    logger.info("instagram_publish_start", video_id=video_id, video_url=video_url)
    container_id = await instagram_service.create_media_container(video_url, caption)
    permalink = await instagram_service.publish_container(container_id)
    logger.info("instagram_published", video_id=video_id, permalink=permalink)
    logger.info("status_published", video_id=video_id)
    return permalink
