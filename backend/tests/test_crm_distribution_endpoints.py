"""
Tests para los endpoints de distribución de CRM (canal, prioridad, dominio de
origen, críticos por módulo). Archivo separado de test_crm_analytics_endpoints.py,
que documenta explícitamente "los cuatro endpoints" originales de kpis_crm.py.
"""
from fastapi.testclient import TestClient


_DISTRIBUTION = {
    "total": 10,
    "items": [
        {"name": "Chat", "count": 6, "percentage": 60.0},
        {"name": "Email", "count": 4, "percentage": 40.0},
    ],
}


class TestCRMChannels:
    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_tickets_by_channel", lambda db: _DISTRIBUTION)
        resp = client.get("/v1/kpis/crm/channels")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 10
        assert len(body["items"]) == 2

    def test_500_on_service_failure(self, client: TestClient, monkeypatch):
        def raise_error(db):
            raise RuntimeError("boom")

        monkeypatch.setattr("app.api.routes.kpis_crm.get_tickets_by_channel", raise_error)
        resp = client.get("/v1/kpis/crm/channels")
        assert resp.status_code == 500


class TestCRMPriority:
    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_tickets_by_priority", lambda db: _DISTRIBUTION)
        resp = client.get("/v1/kpis/crm/priority")
        assert resp.status_code == 200
        assert resp.json()["total"] == 10

    def test_500_on_service_failure(self, client: TestClient, monkeypatch):
        def raise_error(db):
            raise RuntimeError("boom")

        monkeypatch.setattr("app.api.routes.kpis_crm.get_tickets_by_priority", raise_error)
        resp = client.get("/v1/kpis/crm/priority")
        assert resp.status_code == 500


class TestCRMSourceProjects:
    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_tickets_by_source_project", lambda db: _DISTRIBUTION)
        resp = client.get("/v1/kpis/crm/source-projects")
        assert resp.status_code == 200
        assert resp.json()["total"] == 10

    def test_500_on_service_failure(self, client: TestClient, monkeypatch):
        def raise_error(db):
            raise RuntimeError("boom")

        monkeypatch.setattr("app.api.routes.kpis_crm.get_tickets_by_source_project", raise_error)
        resp = client.get("/v1/kpis/crm/source-projects")
        assert resp.status_code == 500


class TestCRMCriticalByModule:
    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_critical_tickets_by_module", lambda db: _DISTRIBUTION)
        resp = client.get("/v1/kpis/crm/critical-by-module")
        assert resp.status_code == 200
        assert resp.json()["total"] == 10

    def test_500_on_service_failure(self, client: TestClient, monkeypatch):
        def raise_error(db):
            raise RuntimeError("boom")

        monkeypatch.setattr("app.api.routes.kpis_crm.get_critical_tickets_by_module", raise_error)
        resp = client.get("/v1/kpis/crm/critical-by-module")
        assert resp.status_code == 500
