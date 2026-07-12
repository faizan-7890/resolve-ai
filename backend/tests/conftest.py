"""
Pytest fixtures for ResolveAI backend tests.
Uses an in-memory SQLite database to avoid needing a real PostgreSQL connection.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User

# SQLite in-memory test database (no PostgreSQL needed)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override the DB dependency with the test SQLite database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables before tests and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a fresh database session per test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client():
    """Provide a FastAPI TestClient with the test DB injected."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a standard test user in the test DB."""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("TestPass123"),
        name="Test User",
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()


@pytest.fixture
def auth_headers(client, test_user):
    """Provide Bearer token auth headers for the test user."""
    res = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123"
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
