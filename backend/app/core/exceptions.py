"""Domain exceptions.

Services raise these; a FastAPI exception handler (see main.py) maps them to
consistent HTTP responses, keeping business logic free of HTTP concerns.
"""


class DomainError(Exception):
    """Base class for domain/business-rule errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """A requested resource does not exist. -> 404"""


class ConflictError(DomainError):
    """A uniqueness/idempotency conflict (e.g. duplicate). -> 409"""


class InvalidStateTransition(DomainError):
    """An illegal lifecycle transition was requested. -> 409"""


class ApprovalRequired(DomainError):
    """An action requires an approved version but it is not approved. -> 409"""
