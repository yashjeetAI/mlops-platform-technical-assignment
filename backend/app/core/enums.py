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
