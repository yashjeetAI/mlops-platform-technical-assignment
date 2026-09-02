"""Deployment ORM: Deployment and DeploymentEvent.

The `deployments` table doubles as the work queue: the worker claims REQUESTED rows
with FOR UPDATE SKIP LOCKED, advances the status, and records a DeploymentEvent per step.
`worker_id`/`locked_at`/`attempts` support the visibility-timeout reaper.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DeploymentStatus, Environment
from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# In-flight states: at most one active deployment per (model, environment).
_IN_FLIGHT_SQL = "status IN ('REQUESTED', 'VALIDATING', 'DEPLOYING')"


class Deployment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deployments"
    __table_args__ = (
        # Business guard: block a second concurrent deployment of the SAME model to
        # the SAME environment while one is still in flight. DB-enforced (race-free);
        # scoped to in-flight states so a new deploy can supersede a succeeded one.
        Index(
            "uq_active_deployment",
            "model_id",
            "environment",
            unique=True,
            postgresql_where=text(_IN_FLIGHT_SQL),
            sqlite_where=text(_IN_FLIGHT_SQL),
        ),
    )

    # Denormalized from the version (immutable) so the guard + rollback need no join.
    model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("models.id"), index=True, nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("model_versions.id"), index=True, nullable=False
    )
    environment: Mapped[Environment] = mapped_column(
        SAEnum(Environment, native_enum=False, length=32), nullable=False
    )
    status: Mapped[DeploymentStatus] = mapped_column(
        SAEnum(DeploymentStatus, native_enum=False, length=32),
        default=DeploymentStatus.REQUESTED,
        index=True,
        nullable=False,
    )

    # Idempotency: a client-supplied key dedupes duplicate requests (nullable -> not enforced).
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )

    # Queue bookkeeping for the worker + reaper.
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Failure-simulation hook for demos/tests.
    simulate_failure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Carries the request's correlation id across the API -> worker boundary.
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    rolled_back_to_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("deployments.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    events: Mapped[list["DeploymentEvent"]] = relationship(
        back_populates="deployment",
        cascade="all, delete-orphan",
        order_by="DeploymentEvent.created_at",
    )


class DeploymentEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deployment_events"

    deployment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("deployments.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    status: Mapped[DeploymentStatus] = mapped_column(
        SAEnum(DeploymentStatus, native_enum=False, length=32), nullable=False
    )
    # Machine-friendly event name, e.g. "deployment_completed", "runtime_timeout".
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    deployment: Mapped["Deployment"] = relationship(back_populates="events")
