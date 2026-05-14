"""SQLAlchemy declarative base. All models import from here."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
