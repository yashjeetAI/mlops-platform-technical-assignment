"""Deployment eligibility policy — which lifecycle stage can deploy where.

Stage-gated (strict): a version must be promoted to a stage before it can deploy to
the matching environment. DRAFT and ARCHIVED are never deployable.
"""
from app.core.enums import Environment, LifecycleStage as S

DEPLOYABLE_STAGES: dict[Environment, set[S]] = {
    Environment.DEVELOPMENT: {S.VALIDATED, S.APPROVED, S.STAGING, S.PRODUCTION},
    Environment.STAGING: {S.STAGING, S.PRODUCTION},
    Environment.PRODUCTION: {S.PRODUCTION},
}


def is_deployable(stage: S, environment: Environment) -> bool:
    return stage in DEPLOYABLE_STAGES[environment]
