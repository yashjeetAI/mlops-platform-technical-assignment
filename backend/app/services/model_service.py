"""Model registry service layer.

Business logic for models and versions, including lifecycle transitions. Functions
take an explicit Session (see ADR-0001) and raise domain errors (see exceptions.py).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import LifecycleStage
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.text import slugify
from app.models.mixins import utcnow
from app.models.model import Model, ModelVersion
from app.schemas.model import ModelCreate, ModelVersionCreate
from app.services import lifecycle

logger = get_logger("registry")


# --- models ---

def _unique_key(db: Session, name: str) -> str:
    """Derive a unique slug from the model name (append -2, -3, … on collision)."""
    base = slugify(name)
    key = base
    n = 2
    while db.execute(select(Model).where(Model.key == key)).scalar_one_or_none() is not None:
        key = f"{base}-{n}"
        n += 1
    return key


def create_model(db: Session, actor_id: uuid.UUID, data: ModelCreate) -> Model:
    model = Model(
        key=_unique_key(db, data.name),
        name=data.name,
        owner=data.owner,
        framework=data.framework.value,
        tags=data.tags,
        created_by=actor_id,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    logger.info("model_created", model_id=str(model.id), key=model.key, actor=str(actor_id))
    return model


def list_models(db: Session) -> list[Model]:
    return list(db.execute(select(Model).order_by(Model.created_at)).scalars())


def get_model(db: Session, model_id: uuid.UUID) -> Model:
    model = db.get(Model, model_id)
    if model is None:
        raise NotFoundError(f"Model {model_id} not found")
    return model


# --- versions ---

def create_version(
    db: Session, actor_id: uuid.UUID, model_id: uuid.UUID, data: ModelVersionCreate
) -> ModelVersion:
    get_model(db, model_id)  # 404 if the model is missing
    dup = db.execute(
        select(ModelVersion).where(
            ModelVersion.model_id == model_id, ModelVersion.version == data.version
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise ConflictError(f"Version '{data.version}' already exists for this model")
    version = ModelVersion(
        model_id=model_id,
        version=data.version,
        stage=LifecycleStage.DRAFT,
        algorithm=data.algorithm,
        artifact_uri=data.artifact_uri,
        training_data_ref=data.training_data_ref,
        tags=data.tags,
        created_by=actor_id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    logger.info(
        "version_created",
        model_id=str(model_id),
        version_id=str(version.id),
        version=version.version,
        actor=str(actor_id),
    )
    return version


def list_versions(db: Session, model_id: uuid.UUID) -> list[ModelVersion]:
    get_model(db, model_id)
    return list(
        db.execute(
            select(ModelVersion)
            .where(ModelVersion.model_id == model_id)
            .order_by(ModelVersion.created_at)
        ).scalars()
    )


def get_version(db: Session, version_id: uuid.UUID) -> ModelVersion:
    version = db.get(ModelVersion, version_id)
    if version is None:
        raise NotFoundError(f"Model version {version_id} not found")
    return version


def approve_version(
    db: Session, actor_id: uuid.UUID, version_id: uuid.UUID
) -> ModelVersion:
    """Approve a version (VALIDATED -> APPROVED), recording the approver."""
    version = get_version(db, version_id)
    # Approving grants approval, so validate with approved=True.
    lifecycle.validate_transition(version.stage, LifecycleStage.APPROVED, approved=True)
    version.approved_at = utcnow()
    version.approved_by = actor_id
    version.stage = LifecycleStage.APPROVED
    db.commit()
    db.refresh(version)
    logger.info("version_approved", version_id=str(version_id), actor=str(actor_id))
    return version


def transition_version(
    db: Session, version_id: uuid.UUID, target: LifecycleStage
) -> ModelVersion:
    """Move a version to `target`, enforcing legality and the approval gate."""
    version = get_version(db, version_id)
    from_stage = version.stage
    lifecycle.validate_transition(from_stage, target, approved=version.approved)
    version.stage = target
    db.commit()
    db.refresh(version)
    logger.info(
        "version_promoted",
        version_id=str(version_id),
        from_stage=from_stage.value,
        to_stage=target.value,
    )
    return version
