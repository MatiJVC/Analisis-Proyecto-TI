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
        {"reason": "Fondos insuficientes", "count": 30, "percentage": 60.0},
        {"reason": "Tarjeta rechazada", "count": 20, "percentage": 40.0},
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
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _patch_all(monkeypatch):
    """Silencia todos los servicios de pagos para evitar llamadas reales."""
    monkeypatch.setattr("app.pagos.routes.analytics.get_payment_kpis",    lambda db, hours: _KPI_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_payment_timeline", lambda db, hours: _TIMELINE_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_failure_reasons",  lambda db, hours, top_n: _FAILURES_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_conciliation_summary", lambda db, hours: _CONCILIATION_DATA)
    monkeypatch.setattr("app.pagos.routes.analytics.get_sla_status",       lambda db, hours: _SLA_DATA)


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

    def test_returns_200_with_data_envelope(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_timeline",
            lambda db, hours: _TIMELINE_DATA,
        )
        response = client.get("/v1/analytics/payments/timeline")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert isinstance(body["data"], list)
        assert len(body["data"]) == 2

    def test_each_point_has_required_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_timeline",
            lambda db, hours: _TIMELINE_DATA,
        )
        body = client.get("/v1/analytics/payments/timeline").json()
        for point in body["data"]:
            for field in ("date", "successful", "failed", "amount"):
                assert field in point, f"Missing field '{field}' in timeline point"

    def test_hours_over_168_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/analytics/payments/timeline?hours=169").status_code == 422

    def test_empty_timeline_returns_empty_data(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.pagos.routes.analytics.get_payment_timeline",
            lambda db, hours: [],
        )
        response = client.get("/v1/analytics/payments/timeline")
        assert response.status_code == 200
        assert response.json() == {"data": []}

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
                      "recent_alerts"):
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
