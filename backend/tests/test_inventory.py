"""
Tests de endpoints inventory/* — Finding 9.1.

Cubre todos los endpoints del módulo de inventario:
  GET /v1/inventory/kpis
  GET /v1/inventory/stock-status
  GET /v1/inventory/snapshot
  GET /v1/inventory/locations/catalog
  GET /v1/inventory/products/thresholds

Para cada endpoint:
  • 200 con respuesta válida (servicio mockeado)
  • 422 para parámetros de query inválidos
  • 500 cuando el servicio subyacente falla
"""

import pytest
from fastapi.testclient import TestClient

# ─── Minimal mock service returns ────────────────────────────────────────────

_KPI_DATA = {
    "total_skus": 42,
    "total_stock_value": 0.0,
    "warehouses_count": 3,
    "low_stock_count": 5,
    "out_of_stock_count": 2,
    "turnover_rate": 0.0,
}

_SNAPSHOT_ROW = {
    "inventory_id": "inv-001",
    "sku_id": "SKU-001",
    "product_name": "Producto A",
    "category": "Cat A",
    "location_id": "loc-001",
    "location_name": "Bodega Central",
    "location_type": "WAREHOUSE",
    "city": "Santiago",
    "physical_stock": 100,
    "reserved_stock": 10,
    "available_stock": 90,
    "critical_threshold": 20,
    "stock_status": "NORMAL",
    "last_updated": "2026-06-11T00:00:00Z",
}

_LOCATION_ROW = {
    "location_id": "loc-001",
    "location_name": "Bodega Central",
    "location_type": "WAREHOUSE",
    "address": "Av. Principal 123",
    "city": "Santiago",
    "country": "Chile",
    "is_active": True,
    "capacity_m2": None,
}

_THRESHOLD_ROW = {
    "sku_id": "SKU-001",
    "product_name": "Producto A",
    "category": "Cat A",
    "critical_threshold": 20,
    "total_physical_stock": 15,
    "total_reserved_stock": 0,
    "total_available_stock": 15,
    "locations_count": 1,
    "is_below_threshold": True,
    "is_out_of_stock": False,
    "last_updated": "2026-06-11T00:00:00Z",
}

_STOCK_STATUS_DATA = [
    {"status": "NORMAL", "count": 30, "percentage": 71.4},
    {"status": "CRITICAL", "count": 5, "percentage": 11.9},
    {"status": "OUT_OF_STOCK", "count": 7, "percentage": 16.7},
]

_GENERATED_AT = "2026-06-11T00:00:00Z"


def _patch_now(monkeypatch):
    monkeypatch.setattr("app.api.routes.inventory._now_utc_iso", lambda: _GENERATED_AT)


# ─── GET /v1/inventory/kpis ───────────────────────────────────────────────────

class TestInventoryKPIs:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.inventory.get_inventory_kpis", lambda db: _KPI_DATA)
        _patch_now(monkeypatch)
        assert client.get("/v1/inventory/kpis").status_code == 200

    def test_response_contains_all_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.inventory.get_inventory_kpis", lambda db: _KPI_DATA)
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/kpis").json()
        for field in ("total_skus", "warehouses_count", "low_stock_count",
                      "out_of_stock_count", "generated_at"):
            assert field in body, f"Missing field: {field}"

    def test_generated_at_present(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.inventory.get_inventory_kpis", lambda db: _KPI_DATA)
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/kpis").json()
        assert body["generated_at"] == _GENERATED_AT

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_inventory_kpis",
            lambda db: (_ for _ in ()).throw(RuntimeError("DB down")),
        )
        assert client.get("/v1/inventory/kpis").status_code == 500


# ─── GET /v1/inventory/stock-status ──────────────────────────────────────────

class TestInventoryStockStatus:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_stock_status_summary",
            lambda db: (_STOCK_STATUS_DATA, 42),
        )
        _patch_now(monkeypatch)
        assert client.get("/v1/inventory/stock-status").status_code == 200

    def test_response_has_data_list(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_stock_status_summary",
            lambda db: (_STOCK_STATUS_DATA, 42),
        )
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/stock-status").json()
        assert isinstance(body["data"], list)
        assert body["total_skus"] == 42

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_stock_status_summary",
            lambda db: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        assert client.get("/v1/inventory/stock-status").status_code == 500


# ─── GET /v1/inventory/snapshot ──────────────────────────────────────────────

