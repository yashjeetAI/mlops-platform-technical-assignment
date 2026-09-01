"""Shared FastAPI dependencies: authentication and role-based authorization."""
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the Bearer JWT."""
    if credentials is None:
        raise _CREDENTIALS_ERROR
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise _CREDENTIALS_ERROR from exc

    username = payload.get("sub")
    if not username:
        raise _CREDENTIALS_ERROR

    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        raise _CREDENTIALS_ERROR
    return user


def require_roles(*allowed: Role) -> Callable[[User], User]:
    """Dependency factory enforcing that the current user has one of `allowed` roles.

    ADMIN is always permitted.
    """
    allowed_set = set(allowed) | {Role.ADMIN}

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{user.role}' is not permitted for this action; "
                    f"requires one of {sorted(r.value for r in allowed_set)}"
                ),
            )
        return user

    return _guard
