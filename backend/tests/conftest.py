"""
Shared pytest fixtures for the event ingestion test suite.

Boot sequence
-------------
1. Set DATABASE_URL (psycopg v3 dialect) *before* any app module is imported.
2. Patch Base.metadata.create_all so main.py does not open a real DB connection
   at import time.
3. Every test gets a fresh MagicMock(spec=Session) — no live DB required.
4. An autouse fixture suppresses _run_etl so background tasks never connect.
"""

import os
from unittest.mock import patch, MagicMock

# psycopg v3 (psycopg[binary]) is the installed driver — NOT psycopg2.
# Using "postgresql+psycopg://" ensures SQLAlchemy uses the right DBAPI.
# The URL is never actually connected to; it only needs to satisfy the driver lookup.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test_db",
)
os.environ.setdefault("SQL_ECHO", "False")

# Patch must be active while main.py is imported, because main.py calls
# Base.metadata.create_all(bind=engine) at module level.
with patch("sqlalchemy.MetaData.create_all"):
    from main import app          # noqa: E402
    from app.db import get_db     # noqa: E402

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.raw.raw_events import RawEvent  # noqa: E402


# ---------------------------------------------------------------------------
# Suppress background ETL (autouse — applies to every test)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def suppress_background_etl(monkeypatch):
    """Prevent _run_etl from opening a real DB connection after the 202 is sent."""
    monkeypatch.setattr("app.api.routes.events._run_etl", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Mock DB session
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db() -> MagicMock:
    """
    SQLAlchemy Session mock.

    create_event() builds a real in-memory RawEvent instance and calls
    db.add(instance) / db.commit() / db.refresh(instance) on this mock.
    The RawEvent has event_id and ingested_at set before db.add() — so tests
    can inspect mock_db.add.call_args[0][0] to verify what would be stored.
    """
    return MagicMock(spec=Session)


# ---------------------------------------------------------------------------
# FastAPI TestClient wired to mock_db
# ---------------------------------------------------------------------------

@pytest.fixture
def client(mock_db: MagicMock) -> TestClient:
    """
    TestClient with get_db dependency overridden to yield the mock session.

    pytest creates mock_db once per test and passes the SAME instance to both
    this fixture and any test that also requests mock_db, so call_args assertions
    work correctly.
    """
    def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
