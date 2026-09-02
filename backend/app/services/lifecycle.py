"""Model-version lifecycle state machine.

Pure functions over LifecycleStage — no DB, no HTTP — so the rules are trivially
unit-testable. Legal transitions and the approval gate live here as the single
source of truth.
"""
from app.core.enums import LifecycleStage as S
from app.core.exceptions import ApprovalRequired, InvalidStateTransition

# Legal forward/back transitions. ARCHIVED is terminal.
ALLOWED_TRANSITIONS: dict[S, set[S]] = {
    S.DRAFT: {S.VALIDATED, S.ARCHIVED},
    S.VALIDATED: {S.APPROVED, S.DRAFT, S.ARCHIVED},
    S.APPROVED: {S.STAGING, S.VALIDATED, S.ARCHIVED},
    S.STAGING: {S.PRODUCTION, S.APPROVED, S.ARCHIVED},
    S.PRODUCTION: {S.STAGING, S.ARCHIVED},
    S.ARCHIVED: set(),
}

# Stages that may only be entered by an approved version.
REQUIRES_APPROVAL: set[S] = {S.APPROVED, S.STAGING, S.PRODUCTION}


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def validate_transition(current: S, target: S, *, approved: bool) -> None:
    """Raise if moving `current` -> `target` is illegal or approval is missing."""
    if current == target:
        raise InvalidStateTransition(f"Version is already in stage {target.value}")
    if not can_transition(current, target):
        raise InvalidStateTransition(
            f"Illegal transition {current.value} -> {target.value}"
        )
    if target in REQUIRES_APPROVAL and not approved:
        raise ApprovalRequired(
            f"Version must be approved before entering {target.value}"
        )
