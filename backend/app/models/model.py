"""Model registry ORM: Model and ModelVersion."""
import uuid
from datetime import datetime

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

    versions: Mapped[list["ModelVersion"]] = relationship(
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

    model: Mapped["Model"] = relationship(back_populates="versions")

    @property
    def approved(self) -> bool:
        return self.approved_at is not None
