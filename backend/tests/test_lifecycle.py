"""Unit tests for the lifecycle state machine (pure, no DB)."""
import pytest

from app.core.enums import LifecycleStage as S
from app.core.exceptions import ApprovalRequired, InvalidStateTransition
from app.services import lifecycle


@pytest.mark.parametrize(
    "current,target",
    [
        (S.DRAFT, S.VALIDATED),
        (S.VALIDATED, S.APPROVED),
        (S.APPROVED, S.STAGING),
        (S.STAGING, S.PRODUCTION),
        (S.PRODUCTION, S.ARCHIVED),
        (S.DRAFT, S.ARCHIVED),
    ],
)
def test_legal_transitions(current, target):
    assert lifecycle.can_transition(current, target)
    # approved=True so the approval gate never blocks these
    lifecycle.validate_transition(current, target, approved=True)


@pytest.mark.parametrize(
    "current,target",
    [
        (S.DRAFT, S.PRODUCTION),   # can't skip stages
        (S.VALIDATED, S.PRODUCTION),
        (S.DRAFT, S.APPROVED),
        (S.ARCHIVED, S.DRAFT),     # terminal
        (S.PRODUCTION, S.DRAFT),
    ],
)
def test_illegal_transitions_raise(current, target):
    assert not lifecycle.can_transition(current, target)
    with pytest.raises(InvalidStateTransition):
        lifecycle.validate_transition(current, target, approved=True)


def test_same_stage_is_rejected():
    with pytest.raises(InvalidStateTransition):
        lifecycle.validate_transition(S.STAGING, S.STAGING, approved=True)


@pytest.mark.parametrize("target", [S.APPROVED, S.STAGING, S.PRODUCTION])
def test_approval_gate_blocks_unapproved(target):
    # structurally-legal source, but approved=False must raise
    source = {S.APPROVED: S.VALIDATED, S.STAGING: S.APPROVED, S.PRODUCTION: S.STAGING}[target]
    with pytest.raises(ApprovalRequired):
        lifecycle.validate_transition(source, target, approved=False)
