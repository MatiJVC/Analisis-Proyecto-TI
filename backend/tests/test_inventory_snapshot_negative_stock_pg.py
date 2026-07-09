"""
Regresión (PostgreSQL real) — GET /inventory/snapshot con stock físico negativo.

Antes del fix, physical_from_movements (dentro de _STOCK_BASE_CTES) calculaba
el stock físico como received − dispatched + adjusted − transfer sin clampear
a cero. Un SKU×ubicación cuyos despachos superan lo recibido (eventos fuera de
orden, carga inicial no registrada, etc.) quedaba con physical_stock negativo,
lo que rompía la validación `ge=0` de InventorySnapshotRow — Pydantic lanzaba
ValidationError al serializar y el `except Exception` genérico del router lo
convertía en 500 para TODO el snapshot (no solo esa fila), dejando el gráfico
"Stock por Ubicación" del frontend sin datos.

El fix agrega GREATEST(0, ...) al cálculo de physical_stock en el CTE
compartido. Este test lo fija contra PostgreSQL real (usa FILTER, sintaxis
PG-específica que no corre en SQLite).

Requiere TEST_DATABASE_URL; se saltea automáticamente si no está definida
(vía el fixture pg_session). Correr con:
    TEST_DATABASE_URL=postgresql+psycopg://user:pass@host/db pytest -m integration
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.warehouse.fact_inventory_movements import FactInventoryMovement
from app.schemas.inventory_query_schemas import InventorySnapshotRow
from app.services.inventory_query_service import get_inventory_snapshot

pytestmark = pytest.mark.integration

_NOW = datetime.now(tz=timezone.utc)


@pytest.fixture
def _oversold_sku(pg_session):
    """SKU×ubicación con despachos (90) superando lo recibido (10) — neto -80."""
    sku = "TEST-NEG-STOCK-001"
    loc = "LOC-NEG-TEST"
    pg_session.add(FactInventoryMovement(
        event_type="stock_received", sku_id=sku, location_id=loc, quantity=10,
        movement_at=_NOW - timedelta(days=1), ingested_at=_NOW - timedelta(days=1),
    ))
    pg_session.add(FactInventoryMovement(
        event_type="stock_dispatched", sku_id=sku, location_id=loc, quantity=90,
        movement_at=_NOW, ingested_at=_NOW,
    ))
    pg_session.flush()
    return pg_session, sku


def test_snapshot_clamps_negative_physical_stock_to_zero(_oversold_sku):
    """physical_stock nunca debe ser negativo — se clampea a 0 en el CTE base."""
    db, sku = _oversold_sku
    rows, total = get_inventory_snapshot(
        db, sku_id=sku, location_id=None, location_type=None,
        stock_status=None, limit=10, offset=0,
    )

    assert total == 1
    row = rows[0]
    assert row["physical_stock"] == 0
    assert row["stock_status"] == "OUT_OF_STOCK"


def test_snapshot_row_with_oversold_sku_passes_pydantic_validation(_oversold_sku):
    """Regresión directa del 500: la fila debe serializar sin ValidationError."""
    db, sku = _oversold_sku
    rows, _ = get_inventory_snapshot(
        db, sku_id=sku, location_id=None, location_type=None,
        stock_status=None, limit=10, offset=0,
    )
    InventorySnapshotRow(**rows[0])  # no debe lanzar ValidationError
