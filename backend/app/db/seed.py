"""Idempotent seeding of demo users."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import Role
from app.core.security import hash_password
from app.models.user import User

settings = get_settings()

# One demo user per role. Password is the same for all (settings.demo_password).
DEMO_USERS = [
    {"username": "admin", "full_name": "Ada Admin", "email": "admin@example.com", "role": Role.ADMIN},
    {"username": "approver", "full_name": "Priya Approver", "email": "approver@example.com", "role": Role.APPROVER},
    {"username": "engineer", "full_name": "Eli Engineer", "email": "engineer@example.com", "role": Role.ENGINEER},
    {"username": "viewer", "full_name": "Vic Viewer", "email": "viewer@example.com", "role": Role.VIEWER},
]


def seed_demo_users(db: Session) -> int:
    """Insert demo users that don't already exist. Returns count created."""
    created = 0
    for spec in DEMO_USERS:
        exists = db.execute(
            select(User).where(User.username == spec["username"])
        ).scalar_one_or_none()
        if exists:
            continue
        db.add(
            User(
                username=spec["username"],
                full_name=spec["full_name"],
                email=spec["email"],
                role=spec["role"],
                hashed_password=hash_password(settings.demo_password),
            )
        )
        created += 1
    if created:
        db.commit()
    return created
