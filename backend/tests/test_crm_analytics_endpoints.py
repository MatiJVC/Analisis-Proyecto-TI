"""
Tests de endpoints HTTP del módulo CRM/Soporte.

Cubre los cuatro endpoints expuestos en kpis_crm.py:
  GET /v1/kpis/crm/kpis
  GET /v1/kpis/crm/timeline
  GET /v1/kpis/crm/tickets
  GET /v1/kpis/crm/sla

Para cada endpoint:
  • 200 con respuesta válida (servicio mockeado)
  • Campos requeridos presentes en la respuesta
  • Parámetros de query propagados correctamente al servicio
  • 422 para parámetros inválidos (fuera de rango)
  • 500 cuando el servicio subyacente falla
"""

import pytest
from fastapi.testclient import TestClient

# ─── Minimal canonical service responses ─────────────────────────────────────

_KPI_DATA = {
    "totalCustomers":        1250,
    "openTickets":           38,
    "avgResponseTimeMinutes": 14.5,
    "criticalTickets":       7,
    "ticketsCreatedToday":   12,
    "resolutionRate":        91.3,
}

_TIMELINE_POINT = {"date": "2026-06-10", "opened": 12, "resolved": 9}

_TICKET_ROW = {
    "ticketId":      "TKT-2026-00500",
    "asunto":        "Pedido no llegó",
    "estado":        "Abierto",
    "prioridad":     "Alta",
    "canal":         "Chat",
    "sourceProject": "orders",
    "openedAt":      "2026-06-10T09:00:00Z",
    "updatedAt":     "2026-06-10T10:30:00Z",
}

_SLA_DATA = {
    "totalViolations":    5,
    "criticalViolations": 2,
    "slaComplianceRate":  96.8,
    "ticketsEvaluated":   120,
}


def _patch_all(monkeypatch):
    """Silencia todos los servicios CRM para evitar llamadas reales."""
    monkeypatch.setattr("app.api.routes.kpis_crm.get_crm_kpis",      lambda db: _KPI_DATA)
    monkeypatch.setattr("app.api.routes.kpis_crm.get_crm_timeline",   lambda db, days: [_TIMELINE_POINT])
    monkeypatch.setattr("app.api.routes.kpis_crm.get_recent_tickets", lambda db, limit: [_TICKET_ROW])
    monkeypatch.setattr("app.api.routes.kpis_crm.get_sla_summary",    lambda db: _SLA_DATA)


# ─── GET /v1/kpis/crm/kpis ───────────────────────────────────────────────────

class TestCRMKPIs:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_crm_kpis", lambda db: _KPI_DATA)
        assert client.get("/v1/kpis/crm/kpis").status_code == 200

    def test_response_contains_all_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_crm_kpis", lambda db: _KPI_DATA)
        body = client.get("/v1/kpis/crm/kpis").json()
        for field in ("totalCustomers", "openTickets", "avgResponseTimeMinutes",
                      "criticalTickets", "ticketsCreatedToday", "resolutionRate"):
            assert field in body, f"Campo faltante: {field}"

    def test_numeric_fields_are_numbers(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_crm_kpis", lambda db: _KPI_DATA)
        body = client.get("/v1/kpis/crm/kpis").json()
        assert isinstance(body["totalCustomers"], int)
        assert isinstance(body["resolutionRate"], float)

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_crm_kpis",
            lambda db: (_ for _ in ()).throw(RuntimeError("DB down")),
        )
        assert client.get("/v1/kpis/crm/kpis").status_code == 500


# ─── GET /v1/kpis/crm/timeline ───────────────────────────────────────────────

class TestCRMTimeline:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_crm_timeline",
            lambda db, days: [_TIMELINE_POINT],
        )
        assert client.get("/v1/kpis/crm/timeline").status_code == 200

    def test_response_has_days_and_points(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_crm_timeline",
            lambda db, days: [_TIMELINE_POINT],
        )
        body = client.get("/v1/kpis/crm/timeline").json()
        assert "days" in body
        assert "points" in body
        assert isinstance(body["points"], list)

    def test_default_days_is_14(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, days):
            received["days"] = days
            return [_TIMELINE_POINT]
        monkeypatch.setattr("app.api.routes.kpis_crm.get_crm_timeline", _capture)
        client.get("/v1/kpis/crm/timeline")
        assert received["days"] == 14

    def test_custom_days_passed_to_service(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, days):
            received["days"] = days
            return [_TIMELINE_POINT]
        monkeypatch.setattr("app.api.routes.kpis_crm.get_crm_timeline", _capture)
        client.get("/v1/kpis/crm/timeline?days=30")
        assert received["days"] == 30

    def test_each_point_has_required_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_crm_timeline",
            lambda db, days: [_TIMELINE_POINT],
        )
        points = client.get("/v1/kpis/crm/timeline").json()["points"]
        for p in points:
            for field in ("date", "opened", "resolved"):
                assert field in p, f"Campo faltante en punto: {field}"

    def test_days_zero_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/kpis/crm/timeline?days=0").status_code == 422

    def test_days_over_90_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/kpis/crm/timeline?days=91").status_code == 422

    def test_empty_timeline_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_crm_timeline",
            lambda db, days: [],
        )
        body = client.get("/v1/kpis/crm/timeline").json()
        assert body["points"] == []

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_crm_timeline",
            lambda db, days: (_ for _ in ()).throw(RuntimeError("timeout")),
        )
        assert client.get("/v1/kpis/crm/timeline").status_code == 500


