import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models import User
from app.auth.security import hash_password, generate_csrf_token

from sqlalchemy.pool import StaticPool

# Test database in memory
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    user = User(
        username="testuser",
        email="testuser@example.com",
        password_hash=hash_password("Password123"),
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_client(client, test_user):
    # Fetch login page to populate session CSRF token
    resp = client.get("/login")
    session_csrf = client.session.get("csrf_token") if hasattr(client, "session") else None
    
    # Extract csrf_token from HTML if session attribute not directly accessible
    import re
    token_match = re.search(r'name="csrf_token"\s+value="([a-f0-9]+)"', resp.text)
    csrf_token = token_match.group(1) if token_match else "dummy_token"

    client.post(
        "/login",
        data={
            "identifier": "testuser",
            "password": "Password123",
            "csrf_token": csrf_token,
            "next": "/"
        },
        follow_redirects=True
    )
    return client

