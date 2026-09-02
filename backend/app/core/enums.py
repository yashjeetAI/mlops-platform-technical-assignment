"""Shared domain enumerations."""
from enum import StrEnum


class Role(StrEnum):
    """User roles, ordered from least to most privileged.

    Governance mapping:
      - VIEWER   : read-only access to registry and monitoring
      - ENGINEER : create models/versions, request deployments
      - APPROVER : approve versions, promote to PRODUCTION
      - ADMIN    : full access, including rollback
    """

    VIEWER = "VIEWER"
    ENGINEER = "ENGINEER"
    APPROVER = "APPROVER"
    ADMIN = "ADMIN"


class LifecycleStage(StrEnum):
    """Model-version lifecycle stages.

    Ordered progression: DRAFT -> VALIDATED -> APPROVED -> STAGING -> PRODUCTION,
    with ARCHIVED reachable as a terminal retirement state. Transition legality is
    enforced by the lifecycle state machine (see services/lifecycle.py).
    """

    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


class Environment(StrEnum):
    """Deployment target environments."""

    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
