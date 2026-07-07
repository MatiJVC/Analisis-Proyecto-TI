"""
Tests para el cliente HTTP del CRM externo (crm_external_client.py).

Cubre get_ticket_estado(): éxito, no encontrado, api_key inválida,
api_key no configurada, timeout, error de red. Se mockea
app.services.crm_external_client.httpx.get vía monkeypatch (no se hace
una llamada de red real en ningún caso).
"""
import httpx
import pytest


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


class TestGetTicketEstado:
    def test_api_key_no_configurada_raises_auth_error(self, monkeypatch):
        import app.services.crm_external_client as client
        monkeypatch.setattr(client, "CRM_EXTERNAL_API_KEY", None)
        with pytest.raises(client.CRMExternalAuthError):
            client.get_ticket_estado("TKT-1")

    def test_exito_devuelve_ticket(self, monkeypatch):
        import app.services.crm_external_client as client
        monkeypatch.setattr(client, "CRM_EXTERNAL_API_KEY", "secret")

        def fake_get(url, params=None, timeout=None):
            return _FakeResponse(200, {"ok": True, "ticket": {"ticket_id": "TKT-1", "estado": "abierto"}})

        monkeypatch.setattr(client.httpx, "get", fake_get)
        result = client.get_ticket_estado("TKT-1")
        assert result == {"ticket_id": "TKT-1", "estado": "abierto"}

    def test_exito_normaliza_id_a_ticket_id(self, monkeypatch):
        """El TicketDto real del CRM externo usa `id`, no `ticket_id`
        (confirmado jul-2026 contra un ticket real: ver respuesta del equipo
        del CRM). get_ticket_estado debe normalizar para que
        CRMExternalTicketResponse (que exige `ticket_id`) no falle."""
        import app.services.crm_external_client as client
        monkeypatch.setattr(client, "CRM_EXTERNAL_API_KEY", "secret")

        real_ticket = {
            "id": "bbd7fb0e-5aa1-4b6a-8bb1-3216ea8fd057",
            "asunto": "Asistencia Informatica",
            "estado": "resuelto",
            "prioridad": "alta",
            "canal": "email",
            "cliente_id": 12,
            "cliente_nombre": "Enzo Inostroza",
            "agente_id": "p7.agent@ucn.cl",
            "fecha_vencimiento_sla": "2026-07-06T07:39:37.606Z",
            "pedido_id_ref": None,
            "suscripcion_id_ref": None,
            "pago_id_ref": None,
            "salud_ref": None,
            "descripcion": None,
            "resolucion": "revisar pagina web",
            "creado_en": "2026-07-05T07:39:37.672Z",
            "actualizado_en": "2026-07-05T07:42:16.568Z",
        }

        def fake_get(url, params=None, timeout=None):
            return _FakeResponse(200, {"ok": True, "ticket": real_ticket})

        monkeypatch.setattr(client.httpx, "get", fake_get)
        result = client.get_ticket_estado(real_ticket["id"])
        assert result["ticket_id"] == real_ticket["id"]
        assert result["id"] == real_ticket["id"]  # no se elimina el original, solo se agrega el alias

    def test_ok_sin_campo_ticket_raises_error(self, monkeypatch):
        import app.services.crm_external_client as client
        monkeypatch.setattr(client, "CRM_EXTERNAL_API_KEY", "secret")

        def fake_get(url, params=None, timeout=None):
            return _FakeResponse(200, {"ok": True})

        monkeypatch.setattr(client.httpx, "get", fake_get)
        with pytest.raises(client.CRMExternalError):
            client.get_ticket_estado("TKT-1")

    def test_no_encontrado_raises_not_found(self, monkeypatch):
        import app.services.crm_external_client as client
        monkeypatch.setattr(client, "CRM_EXTERNAL_API_KEY", "secret")

        def fake_get(url, params=None, timeout=None):
            return _FakeResponse(404, {"ok": False, "message": "Ticket no encontrado"})

        monkeypatch.setattr(client.httpx, "get", fake_get)
        with pytest.raises(client.CRMExternalNotFoundError):
            client.get_ticket_estado("TKT-404")

    def test_api_key_invalida_raises_auth_error(self, monkeypatch):
        import app.services.crm_external_client as client
        monkeypatch.setattr(client, "CRM_EXTERNAL_API_KEY", "secret-invalido")

        def fake_get(url, params=None, timeout=None):
            return _FakeResponse(401, {"ok": False, "message": "api_key inválida"})

        monkeypatch.setattr(client.httpx, "get", fake_get)
        with pytest.raises(client.CRMExternalAuthError):
            client.get_ticket_estado("TKT-1")

    def test_error_generico_raises_crm_external_error(self, monkeypatch):
        import app.services.crm_external_client as client
        monkeypatch.setattr(client, "CRM_EXTERNAL_API_KEY", "secret")

        def fake_get(url, params=None, timeout=None):
            return _FakeResponse(500, {"ok": False, "message": "Error interno del CRM"})

        monkeypatch.setattr(client.httpx, "get", fake_get)
        with pytest.raises(client.CRMExternalError):
            client.get_ticket_estado("TKT-1")

    def test_timeout_raises_timeout_error(self, monkeypatch):
        import app.services.crm_external_client as client
        monkeypatch.setattr(client, "CRM_EXTERNAL_API_KEY", "secret")

        def fake_get(url, params=None, timeout=None):
            raise httpx.TimeoutException("timed out")

        monkeypatch.setattr(client.httpx, "get", fake_get)
        with pytest.raises(client.CRMExternalTimeoutError):
            client.get_ticket_estado("TKT-1")

    def test_error_de_red_raises_generic_error(self, monkeypatch):
        import app.services.crm_external_client as client
        monkeypatch.setattr(client, "CRM_EXTERNAL_API_KEY", "secret")

        def fake_get(url, params=None, timeout=None):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(client.httpx, "get", fake_get)
        with pytest.raises(client.CRMExternalError):
            client.get_ticket_estado("TKT-1")
