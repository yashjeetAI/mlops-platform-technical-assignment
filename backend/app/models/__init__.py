"""ORM models package.

Importing any submodule triggers this, which imports all models so that
Base.metadata is always complete (FK resolution, create_all, migrations, worker).
"""
from app.models import deployment, mixins, model, user  # noqa: F401
