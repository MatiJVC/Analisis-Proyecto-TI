"""
Tests de endpoints analytics/payments/* — Finding 9.1.

Cubre todos los endpoints del módulo de pagos:
  GET /v1/analytics/payments/kpis
  GET /v1/analytics/payments/timeline
  GET /v1/analytics/payments/failures
  GET /v1/analytics/payments/conciliation
  GET /v1/analytics/payments/sla

Para cada endpoint:
  • 200 con respuesta válida
  • 422 para parámetros de query inválidos (fuera de rango)
  • 500 cuando el servicio subyacente falla
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# ─── Canonical minimal service responses ─────────────────────────────────────

_KPI_DATA = {
    "totalTransactions": 1000,
    "failedPayments": 50,
    "failureRate": 5.0,
    "revenue": 85000.0,
    "avgTransactionValue": 89.47,
    "uptime": 99.9,
}

_TIMELINE_DATA = [
    {"date": "10:00", "successful": 200, "failed": 3, "amount": 14000.0},
    {"date": "11:00", "successful": 180, "failed": 5, "amount": 12600.0},
]

_FAILURES_DATA = {
    "rejection_rate": 5.0,
    "total": 1000,
    "failed": 50,
    "reasons": [
        {"reason": "Fondos insuficientes", "categoria": "tarjeta", "count": 30, "percentage": 60.0},
        {"reason": "Proveedor no disponible", "categoria": "proveedor", "count": 20, "percentage": 40.0},
    ],
}

_CONCILIATION_DATA = {
    "statuses": [
        {"status": "Aprobado", "count": 950, "percentage": 95.0},
        {"status": "esperando_revisión", "count": 50, "percentage": 5.0},
    ],
    "total": 1000,
    "approval_rate": 95.0,
}

_SLA_DATA = {
    "uptime_pct": 99.9,
    "sla_ok": True,
    "sla_threshold": 99.5,
    "active_events": [],
    "recent_alerts": [],
    "alert_created": False,
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

_METHODS_DATA = {
    "methods": [
        {"name": "Tarjeta de Crédito", "value": 48.5, "count": 21820},
        {"name": "Tarjeta de Débito",  "value": 27.3, "count": 12288},
        {"name": "Transferencia",      "value": 14.2, "count": 6394},
        {"name": "Billetera Digital",  "value": 10.0, "count": 4500},
    ],
    "total": 45002,
}


_SLA_TIMELINE_DATA = [
    {"date": "2026-07-05", "downtimeMinutes": 30.0, "degradedMinutes": 5.0},
    {"date": "2026-07-06", "downtimeMinutes": 0.0,  "degradedMinutes": 0.0},
]


def _patch_all(monkeypatch):
    """Silencia todos los servicios de pagos para evitar llamadas reales."""
    monkeypatch.setattr("app.pagos.routes.analytics.get_payment_kpis",    lambda db, hours: _KPI_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_payment_timeline", lambda db, hours: _TIMELINE_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_failure_reasons",  lambda db, hours, top_n: _FAILURES_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_conciliation_summary", lambda db, hours: _CONCILIATION_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_sla_status",       lambda db, hours: _SLA_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_sla_timeline",     lambda db, days: _SLA_TIMELINE_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_payment_methods",  lambda db, hours: _METHODS_DATA)


# ─── GET /v1/analytics/payments/kpis ─────────────────────────────────────────

class TestPaymentKPIs:

    def test_returns_200_with_valid_data(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_kpis",
            lambda db, hours: _KPI_DATA,
        )
        response = client.get("/v1/analytics/payments/kpis")
        assert response.status_code == 200

    def test_response_contains_all_kpi_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_kpis",
            lambda db, hours: _KPI_DATA,
        )
        body = client.get("/v1/analytics/payments/kpis").json()
        for field in ("totalTransactions", "failedPayments", "failureRate", "revenue",
                      "avgTransactionValue", "uptime"):
            assert field in body, f"Missing field: {field}"

    def test_default_hours_parameter_accepted(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, hours):
            received["hours"] = hours
            return _KPI_DATA
        monkeypatch.setattr("app.pagos.routes.analytics.get_payment_kpis", _capture)
        client.get("/v1/analytics/payments/kpis")
        assert received["hours"] == 24

    def test_custom_hours_passed_to_service(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, hours):
            received["hours"] = hours
            return _KPI_DATA
        monkeypatch.setattr("app.pagos.routes.analytics.get_payment_kpis", _capture)
        client.get("/v1/analytics/payments/kpis?hours=48")
        assert received["hours"] == 48

    def test_hours_zero_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/kpis?hours=0").status_code == 422

    def test_hours_over_max_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/kpis?hours=8761").status_code == 422

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_kpis",
            lambda db, hours: (_ for _ in ()).throw(RuntimeError("DB down")),
        )
        assert client.get("/v1/analytics/payments/kpis").status_code == 500


# ─── GET /v1/analytics/payments/timeline ─────────────────────────────────────

class TestPaymentTimeline:

    def test_returns_200_list(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_timeline",
            lambda db, hours: _TIMELINE_DATA,
        )
        response = client.get("/v1/analytics/payments/timeline")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 2

    def test_each_point_has_required_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_timeline",
            lambda db, hours: _TIMELINE_DATA,
        )
        points = client.get("/v1/analytics/payments/timeline").json()
        for point in points:
            for field in ("date", "successful", "failed", "amount"):
                assert field in point, f"Missing field '{field}' in timeline point"

    def test_hours_over_168_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/timeline?hours=169").status_code == 422

    def test_empty_timeline_returns_empty_list(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_timeline",
            lambda db, hours: [],
        )
        response = client.get("/v1/analytics/payments/timeline")
        assert response.status_code == 200
        assert response.json() == []

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_timeline",
            lambda db, hours: (_ for _ in ()).throw(RuntimeError("timeout")),
        )
        assert client.get("/v1/analytics/payments/timeline").status_code == 500


# ─── GET /v1/analytics/payments/failures ─────────────────────────────────────

class TestPaymentFailures:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_failure_reasons",
            lambda db, hours, top_n: _FAILURES_DATA,
        )
        assert client.get("/v1/analytics/payments/failures").status_code == 200

    def test_response_shape(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_failure_reasons",
            lambda db, hours, top_n: _FAILURES_DATA,
        )
        body = client.get("/v1/analytics/payments/failures").json()
        assert "rejection_rate" in body
        assert "reasons" in body
        assert isinstance(body["reasons"], list)

    def test_reasons_include_categoria(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_failure_reasons",
            lambda db, hours, top_n: _FAILURES_DATA,
        )
        body = client.get("/v1/analytics/payments/failures").json()
        assert body["reasons"][0]["categoria"] == "tarjeta"
        assert body["reasons"][1]["categoria"] == "proveedor"

    def test_top_n_defaults_to_10(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, hours, top_n):
            received["top_n"] = top_n
            return _FAILURES_DATA
        monkeypatch.setattr("app.pagos.routes.analytics.get_failure_reasons", _capture)
        client.get("/v1/analytics/payments/failures")
        assert received["top_n"] == 10

    def test_top_n_over_50_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/failures?top_n=51").status_code == 422

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_failure_reasons",
            lambda db, hours, top_n: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        assert client.get("/v1/analytics/payments/failures").status_code == 500


# ─── GET /v1/analytics/payments/conciliation ─────────────────────────────────

class TestPaymentConciliation:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_conciliation_summary",
            lambda db, hours: _CONCILIATION_DATA,
        )
        assert client.get("/v1/analytics/payments/conciliation").status_code == 200

    def test_response_has_statuses_list(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_conciliation_summary",
            lambda db, hours: _CONCILIATION_DATA,
        )
        body = client.get("/v1/analytics/payments/conciliation").json()
        assert isinstance(body["statuses"], list)
        assert "approval_rate" in body

    def test_hours_out_of_range_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/conciliation?hours=0").status_code == 422

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_conciliation_summary",
            lambda db, hours: (_ for _ in ()).throw(ValueError("schema error")),
        )
        assert client.get("/v1/analytics/payments/conciliation").status_code == 500


# ─── GET /v1/analytics/payments/methods ─────────────────────────────────────

class TestPaymentMethods:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_methods",
            lambda db, hours: _METHODS_DATA,
        )
        assert client.get("/v1/analytics/payments/methods").status_code == 200

    def test_response_has_methods_list_and_total(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_methods",
            lambda db, hours: _METHODS_DATA,
        )
        body = client.get("/v1/analytics/payments/methods").json()
        assert "methods" in body
        assert "total" in body
        assert isinstance(body["methods"], list)
        assert len(body["methods"]) == 4

    def test_each_method_has_name_value_count(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_methods",
            lambda db, hours: _METHODS_DATA,
        )
        methods = client.get("/v1/analytics/payments/methods").json()["methods"]
        for m in methods:
            assert "name" in m, "Missing field: name"
            assert "value" in m, "Missing field: value"
            assert "count" in m, "Missing field: count"

    def test_default_hours_is_24(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, hours):
            received["hours"] = hours
            return _METHODS_DATA
        monkeypatch.setattr("app.pagos.routes.analytics.get_payment_methods", _capture)
        client.get("/v1/analytics/payments/methods")
        assert received["hours"] == 24

    def test_custom_hours_passed_to_service(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, hours):
            received["hours"] = hours
            return _METHODS_DATA
        monkeypatch.setattr("app.pagos.routes.analytics.get_payment_methods", _capture)
        client.get("/v1/analytics/payments/methods?hours=72")
        assert received["hours"] == 72

    def test_hours_zero_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/methods?hours=0").status_code == 422

    def test_hours_over_max_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/methods?hours=8761").status_code == 422

    def test_empty_methods_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_methods",
            lambda db, hours: {"methods": [], "total": 0},
        )
        response = client.get("/v1/analytics/payments/methods")
        assert response.status_code == 200
        assert response.json()["methods"] == []
        assert response.json()["total"] == 0

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_methods",
            lambda db, hours: (_ for _ in ()).throw(RuntimeError("DB down")),
        )
        assert client.get("/v1/analytics/payments/methods").status_code == 500


# ─── GET /v1/analytics/payments/sla ──────────────────────────────────────────

class TestPaymentSLA:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_sla_status",
            lambda db, hours: _SLA_DATA,
        )
        assert client.get("/v1/analytics/payments/sla").status_code == 200

    def test_response_has_sla_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_sla_status",
            lambda db, hours: _SLA_DATA,
        )
        body = client.get("/v1/analytics/payments/sla").json()
        for field in ("uptime_pct", "sla_ok", "sla_threshold", "active_events",
                      "recent_alerts", "alert_created"):
            assert field in body, f"Missing field: {field}"

    def test_sla_ok_true_when_uptime_above_threshold(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_sla_status",
            lambda db, hours: {**_SLA_DATA, "uptime_pct": 99.9, "sla_ok": True},
        )
        body = client.get("/v1/analytics/payments/sla").json()
        assert body["sla_ok"] is True
        assert body["uptime_pct"] == 99.9

    def test_hours_over_720_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/sla?hours=721").status_code == 422

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_sla_status",
            lambda db, hours: (_ for _ in ()).throw(RuntimeError("sla fail")),
        )
        assert client.get("/v1/analytics/payments/sla").status_code == 500


# ─── GET /v1/analytics/payments/sla/timeline ─────────────────────────────────

class TestPaymentSlaTimeline:

    def test_returns_200_list(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_sla_timeline",
            lambda db, days: _SLA_TIMELINE_DATA,
        )
        resp = client.get("/v1/analytics/payments/sla/timeline")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_each_point_has_required_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_sla_timeline",
            lambda db, days: _SLA_TIMELINE_DATA,
        )
        body = client.get("/v1/analytics/payments/sla/timeline").json()
        for point in body:
            for field in ("date", "downtimeMinutes", "degradedMinutes"):
                assert field in point, f"Missing field: {field}"

    def test_default_days_is_14(self, client: TestClient, monkeypatch):
        captured = {}
        def _capture(db, days):
            captured["days"] = days
            return _SLA_TIMELINE_DATA
        monkeypatch.setattr("app.pagos.routes.analytics.get_sla_timeline", _capture)
        client.get("/v1/analytics/payments/sla/timeline")
        assert captured["days"] == 14

    def test_days_over_90_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/sla/timeline?days=91").status_code == 422

    def test_days_zero_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/sla/timeline?days=0").status_code == 422

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_sla_timeline",
            lambda db, days: (_ for _ in ()).throw(RuntimeError("timeline fail")),
        )
        assert client.get("/v1/analytics/payments/sla/timeline").status_code == 500
