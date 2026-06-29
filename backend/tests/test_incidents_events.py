"""
Suite de tests — eventos de Soporte / Incidents (Proyecto 09 → Módulo Incidents).

Contratos de payload alineados con el procesador ETL:
  Tipos de evento : incident_created | incident_upsert | incident_assigned
                    | incident_status_changed | incident_resolved

  Severidades     : critical | high | medium | low
  Estados         : open | investigating | resolved
  SLA             : sla_met (bool), resolution_time_hours (float)

Ciclo completo de un incidente:
  incident_created → incident_assigned → incident_status_changed → incident_resolved
"""

import uuid as _uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.raw.raw_events import RawEvent


# =============================================================================
# Payloads canónicos — contratos de evento acordados
# =============================================================================

# ── 1. Creación ──────────────────────────────────────────────────────────────
INCIDENT_CREATED = {
    "source": "incidents",
    "event_type": "incident_created",
    "payload": {
        "incident_id": "INC-2026-00500",
        "title": "Servidor de pagos no responde",
        "severity": "critical",
        "status": "open",
        "assignee": None,
        "opened_at": "2026-06-28T08:00:00Z",
        "source_project": "pagos",
    },
}

# ── 2. Upsert (alias idempotente de incident_created) ───────────────────────
INCIDENT_UPSERT = {
    "source": "incidents",
    "event_type": "incident_upsert",
    "payload": {
        "incident_id": "INC-2026-00500",
        "title": "Servidor de pagos no responde",
        "severity": "critical",
        "status": "open",
        "opened_at": "2026-06-28T08:00:00Z",
    },
}

# ── 3. Asignación ─────────────────────────────────────────────────────────────
INCIDENT_ASSIGNED = {
    "source": "incidents",
    "event_type": "incident_assigned",
    "payload": {
        "incident_id": "INC-2026-00500",
        "assignee": "devops-alice",
        "assigned_at": "2026-06-28T08:05:00Z",
    },
}

# ── 4. Cambio de estado ───────────────────────────────────────────────────────
INCIDENT_STATUS_CHANGED = {
    "source": "incidents",
    "event_type": "incident_status_changed",
    "payload": {
        "incident_id": "INC-2026-00500",
        "status": "investigating",
        "severity": "high",
        "changed_at": "2026-06-28T08:10:00Z",
    },
}

# ── 5. Resolución ─────────────────────────────────────────────────────────────
INCIDENT_RESOLVED = {
    "source": "incidents",
    "event_type": "incident_resolved",
    "payload": {
        "incident_id": "INC-2026-00500",
        "status": "resolved",
        "resolved_at": "2026-06-28T10:00:00Z",
        "resolution_time_hours": 2.0,
        "sla_met": True,
        "resolution_notes": "Reinicio del servicio de pagos; causa: timeout en pool de conexiones",
    },
}


# =============================================================================
# Helper
# =============================================================================

def _saved(mock_db: MagicMock) -> RawEvent:
    assert mock_db.add.call_count >= 1, "db.add() nunca fue llamado"
    return mock_db.add.call_args[0][0]


# =============================================================================
# 1. incident_created — apertura del incidente
# =============================================================================

class TestIncidentCreated:
    def test_202(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=INCIDENT_CREATED).status_code == 202

    def test_source_es_incidents(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_CREATED)
        assert _saved(mock_db).source == "incidents"

    def test_event_type_correcto(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_CREATED)
        assert _saved(mock_db).event_type == "incident_created"

    def test_incident_id_presente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_CREATED)
        assert "incident_id" in _saved(mock_db).payload

    def test_severity_enum_valido(self, client: TestClient, mock_db: MagicMock):
        """Enum de severidad: critical | high | medium | low."""
        client.post("/v1/events", json=INCIDENT_CREATED)
        assert _saved(mock_db).payload["severity"] in {"critical", "high", "medium", "low"}

    def test_status_inicial_es_open(self, client: TestClient, mock_db: MagicMock):
        """El estado inicial de un incidente debe ser 'open'."""
        client.post("/v1/events", json=INCIDENT_CREATED)
        assert _saved(mock_db).payload["status"] == "open"

    def test_opened_at_presente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_CREATED)
        assert "opened_at" in _saved(mock_db).payload

    def test_source_project_para_segmentacion(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_CREATED)
        assert "source_project" in _saved(mock_db).payload


# =============================================================================
# 2. incident_upsert — alias idempotente de incident_created
# =============================================================================

class TestIncidentUpsert:
    def test_202(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=INCIDENT_UPSERT).status_code == 202

    def test_event_type_es_incident_upsert(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_UPSERT)
        assert _saved(mock_db).event_type == "incident_upsert"

    def test_incident_id_consistente_con_created(self, client: TestClient, mock_db: MagicMock):
        """El upsert referencia el mismo incident_id que el incident_created."""
        client.post("/v1/events", json=INCIDENT_UPSERT)
        assert _saved(mock_db).payload["incident_id"] == INCIDENT_CREATED["payload"]["incident_id"]

    def test_doble_envio_idempotente(self, client: TestClient, mock_db: MagicMock):
        """Dos upserts del mismo incidente no deben fallar — idempotencia."""
        r1 = client.post("/v1/events", json=INCIDENT_UPSERT)
        r2 = client.post("/v1/events", json=INCIDENT_UPSERT)
        assert r1.status_code == 202
        assert r2.status_code == 202


# =============================================================================
# 3. incident_assigned — asignación a un agente
# =============================================================================

