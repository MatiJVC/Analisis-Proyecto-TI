"""
Shared fixtures para los tests del Proyecto 09.

Fixtures disponibles
────────────────────
mock_db / client  — tests HTTP (MagicMock, sin BD real)
db_engine         — SQLite in-memory, scope=session (solo crea fact_orders para
                    evitar DDL PostgreSQL-específico de raw_events: UUID PK / JSONB)
db_session        — sesión SQLAlchemy real por test; rollback al teardown
"""

import os
from unittest.mock import patch, MagicMock

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test_db",
)
os.environ.setdefault("SQL_ECHO", "False")
os.environ.setdefault("DISABLE_AUTH", "true")

with patch("sqlalchemy.MetaData.create_all"):
    from main import app
    from app.db import get_db

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import Session, sessionmaker as _sessionmaker
from sqlalchemy.pool import StaticPool as _StaticPool


# ─── Real-DB fixtures (SQLite in-memory) ─────────────────────────────────────

@pytest.fixture(scope="session")
def db_engine():
    """
    SQLite in-memory engine creado una vez por sesión de tests.
    Solo crea la tabla fact_orders — FactOrder usa tipos estándar (Integer,
    String, Float, Boolean, DateTime) que SQLite soporta sin adaptación.
    No incluye fact_raw_events porque su PK es UUID del dialecto PostgreSQL,
    cuyo DDL no es compatible con SQLite.
    """
    from app.models.warehouse.fact_orders import FactOrder

    engine = _create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=_StaticPool,
    )
    FactOrder.__table__.create(engine, checkfirst=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """
    Sesión SQLAlchemy real por test.
    Los processors llaman flush() pero no commit(), así que session.rollback()
    al teardown deja la BD vacía para el siguiente test sin recrear el esquema.
    """
    Session = _sessionmaker(bind=db_engine, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ─── Mock-DB fixtures (HTTP endpoint tests) ──────────────────────────────────

@pytest.fixture(autouse=True)
def suppress_background_etl(monkeypatch):
    """Evita que _run_etl intente abrir una SessionLocal real después del 202."""
    monkeypatch.setattr("app.api.routes.events._run_etl", lambda *a, **kw: None)


@pytest.fixture
def mock_db() -> MagicMock:
    session = MagicMock(spec=Session)
    # Simula el autoincrement del PK que la BD normalmente asigna en db.refresh()
    _counter = [0]
    def _refresh(obj):
        _counter[0] += 1
        obj.id = _counter[0]
    session.refresh.side_effect = _refresh
    return session


@pytest.fixture
def client(mock_db: MagicMock) -> TestClient:
    def _override():
        yield mock_db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
