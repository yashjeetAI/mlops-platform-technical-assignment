"""Monitoring metric ORM."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import Environment
from app.db.session import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Metric(UUIDPrimaryKeyMixin, Base):
    """A monitoring sample for a model version in an environment at a point in time."""

    __tablename__ = "metrics"
    __table_args__ = (
        Index("ix_metrics_model_time", "model_id", "timestamp"),
    )

    model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("models.id", ondelete="CASCADE"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=True
    )
    # The deployment that produced this sample (metrics come from a running deployment).
    deployment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[Environment] = mapped_column(
        SAEnum(Environment, native_enum=False, length=32), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    throughput_rpm: Mapped[float] = mapped_column(Float, nullable=False)
    error_rate: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    drift_score: Mapped[float] = mapped_column(Float, nullable=False)
    availability: Mapped[float] = mapped_column(Float, nullable=False)