class TestIncidentAssigned:
    def test_202(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=INCIDENT_ASSIGNED).status_code == 202

    def test_event_type_correcto(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_ASSIGNED)
        assert _saved(mock_db).event_type == "incident_assigned"

    def test_assignee_presente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_ASSIGNED)
        assert "assignee" in _saved(mock_db).payload

    def test_incident_id_consistente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_ASSIGNED)
        assert (
            _saved(mock_db).payload["incident_id"]
            == INCIDENT_CREATED["payload"]["incident_id"]
        )

    def test_assigned_at_presente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_ASSIGNED)
        assert "assigned_at" in _saved(mock_db).payload


# =============================================================================
# 4. incident_status_changed — transición de estado
# =============================================================================

class TestIncidentStatusChanged:
    def test_202(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=INCIDENT_STATUS_CHANGED).status_code == 202

    def test_status_enum_valido(self, client: TestClient, mock_db: MagicMock):
        """Enum de estados: open | investigating | resolved."""
        client.post("/v1/events", json=INCIDENT_STATUS_CHANGED)
        assert _saved(mock_db).payload["status"] in {"open", "investigating", "resolved"}

    def test_status_investigating_en_payload(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_STATUS_CHANGED)
        assert _saved(mock_db).payload["status"] == "investigating"

    def test_severity_puede_actualizarse(self, client: TestClient, mock_db: MagicMock):
        """La severidad puede cambiar junto con el estado."""
        client.post("/v1/events", json=INCIDENT_STATUS_CHANGED)
        assert _saved(mock_db).payload["severity"] in {"critical", "high", "medium", "low"}

    def test_incident_id_consistente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_STATUS_CHANGED)
        assert (
            _saved(mock_db).payload["incident_id"]
            == INCIDENT_CREATED["payload"]["incident_id"]
        )


# =============================================================================
# 5. incident_resolved — cierre del incidente
# =============================================================================

class TestIncidentResolved:
    def test_202(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=INCIDENT_RESOLVED).status_code == 202

    def test_status_resolved_en_payload(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_RESOLVED)
        assert _saved(mock_db).payload["status"] == "resolved"

    def test_resolved_at_presente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_RESOLVED)
        assert "resolved_at" in _saved(mock_db).payload

    def test_resolution_time_hours_es_float(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_RESOLVED)
        assert isinstance(_saved(mock_db).payload["resolution_time_hours"], float)

    def test_resolution_time_positivo(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_RESOLVED)
        assert _saved(mock_db).payload["resolution_time_hours"] > 0

    def test_sla_met_es_booleano(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INCIDENT_RESOLVED)
        assert isinstance(_saved(mock_db).payload["sla_met"], bool)

    def test_incident_id_consistente_ciclo_completo(self, client: TestClient, mock_db: MagicMock):
        """El incident_id es constante a lo largo de todo el ciclo de vida."""
        client.post("/v1/events", json=INCIDENT_RESOLVED)
        assert (
            _saved(mock_db).payload["incident_id"]
            == INCIDENT_CREATED["payload"]["incident_id"]
        )

    def test_sin_campos_no_resolucion(self, client: TestClient, mock_db: MagicMock):
        """
        incident_resolved no debe tener campos de asignación (assignee).
        Esos cambios viajan por incident_assigned.
        """
        client.post("/v1/events", json=INCIDENT_RESOLVED)
        p = _saved(mock_db).payload
        assert "assignee" not in p


# =============================================================================
# 6. Ciclo de vida completo — secuencia de eventos para un mismo INC
# =============================================================================

class TestCicloVidaCompleto:
    def test_ciclo_creado_asignado_investigando_resuelto(
        self, client: TestClient, mock_db: MagicMock
    ):
        """Todos los eventos del ciclo deben ser aceptados (202)."""
        for evento in [
            INCIDENT_CREATED,
            INCIDENT_ASSIGNED,
            INCIDENT_STATUS_CHANGED,
            INCIDENT_RESOLVED,
        ]:
            r = client.post("/v1/events", json=evento)
            assert r.status_code == 202, f"Fallo en {evento['event_type']}"

    def test_todos_los_eventos_comparten_incident_id(
        self, client: TestClient, mock_db: MagicMock
    ):
        """El incident_id debe ser el mismo en cada fase del ciclo."""
        iid = INCIDENT_CREATED["payload"]["incident_id"]
        for evento in [
            INCIDENT_CREATED,
            INCIDENT_ASSIGNED,
            INCIDENT_STATUS_CHANGED,
            INCIDENT_RESOLVED,
        ]:
            mock_db.reset_mock()
            client.post("/v1/events", json=evento)
            assert _saved(mock_db).payload["incident_id"] == iid


# =============================================================================
# 7. Validaciones generales — rechaza payloads inválidos
# =============================================================================

class TestIncidentsValidaciones:
    def test_missing_source_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {k: v for k, v in INCIDENT_CREATED.items() if k != "source"}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()

    def test_missing_event_type_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {k: v for k, v in INCIDENT_CREATED.items() if k != "event_type"}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()

    def test_payload_como_lista_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {**INCIDENT_CREATED, "payload": ["esto", "no", "es", "un", "objeto"]}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()

    def test_payload_vacio_acepta_202(self, client: TestClient, mock_db: MagicMock):
        """
        El endpoint acepta payload vacío — la validación de incident_id
        ocurre en el procesador ETL, no en el ingreso al Bronze Layer.
        """
        minimal = {
            "source": "incidents",
            "event_type": "incident_created",
            "payload": {},
        }
        assert client.post("/v1/events", json=minimal).status_code == 202