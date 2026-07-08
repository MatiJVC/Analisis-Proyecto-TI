"""
Regresión (PostgreSQL real) — GET /products/thresholds ("Alertas de Stock Bajo").

Antes del fix, get_products_thresholds calculaba el stock SOLO desde
fact_inventory_alerts (el current_stock congelado en la alerta), ignorando los
movimientos posteriores. Un SKU cuya alerta decía "stock alto" pero que después
cayó bajo umbral por despachos quedaba INVISIBLE en la lista de alertas, aunque
los KPIs (que sí leen fact_inventory_movements) lo contaban → card vacía pese a
"Stock bajo mínimo: 1".

El fix migró la query al mismo CTE compartido (_STOCK_BASE_CTES, movimientos ∪
alertas) que usan /kpis y /stock-status. Este test lo fija contra PostgreSQL real
(usa DISTINCT ON / FILTER / BOOL_OR, sintaxis PG-específica que no corre en SQLite).

Requiere TEST_DATABASE_URL; se saltea automáticamente si no está definida
(vía el fixture pg_session). Correr con:
    TEST_DATABASE_URL=postgresql+psycopg://user:pass@host/db pytest -m integration
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.warehouse.dim_products import DimProduct
from app.models.warehouse.fact_inventory_alerts import FactInventoryAlert
from app.models.warehouse.fact_inventory_movements import FactInventoryMovement
from app.services.inventory_query_service import get_products_thresholds

pytestmark = pytest.mark.integration

_NOW = datetime.now(tz=timezone.utc)


@pytest.fixture
def _low_by_movements(pg_session):
    """SKU cuya alerta vieja decía current_stock=100 (>umbral 20), pero cuyos
    movimientos posteriores lo bajaron a 10 (<umbral): received 100 − dispatched 90."""
    sku = "TEST-SCEN-001"
    pg_session.add(DimProduct(sku_id=sku, product_name="Producto de prueba", category="Test", unit="unidad"))
    pg_session.add(FactInventoryAlert(
        event_type="critical_threshold_reached", sku_id=sku, location_id="LOC-TEST",
        current_stock=100, threshold_limite=20, is_stock_out=False,
        alert_at=_NOW - timedelta(days=2), ingested_at=_NOW - timedelta(days=2),
    ))
    pg_session.add(FactInventoryMovement(
        event_type="stock_received", sku_id=sku, location_id="LOC-TEST", quantity=100,
        movement_at=_NOW - timedelta(days=2), ingested_at=_NOW - timedelta(days=2),
    ))
    pg_session.add(FactInventoryMovement(
        event_type="stock_dispatched", sku_id=sku, location_id="LOC-TEST", quantity=90,
        movement_at=_NOW - timedelta(hours=1), ingested_at=_NOW - timedelta(hours=1),
    ))
    pg_session.flush()
    return pg_session, sku


def test_below_threshold_by_movements_is_listed(_low_by_movements):
    """El SKU aparece en below_threshold=True porque el stock físico real (movimientos)
    está bajo umbral, aunque la alerta congelada decía lo contrario."""
    db, sku = _low_by_movements
    rows = get_products_thresholds(db, sku_id=None, category=None, below_threshold=True)

    match = [r for r in rows if r["sku_id"] == sku]
    assert match, "El SKU bajo umbral por movimientos debe aparecer en la lista de alertas"
    row = match[0]
    assert row["critical_threshold"] == 20
    assert row["total_physical_stock"] == 10          # 100 recibido − 90 despachado
    assert row["is_below_threshold"] is True
    assert row["is_out_of_stock"] is False            # 10 > 0 y sin is_stock_out


def test_threshold_row_matches_kpi_low_stock_basis(_low_by_movements):
    """Consistencia: la clasificación de la lista usa stock físico, igual que el
    low_stock_count del KPI — el mismo SKU que cuenta el KPI aparece en la lista."""
    db, sku = _low_by_movements
    rows = get_products_thresholds(db, sku_id=None, category=None, below_threshold=None)
    match = [r for r in rows if r["sku_id"] == sku]
    assert match and match[0]["is_below_threshold"] is True
