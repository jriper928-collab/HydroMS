"""GPS coordinate validation and formatting helpers."""

from app.core.exceptions import BadRequest


def validate_coordinates(latitude: float, longitude: float) -> None:
    if not (-90.0 <= latitude <= 90.0):
        raise BadRequest("Invalid GPS coordinates")
    if not (-180.0 <= longitude <= 180.0):
        raise BadRequest("Invalid GPS coordinates")


def format_coordinates(latitude: float, longitude: float) -> dict:
    return {"latitude": round(latitude, 6), "longitude": round(longitude, 6)}
