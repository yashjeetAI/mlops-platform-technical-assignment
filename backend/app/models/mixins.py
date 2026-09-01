"""Reusable ORM column mixins."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    """Time-ordered UUID (v7) primary key.

    Uses SQLAlchemy's dialect-aware `Uuid` type: native `uuid` on PostgreSQL,
    CHAR(32) on SQLite. Generated app-side so IDs need no central sequence.
    UUIDv7 embeds a timestamp prefix, so keys are roughly monotonic — this
    restores B-tree index locality that random UUIDv4 loses on high-volume inserts.
    Requires Python 3.14+ (stdlib `uuid.uuid7`).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid7
    )


class TimestampMixin:
    """Adds created_at / updated_at audit timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
