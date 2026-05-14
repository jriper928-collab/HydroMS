"""Pydantic schemas for GeoJSON FeatureCollection responses."""

from pydantic import BaseModel, ConfigDict


class MediaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    thumbnail_url: str | None
    media_url: str | None
    is_image: bool
    title_en: str | None
    instagram_url: str | None = None


class GeoJSONGeometry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type: str = "Point"
    coordinates: list[float]


class GeoJSONProperties(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    farmer_name: str
    farmer_id: str
    video_title_en: str | None
    thumbnail_url: str | None
    instagram_url: str | None
    media_items: list[MediaItem]


class GeoJSONFeature(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: GeoJSONProperties


class GeoJSONFeatureCollection(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]