class TestInventorySnapshot:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_inventory_snapshot",
            lambda db, sku_id, location_id, location_type, stock_status, limit, offset:
                ([_SNAPSHOT_ROW], 1),
        )
        _patch_now(monkeypatch)
        assert client.get("/v1/inventory/snapshot").status_code == 200

    def test_response_has_pagination_meta(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_inventory_snapshot",
            lambda **kw: ([_SNAPSHOT_ROW], 1),
        )
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/snapshot").json()
        assert "meta" in body
        meta = body["meta"]
        for key in ("total", "limit", "offset", "pages", "has_next", "has_prev"):
            assert key in meta, f"Missing pagination key: {key}"

    def test_limit_defaults_to_100(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, sku_id, location_id, location_type, stock_status, limit, offset):
            received["limit"] = limit
            return [], 0
        monkeypatch.setattr("app.api.routes.inventory.get_inventory_snapshot", _capture)
        _patch_now(monkeypatch)
        client.get("/v1/inventory/snapshot")
        assert received["limit"] == 100

    def test_limit_over_500_returns_422(self, client: TestClient, monkeypatch):
        assert client.get("/v1/inventory/snapshot?limit=501").status_code == 422

    def test_limit_zero_returns_422(self, client: TestClient, monkeypatch):
        assert client.get("/v1/inventory/snapshot?limit=0").status_code == 422

    def test_offset_parameter_passed_through(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, sku_id, location_id, location_type, stock_status, limit, offset):
            received["offset"] = offset
            return [], 0
        monkeypatch.setattr("app.api.routes.inventory.get_inventory_snapshot", _capture)
        _patch_now(monkeypatch)
        client.get("/v1/inventory/snapshot?offset=50")
        assert received["offset"] == 50

    def test_sku_id_filter_passed_to_service(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, sku_id, location_id, location_type, stock_status, limit, offset):
            received["sku_id"] = sku_id
            return [], 0
        monkeypatch.setattr("app.api.routes.inventory.get_inventory_snapshot", _capture)
        _patch_now(monkeypatch)
        client.get("/v1/inventory/snapshot?sku_id=SKU-PROD-001")
        assert received["sku_id"] == "SKU-PROD-001"

    def test_has_next_false_on_last_page(self, client: TestClient, monkeypatch):
        # 1 row total, limit=100, offset=0 → has_next=False
        monkeypatch.setattr(
            "app.api.routes.inventory.get_inventory_snapshot",
            lambda **kw: ([_SNAPSHOT_ROW], 1),
        )
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/snapshot").json()
        assert body["meta"]["has_next"] is False
        assert body["meta"]["has_prev"] is False

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_inventory_snapshot",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("query fail")),
        )
        assert client.get("/v1/inventory/snapshot").status_code == 500


# ─── GET /v1/inventory/locations/catalog ─────────────────────────────────────

class TestLocationsCatalog:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_locations_catalog",
            lambda db: [_LOCATION_ROW],
        )
        _patch_now(monkeypatch)
        assert client.get("/v1/inventory/locations/catalog").status_code == 200

    def test_response_contains_data_and_total(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_locations_catalog",
            lambda db: [_LOCATION_ROW],
        )
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/locations/catalog").json()
        assert "data" in body
        assert body["total"] == 1

    def test_response_contains_location_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_locations_catalog",
            lambda db: [_LOCATION_ROW],
        )
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/locations/catalog").json()
        row = body["data"][0]
        for field in ("location_id", "location_name", "location_type", "is_active"):
            assert field in row, f"Missing field: {field}"

    def test_empty_catalog_returns_200_with_empty_list(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_locations_catalog",
            lambda db: [],
        )
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/locations/catalog").json()
        assert body["data"] == []
        assert body["total"] == 0

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_locations_catalog",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        assert client.get("/v1/inventory/locations/catalog").status_code == 500


# ─── GET /v1/inventory/products/thresholds ────────────────────────────────────

class TestProductsThresholds:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_products_thresholds",
            lambda db, sku_id, below_threshold: [_THRESHOLD_ROW],
        )
        _patch_now(monkeypatch)
        assert client.get("/v1/inventory/products/thresholds").status_code == 200

    def test_response_contains_summary_counts(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_products_thresholds",
            lambda db, sku_id, below_threshold: [_THRESHOLD_ROW],
        )
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/products/thresholds").json()
        assert "total_below_threshold" in body
        assert "total_out_of_stock" in body
        assert body["total"] == 1

    def test_below_threshold_filter_true(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, sku_id, below_threshold):
            received["below_threshold"] = below_threshold
            return [_THRESHOLD_ROW]
        monkeypatch.setattr("app.api.routes.inventory.get_products_thresholds", _capture)
        _patch_now(monkeypatch)
        client.get("/v1/inventory/products/thresholds?below_threshold=true")
        assert received["below_threshold"] is True

    def test_below_threshold_filter_false(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, sku_id, below_threshold):
            received["below_threshold"] = below_threshold
            return []
        monkeypatch.setattr("app.api.routes.inventory.get_products_thresholds", _capture)
        _patch_now(monkeypatch)
        client.get("/v1/inventory/products/thresholds?below_threshold=false")
        assert received["below_threshold"] is False

    def test_counts_below_threshold_correctly(self, client: TestClient, monkeypatch):
        rows = [
            {**_THRESHOLD_ROW, "is_below_threshold": True, "is_out_of_stock": False},
            {**_THRESHOLD_ROW, "sku_id": "SKU-002", "is_below_threshold": True, "is_out_of_stock": True},
            {**_THRESHOLD_ROW, "sku_id": "SKU-003", "is_below_threshold": False, "is_out_of_stock": False},
        ]
        monkeypatch.setattr(
            "app.api.routes.inventory.get_products_thresholds",
            lambda db, sku_id, below_threshold: rows,
        )
        _patch_now(monkeypatch)
        body = client.get("/v1/inventory/products/thresholds").json()
        assert body["total_below_threshold"] == 2
        assert body["total_out_of_stock"] == 1

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.inventory.get_products_thresholds",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        assert client.get("/v1/inventory/products/thresholds").status_code == 500
