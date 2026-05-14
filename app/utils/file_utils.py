"""File validation — extension check and magic byte verification. Pure Python, no libmagic."""

from app.core.exceptions import BadRequest

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS

VIDEO_MAGIC: dict[str, tuple[int, bytes]] = {
    ".mp4": (4, b"ftyp"),
    ".mov": (4, b"ftyp"),
    ".avi": (0, b"RIFF"),
    ".mkv": (0, b"\x1a\x45\xdf\xa3"),
    ".webm": (0, b"\x1a\x45\xdf\xa3"),
}

IMAGE_MAGIC: dict[str, tuple[int, bytes]] = {
    ".jpg":  (0, b"\xff\xd8\xff"),
    ".jpeg": (0, b"\xff\xd8\xff"),
    ".png":  (0, b"\x89PNG"),
    ".webp": (0, b"RIFF"),
}

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024


def is_image_extension(filename: str) -> bool:
    return _get_extension(filename.lower()) in IMAGE_EXTENSIONS


def validate_media_file(filename: str, file_header: bytes) -> None:
    ext = _get_extension(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequest("Invalid file type. Allowed: mp4, mov, avi, mkv, webm, jpg, png, webp")

    if ext in VIDEO_MAGIC:
        offset, expected = VIDEO_MAGIC[ext]
        actual = file_header[offset:offset + len(expected)]
        if actual != expected:
            raise BadRequest("File content does not match extension")
    elif ext in IMAGE_MAGIC:
        offset, expected = IMAGE_MAGIC[ext]
        actual = file_header[offset:offset + len(expected)]
        if actual != expected:
            raise BadRequest("File content does not match extension")


def validate_video_file(filename: str, file_header: bytes) -> None:
    validate_media_file(filename, file_header)


def validate_file_size(size_bytes: int) -> None:
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise BadRequest("File exceeds maximum allowed size of 500MB")


def _get_extension(filename: str) -> str:
    dot = filename.rfind(".")
    if dot == -1:
        return ""
    return filename[dot:]
