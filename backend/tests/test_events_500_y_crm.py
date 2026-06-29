"""
Test suite — Forzar 500 en POST /events + evento CRM correcto
=============================================================

Escenarios
----------
  500 por fallo en DB        db.add() lanza excepción → el endpoint devuelve 500
  500 por fallo en commit    db.commit() lanza excepción → el endpoint devuelve 500
  CRM ticket.creado          evento válido → 202 con status "acknowledged"
  CRM interaccion.creada     evento válido → 202
  CRM ticket.sla_violado     evento válido → 202
  Respuesta nunca 500        ante payload válido el Literal del schema no rompe
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


# =============================================================================
# Payloads
# =============================================================================

CRM_TICKET_CREADO = {
    "source": "crm",
    "event_type": "ticket.creado",
    "payload": {
        "ticket_id": "TK-TEST-001",
        "asunto": "No puedo iniciar sesión",
        "estado": "Abierto",
        "prioridad": "Alta",
        "canal": "Email",
        "source_project": "auth",
        "cliente_identidad_id": "CLI-999",
        "email": "cliente@test.cl",
        "fecha_vencimiento_sla": "2026-06-30T10:00:00Z",
    },
}

CRM_INTERACCION = {
    "source": "crm",
    "event_type": "interaccion.creada",
    "payload": {
        "interaccion_id": "INT-TEST-001",
        "ticket_id": "TK-TEST-001",
        "autor_tipo": "agente",
        "autor_id": "AGT-001",
        "contenido": "Revisando el problema de acceso.",
        "es_nota_interna": False,
        "creado_en": "2026-06-28T10:00:00Z",
    },
}

CRM_SLA_VIOLADO = {
    "source": "crm",
    "event_type": "ticket.sla_violado",
    "payload": {
        "ticket_id": "TK-TEST-001",
        "prioridad": "Alta",
        "canal": "Email",
        "sla_threshold_hours": 8.0,
        "elapsed_hours": 10.5,
        "breach_percentage": 131.0,
        "escalation_required": True,
        "violation_detected_at": "2026-06-28T10:30:00Z",
    },
}


# =============================================================================
# Forzar 500 — fallos en la capa de base de datos
# =============================================================================

class TestForzar500:
    """
    Simula condiciones que deben devolver 500.
    El endpoint captura excepciones de DB y las convierte en HTTP 500.
    """

    def test_500_cuando_db_add_lanza_excepcion(self, client: TestClient, mock_db: MagicMock):
        """db.add() falla (ej: tabla no existe, conexión caída) → 500."""
        mock_db.add.side_effect = OperationalError(
            "could not connect to server", None, None
        )
        response = client.post("/v1/events", json=CRM_TICKET_CREADO)
        assert response.status_code == 500

    def test_500_cuando_db_commit_lanza_excepcion(self, client: TestClient, mock_db: MagicMock):
        """commit() falla (ej: constraint violation, deadlock) → 500."""
        mock_db.commit.side_effect = OperationalError(
            "deadlock detected", None, None
        )
        response = client.post("/v1/events", json=CRM_TICKET_CREADO)
        assert response.status_code == 500

    def test_500_no_llama_commit_despues_del_fallo(self, client: TestClient, mock_db: MagicMock):
        """Cuando add() falla, no debe intentar hacer commit."""
        mock_db.add.side_effect = OperationalError("connection reset", None, None)
        client.post("/v1/events", json=CRM_TICKET_CREADO)
        mock_db.commit.assert_not_called()

    def test_payload_valido_no_produce_500(self, client: TestClient, mock_db: MagicMock):
        """
        Verifica que el fix del Literal["acknowledged"] funciona:
        antes del fix, este request devolvía 500 por ValidationError en el schema.
        """
        response = client.post("/v1/events", json=CRM_TICKET_CREADO)
        assert response.status_code != 500
        assert response.status_code == 202


# =============================================================================
# Evento CRM correcto — happy path
# =============================================================================

class TestCRMEventoCorrecto:
    """Verifica que los eventos CRM se ingresan correctamente tras el fix."""

    def test_ticket_creado_devuelve_202(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=CRM_TICKET_CREADO)
        assert response.status_code == 202

    def test_respuesta_tiene_status_evento_recibido(self, client: TestClient, mock_db: MagicMock):
        """El campo status debe ser exactamente 'acknowledged', no otro valor."""
        body = client.post("/v1/events", json=CRM_TICKET_CREADO).json()
        assert body["status"] == "acknowledged"

    def test_respuesta_tiene_event_id_uuid_v4(self, client: TestClient, mock_db: MagicMock):
        body = client.post("/v1/events", json=CRM_TICKET_CREADO).json()
        parsed = uuid.UUID(body["event_id"])
        assert parsed.version == 4

    def test_source_crm_almacenado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=CRM_TICKET_CREADO)
        saved = mock_db.add.call_args[0][0]
        assert saved.source == "crm"
        assert saved.event_type == "ticket.creado"

    def test_payload_ticket_almacenado_integro(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=CRM_TICKET_CREADO)
        p = mock_db.add.call_args[0][0].payload
        assert p["ticket_id"] == "TK-TEST-001"
        assert p["prioridad"] == "Alta"
        assert p["canal"] == "Email"

    def test_interaccion_creada_devuelve_202(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=CRM_INTERACCION)
        assert response.status_code == 202
        assert response.json()["status"] == "acknowledged"

    def test_interaccion_source_y_tipo_correctos(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=CRM_INTERACCION)
        saved = mock_db.add.call_args[0][0]
        assert saved.source == "crm"
        assert saved.event_type == "interaccion.creada"

    def test_sla_violado_devuelve_202(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=CRM_SLA_VIOLADO)
        assert response.status_code == 202
        assert response.json()["status"] == "acknowledged"

    def test_sla_payload_metricas_almacenadas(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=CRM_SLA_VIOLADO)
        p = mock_db.add.call_args[0][0].payload
        assert p["sla_threshold_hours"] == 8.0
        assert p["elapsed_hours"] == 10.5
        assert p["breach_percentage"] == 131.0
        assert p["escalation_required"] is True

    def test_dos_eventos_generan_ids_distintos(self, client: TestClient, mock_db: MagicMock):
        id1 = client.post("/v1/events", json=CRM_TICKET_CREADO).json()["event_id"]
        id2 = client.post("/v1/events", json=CRM_INTERACCION).json()["event_id"]
        assert id1 != id2
