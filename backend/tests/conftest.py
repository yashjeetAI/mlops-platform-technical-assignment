"""Shared pytest fixtures: isolated in-memory DB and test client."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.seed import seed_demo_users
from app.db.session import Base, get_db
from app.main import app

# Import all models so metadata is fully populated.
from app.models import deployment as _deployment  # noqa: F401
from app.models import metric as _metric  # noqa: F401
from app.models import model as _model  # noqa: F401
from app.models import user as _user  # noqa: F401


@pytest.fixture()
def db_session():
    """Fresh in-memory SQLite DB per test, shared across connections."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    seed_demo_users(db)
    try:
        yield db, TestingSession
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    _, TestingSession = db_session

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # NB: construct TestClient WITHOUT the context manager on purpose. The `with`
    # form runs the app lifespan, which applies Alembic migrations + seeds against
    # Postgres — coupling the "SQLite unit tests" to a live Postgres and causing
    # flakiness. Tests build their schema on SQLite via the db_session fixture, so
    # the production startup is neither needed nor wanted here.
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def auth_header(client: TestClient, username: str, password: str = "demo1234") -> dict:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['accessToken']}"}
