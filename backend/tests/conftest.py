"""
Pytest fixtures for ResolveAI backend tests.
Uses an in-memory SQLite database (with StaticPool) so no local DB files or PostgreSQL server are required.
"""
import os

# Provide deterministic test defaults before importing app settings/main
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("NVIDIA_NIM_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.middleware.rate_limiter import reset_rate_limits
from app.models.user import User

SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override the DB dependency with the shared in-memory test SQLite database."""
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


@pytest.fixture(autouse=True)
def clear_rate_limiter():
    """Reset in-memory rate limit buckets before each test."""
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def db():
    """Provide a database session per test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    """Provide a FastAPI TestClient with the test DB injected."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _create_or_get_user(db, email: str, password: str, name: str, role: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        existing.password_hash = get_password_hash(password)
        existing.role = role
        db.commit()
        db.refresh(existing)
        return existing
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        name=name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user(db):
    """Create a standard test user in the test DB."""
    user = _create_or_get_user(db, "test@example.com", "TestPass123", "Test User", "user")
    yield user
    persisted = db.query(User).filter(User.id == user.id).first()
    if persisted:
        db.delete(persisted)
        db.commit()


@pytest.fixture
def auth_headers(client, test_user):
    """Provide Bearer token auth headers for the standard test user."""
    res = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123",
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_user(db):
    """Create a second standard user to verify ownership/IDOR isolation."""
    user = _create_or_get_user(db, "other@example.com", "OtherPass123", "Other User", "user")
    yield user
    persisted = db.query(User).filter(User.id == user.id).first()
    if persisted:
        db.delete(persisted)
        db.commit()


@pytest.fixture
def second_auth_headers(client, second_user):
    """Provide Bearer token auth headers for the second standard user."""
    res = client.post("/api/auth/login", json={
        "email": "other@example.com",
        "password": "OtherPass123",
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_user(db):
    """Create an admin test user in the test DB."""
    user = _create_or_get_user(db, "admin@example.com", "AdminPass123", "Admin User", "admin")
    yield user
    persisted = db.query(User).filter(User.id == user.id).first()
    if persisted:
        db.delete(persisted)
        db.commit()


@pytest.fixture
def admin_headers(client, admin_user):
    """Provide Bearer token auth headers for the admin user."""
    res = client.post("/api/auth/login", json={
        "email": "admin@example.com",
        "password": "AdminPass123",
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