# ─── GET /v1/kpis/crm/tickets ────────────────────────────────────────────────

class TestCRMTickets:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_recent_tickets",
            lambda db, limit: [_TICKET_ROW],
        )
        assert client.get("/v1/kpis/crm/tickets").status_code == 200

    def test_response_has_tickets_list(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_recent_tickets",
            lambda db, limit: [_TICKET_ROW],
        )
        body = client.get("/v1/kpis/crm/tickets").json()
        assert "tickets" in body
        assert isinstance(body["tickets"], list)
        assert len(body["tickets"]) == 1

    def test_each_ticket_has_required_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_recent_tickets",
            lambda db, limit: [_TICKET_ROW],
        )
        ticket = client.get("/v1/kpis/crm/tickets").json()["tickets"][0]
        for field in ("ticketId", "asunto", "estado", "prioridad",
                      "canal", "sourceProject", "openedAt", "updatedAt"):
            assert field in ticket, f"Campo faltante: {field}"

    def test_default_limit_is_10(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, limit):
            received["limit"] = limit
            return [_TICKET_ROW]
        monkeypatch.setattr("app.api.routes.kpis_crm.get_recent_tickets", _capture)
        client.get("/v1/kpis/crm/tickets")
        assert received["limit"] == 10

    def test_custom_limit_passed_to_service(self, client: TestClient, monkeypatch):
        received = {}
        def _capture(db, limit):
            received["limit"] = limit
            return [_TICKET_ROW]
        monkeypatch.setattr("app.api.routes.kpis_crm.get_recent_tickets", _capture)
        client.get("/v1/kpis/crm/tickets?limit=25")
        assert received["limit"] == 25

    def test_limit_zero_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/kpis/crm/tickets?limit=0").status_code == 422

    def test_limit_over_100_returns_422(self, client: TestClient, monkeypatch):
        _patch_all(monkeypatch)
        assert client.get("/v1/kpis/crm/tickets?limit=101").status_code == 422

    def test_empty_tickets_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_recent_tickets",
            lambda db, limit: [],
        )
        body = client.get("/v1/kpis/crm/tickets").json()
        assert body["tickets"] == []

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_recent_tickets",
            lambda db, limit: (_ for _ in ()).throw(RuntimeError("query fail")),
        )
        assert client.get("/v1/kpis/crm/tickets").status_code == 500


# ─── GET /v1/kpis/crm/sla ────────────────────────────────────────────────────

class TestCRMSLA:

    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_sla_summary", lambda db: _SLA_DATA)
        assert client.get("/v1/kpis/crm/sla").status_code == 200

    def test_response_has_sla_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_sla_summary", lambda db: _SLA_DATA)
        body = client.get("/v1/kpis/crm/sla").json()
        for field in ("totalViolations", "criticalViolations", "slaComplianceRate"):
            assert field in body, f"Campo faltante: {field}"

    def test_sla_compliance_is_percentage(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_sla_summary", lambda db: _SLA_DATA)
        body = client.get("/v1/kpis/crm/sla").json()
        rate = body["slaComplianceRate"]
        assert 0.0 <= rate <= 100.0, f"slaComplianceRate fuera de rango: {rate}"

    def test_violations_are_integers(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_sla_summary", lambda db: _SLA_DATA)
        body = client.get("/v1/kpis/crm/sla").json()
        assert isinstance(body["totalViolations"],    int)
        assert isinstance(body["criticalViolations"], int)

    def test_critical_violations_lte_total(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_sla_summary", lambda db: _SLA_DATA)
        body = client.get("/v1/kpis/crm/sla").json()
        assert body["criticalViolations"] <= body["totalViolations"]

    def test_zero_violations_is_valid(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_sla_summary",
            lambda db: {"totalViolations": 0, "criticalViolations": 0, "slaComplianceRate": 100.0},
        )
        body = client.get("/v1/kpis/crm/sla").json()
        assert body["totalViolations"] == 0
        assert body["slaComplianceRate"] == 100.0

    def test_service_error_returns_500(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "app.api.routes.kpis_crm.get_sla_summary",
            lambda db: (_ for _ in ()).throw(RuntimeError("sla fail")),
        )
        assert client.get("/v1/kpis/crm/sla").status_code == 500
