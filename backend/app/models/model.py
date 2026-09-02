"""Model registry ORM: Model and ModelVersion."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import LifecycleStage
from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Model(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "models"

    # Human-friendly business identifier (slug), e.g. "pump-failure-predictor".
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    framework: Mapped[str] = mapped_column(String(64), nullable=False)
    tags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    versions: Mapped[list[ModelVersion]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
        # Newest first (UUIDv7 id is time-ordered).
        order_by="ModelVersion.id.desc()",
    )


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("model_id", "version", name="uq_model_version"),
    )

    model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("models.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[LifecycleStage] = mapped_column(
        SAEnum(LifecycleStage, native_enum=False, length=32),
        default=LifecycleStage.DRAFT,
        nullable=False,
    )
    algorithm: Mapped[str | None] = mapped_column(String(128), nullable=True)
    artifact_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    training_data_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    model: Mapped[Model] = relationship(back_populates="versions")
    events: Mapped[list[ModelVersionEvent]] = relationship(
        back_populates="model_version",
        cascade="all, delete-orphan",
        order_by="ModelVersionEvent.id",  # chronological (UUIDv7)
    )

    @property
    def approved(self) -> bool:
        return self.approved_at is not None


class ModelVersionEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audit trail of a version's lifecycle transitions."""

    __tablename__ = "model_version_events"

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("model_versions.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    # e.g. "created", "validated", "approved", "promoted", "archived".
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    from_stage: Mapped[LifecycleStage | None] = mapped_column(
        SAEnum(LifecycleStage, native_enum=False, length=32), nullable=True
    )
    to_stage: Mapped[LifecycleStage] = mapped_column(
        SAEnum(LifecycleStage, native_enum=False, length=32), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    model_version: Mapped[ModelVersion] = relationship(back_populates="events")
    actor_user: Mapped[User] = relationship("User", lazy="selectin", viewonly=True)

    @property
    def actor(self) -> str | None:
        return self.actor_user.username if self.actor_user else None
