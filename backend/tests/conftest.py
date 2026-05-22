"""
Shared fixtures para los tests del Proyecto 09.

Setup:
1. DATABASE_URL se setea antes de importar cualquier módulo de la app.
2. Base.metadata.create_all se parchea para evitar conexión real a la BD al importar.
3. Cada test obtiene un MagicMock(spec=Session) fresco — no requiere BD real.
4. mock_db.refresh simula el autoincrement del PK entero de la BD.
"""

import os
from unittest.mock import patch, MagicMock

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test_db",
)
os.environ.setdefault("SQL_ECHO", "False")

with patch("sqlalchemy.MetaData.create_all"):
    from main import app
    from app.db import get_db

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


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
