import os
# Force a hermetic in-memory DB BEFORE importing app modules (engine is built at import time).
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("GEMINI_API_KEY", "")  # ensure rule-based fallback in tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
get_settings.cache_clear()  # drop any cached settings so the env override above takes effect

from app.core.database import Base, get_db
import app.models  # noqa: F401
from app.main import create_app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    app = create_app()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _register(client, email, password, full_name, role):
    return client.post("/auth/register", json={
        "email": email, "password": password, "full_name": full_name, "role": role,
    })


def _login(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


@pytest.fixture()
def customer_token(client):
    _register(client, "cust@x.com", "secret1", "Cust", "customer")
    return _login(client, "cust@x.com", "secret1")


@pytest.fixture()
def agent_token(client):
    _register(client, "agent@x.com", "secret1", "Agent", "agent")
    return _login(client, "agent@x.com", "secret1")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
