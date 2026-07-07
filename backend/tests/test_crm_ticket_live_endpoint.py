"""
Tests para GET /v1/kpis/crm/tickets/{ticket_id}/live (consulta en vivo
del ticket contra el CRM externo). Archivo separado de
test_crm_analytics_endpoints.py, que documenta explícitamente "los cuatro
endpoints" de kpis_crm.py.
"""
from fastapi.testclient import TestClient


_LIVE_TICKET = {
    "ticket_id": "TKT-4521",
    "estado": "Progreso",
    "prioridad": "Alta",
    "canal": "Email",
    "asunto": "Problema con pago de suscripción",
}


class TestCRMTicketLive:
    def test_returns_200(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.api.routes.kpis_crm.get_ticket_estado", lambda ticket_id: _LIVE_TICKET)
        resp = client.get("/v1/kpis/crm/tickets/TKT-4521/live")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticket_id"] == "TKT-4521"
        assert body["estado"] == "Progreso"

    def test_not_found_returns_404(self, client: TestClient, monkeypatch):
        from app.services.crm_external_client import CRMExternalNotFoundError

        def raise_not_found(ticket_id):
            raise CRMExternalNotFoundError(f"Ticket '{ticket_id}' no encontrado")

        monkeypatch.setattr("app.api.routes.kpis_crm.get_ticket_estado", raise_not_found)
        resp = client.get("/v1/kpis/crm/tickets/NO-EXISTE/live")
        assert resp.status_code == 404

    def test_auth_error_returns_502(self, client: TestClient, monkeypatch):
        from app.services.crm_external_client import CRMExternalAuthError

        def raise_auth_error(ticket_id):
            raise CRMExternalAuthError("CRM_EXTERNAL_API_KEY no configurada")

        monkeypatch.setattr("app.api.routes.kpis_crm.get_ticket_estado", raise_auth_error)
        resp = client.get("/v1/kpis/crm/tickets/TKT-1/live")
        assert resp.status_code == 502

    def test_timeout_returns_504(self, client: TestClient, monkeypatch):
        from app.services.crm_external_client import CRMExternalTimeoutError

        def raise_timeout(ticket_id):
            raise CRMExternalTimeoutError("timeout")

        monkeypatch.setattr("app.api.routes.kpis_crm.get_ticket_estado", raise_timeout)
        resp = client.get("/v1/kpis/crm/tickets/TKT-1/live")
        assert resp.status_code == 504

    def test_generic_error_returns_502(self, client: TestClient, monkeypatch):
        from app.services.crm_external_client import CRMExternalError

        def raise_generic(ticket_id):
            raise CRMExternalError("error genérico")

        monkeypatch.setattr("app.api.routes.kpis_crm.get_ticket_estado", raise_generic)
        resp = client.get("/v1/kpis/crm/tickets/TKT-1/live")
        assert resp.status_code == 502

    def test_unexpected_error_returns_500(self, client: TestClient, monkeypatch):
        def raise_unexpected(ticket_id):
            raise RuntimeError("boom")

        monkeypatch.setattr("app.api.routes.kpis_crm.get_ticket_estado", raise_unexpected)
        resp = client.get("/v1/kpis/crm/tickets/TKT-1/live")
        assert resp.status_code == 500
