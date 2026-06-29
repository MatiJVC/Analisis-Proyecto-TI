"""
Test suite — POST /events (event ingestion endpoint)
=====================================================

Coverage
--------
  Caso Exitoso 1  Proyecto 03 – Pedidos:   pedido_creado
  Caso Exitoso 2  Proyecto 07 – CRM:       ticket.resuelto (with pedido_id_ref + KB)
  Caso Exitoso 3  Proyecto 07 – SLA:       ticket.sla_violado (criticality thresholds)
  Casos Fallidos  missing fields, wrong types, corrupt JSON
  Audit metadata  event_id (UUID v4) and ingested_at (UTC) generated server-side

All tests run without a live database.  See conftest.py for fixture design.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.raw.raw_events import RawEvent


# =============================================================================
# Realistic ecosystem payloads
# =============================================================================

# Proyecto 03 — Orders system
ORDERS_PEDIDO_CREADO = {
    "source": "orders",
    "event_type": "pedido_creado",
    "payload": {
        "order_id": "ORD-2026-78901",
        "customer_id": "CLI-4567",
        "channel": "app_movil",
        "total_amount": 149990,
        "currency": "CLP",
        "items": [
            {
                "sku": "PROD-001",
                "name": "Laptop Pro 14",
                "qty": 1,
                "unit_price": 149990,
            }
        ],
        "shipping_address": "Av. Providencia 1234, Santiago",
        "payment_method": "tarjeta_credito",
        "order_date": "2026-05-21T14:30:00Z",
    },
}

# Proyecto 07 — CRM: resolved ticket cross-referencing an order + KB article usage
CRM_TICKET_RESUELTO = {
    "source": "crm",
    "event_type": "ticket.resuelto",
    "payload": {
        "ticket_id": "TKT-2026-00342",
        "customer_id": "CLI-4567",
        "pedido_id_ref": "ORD-2026-78901",   # cross-domain foreign key
        "priority": "high",
        "category": "logistica",
        "created_at": "2026-05-21T09:00:00Z",
        "resolved_at": "2026-05-21T14:45:00Z",
        "resolution_time_hours": 5.75,
        "within_sla": True,
        "assigned_agent_id": "AGT-089",
        "kb_articulo_usado": True,            # knowledge-base article usage flag
        "kb_articulo_id": "KB-LOGISTICA-012",
        "resolution_notes": "Coordinado con operador logístico para reentrega",
    },
}

# Proyecto 07 — CRM SLA: breach alert with criticality thresholds
CRM_SLA_VIOLADO = {
    "source": "crm",
    "event_type": "ticket.sla_violado",
    "payload": {
        "ticket_id": "TKT-2026-00399",
        "customer_id": "CLI-8910",
        "priority": "critical",
        "sla_threshold_hours": 4,
        "elapsed_hours": 6.5,
        "breach_percentage": 62.5,
        "category": "pagos",
        "assigned_agent_id": "AGT-044",
        "escalation_required": True,
        "alert_sent_to": ["supervisor@empresa.cl", "ops@empresa.cl"],
        "created_at": "2026-05-21T08:00:00Z",
        "sla_deadline": "2026-05-21T12:00:00Z",
        "current_time": "2026-05-21T14:30:00Z",
    },
}


# =============================================================================
# Internal helper
# =============================================================================

def _saved_event(mock_db: MagicMock) -> RawEvent:
    """
    Return the RawEvent instance that was passed to db.add() by create_event().

    The object is a real in-memory SQLAlchemy instance — not a mock — so
    attribute access (event_id, ingested_at, payload, …) works normally.
    """
    assert mock_db.add.call_count >= 1, "db.add() was never called — nothing was persisted"
    return mock_db.add.call_args[0][0]


# =============================================================================
# Caso Exitoso 1 — Proyecto 03 Pedidos: pedido_creado
# =============================================================================

class TestOrdersPedidoCreado:
    """Happy-path for an order creation event from Proyecto 03."""

    def test_returns_202_accepted(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        assert response.status_code == 202

    def test_response_status_is_acknowledged(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        assert response.json()["status"] == "acknowledged"

    def test_response_contains_valid_uuid_event_id(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        returned_id = response.json()["event_id"]
        parsed = uuid.UUID(returned_id)     # raises ValueError if not a valid UUID
        assert parsed.version == 4

    def test_db_receives_correct_source_and_event_type(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        saved = _saved_event(mock_db)
        assert saved.source == "orders"
        assert saved.event_type == "pedido_creado"

    def test_full_payload_stored_intact(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        saved = _saved_event(mock_db)
        p = saved.payload
        assert p["order_id"] == "ORD-2026-78901"
        assert p["channel"] == "app_movil"
        assert p["total_amount"] == 149990
        assert p["currency"] == "CLP"
        assert len(p["items"]) == 1
        assert p["items"][0]["sku"] == "PROD-001"

    def test_audit_event_id_in_db_matches_response(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        saved = _saved_event(mock_db)
        assert str(saved.event_id) == response.json()["event_id"]

    def test_audit_ingested_at_is_set_in_db(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        saved = _saved_event(mock_db)
        assert saved.ingested_at is not None
        assert saved.ingested_at.tzinfo is not None, "ingested_at must be timezone-aware (UTC)"

    def test_db_commit_called(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        mock_db.commit.assert_called()


# =============================================================================
# Caso Exitoso 2 — Proyecto 07 CRM: ticket.resuelto
# (pedido_id_ref cross-reference + resolution time + KB usage)
# =============================================================================

class TestCRMTicketResuelto:
    """Happy-path for a CRM resolved-ticket event from Proyecto 07."""

    def test_returns_202_accepted(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=CRM_TICKET_RESUELTO)
        assert response.status_code == 202

    def test_response_shape(self, client: TestClient, mock_db: MagicMock):
        body = client.post("/v1/events", json=CRM_TICKET_RESUELTO).json()
        assert body["status"] == "acknowledged"
        assert "event_id" in body

    def test_source_and_event_type_stored(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=CRM_TICKET_RESUELTO)
        saved = _saved_event(mock_db)
        assert saved.source == "crm"
        assert saved.event_type == "ticket.resuelto"

    def test_cross_domain_reference_preserved(self, client: TestClient, mock_db: MagicMock):
        """pedido_id_ref links this CRM ticket back to the Orders domain."""
        client.post("/v1/events", json=CRM_TICKET_RESUELTO)
        saved = _saved_event(mock_db)
        assert saved.payload["pedido_id_ref"] == "ORD-2026-78901"

    def test_resolution_time_and_sla_flag_preserved(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=CRM_TICKET_RESUELTO)
        p = _saved_event(mock_db).payload
        assert p["resolution_time_hours"] == 5.75
        assert p["within_sla"] is True

    def test_kb_article_usage_flags_preserved(self, client: TestClient, mock_db: MagicMock):
        """kb.articulo.usado and kb.articulo.id must reach the warehouse intact."""
        client.post("/v1/events", json=CRM_TICKET_RESUELTO)
        p = _saved_event(mock_db).payload
        assert p["kb_articulo_usado"] is True
        assert p["kb_articulo_id"] == "KB-LOGISTICA-012"

    def test_iso8601_timestamps_stored_as_strings(self, client: TestClient, mock_db: MagicMock):
        """Timestamps inside payload are plain strings — not parsed by the ingestion layer."""
        client.post("/v1/events", json=CRM_TICKET_RESUELTO)
        p = _saved_event(mock_db).payload
        assert p["created_at"] == "2026-05-21T09:00:00Z"
        assert p["resolved_at"] == "2026-05-21T14:45:00Z"

    def test_two_identical_payloads_get_different_event_ids(
        self, client: TestClient, mock_db: MagicMock
    ):
        """UUIDs must be unique even for duplicate payloads."""
        r1 = client.post("/v1/events", json=CRM_TICKET_RESUELTO).json()["event_id"]
        r2 = client.post("/v1/events", json=CRM_TICKET_RESUELTO).json()["event_id"]
        assert r1 != r2


# =============================================================================
# Caso Exitoso 3 — Proyecto 07 CRM SLA: ticket.sla_violado
# (breach threshold, criticality indicators, alert recipients)
# =============================================================================

class TestCRMSLAViolado:
    """Happy-path for an SLA breach alert event from Proyecto 07."""

    def test_returns_202_accepted(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=CRM_SLA_VIOLADO)
        assert response.status_code == 202

    def test_event_type_stored_correctly(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=CRM_SLA_VIOLADO)
        saved = _saved_event(mock_db)
        assert saved.event_type == "ticket.sla_violado"
        assert saved.source == "crm"

    def test_criticality_thresholds_stored(self, client: TestClient, mock_db: MagicMock):
        """SLA threshold, elapsed time and breach % are the core analytics metrics."""
        client.post("/v1/events", json=CRM_SLA_VIOLADO)
        p = _saved_event(mock_db).payload
        assert p["priority"] == "critical"
        assert p["sla_threshold_hours"] == 4
        assert p["elapsed_hours"] == 6.5
        assert p["breach_percentage"] == 62.5

    def test_escalation_flag_stored(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=CRM_SLA_VIOLADO)
        assert _saved_event(mock_db).payload["escalation_required"] is True

    def test_alert_recipients_stored_as_list(self, client: TestClient, mock_db: MagicMock):
        """Multi-value fields (list of emails) must survive JSON round-trip."""
        client.post("/v1/events", json=CRM_SLA_VIOLADO)
        recipients = _saved_event(mock_db).payload["alert_sent_to"]
        assert isinstance(recipients, list)
        assert len(recipients) == 2
        assert "supervisor@empresa.cl" in recipients

    def test_sla_deadline_stored(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=CRM_SLA_VIOLADO)
        assert _saved_event(mock_db).payload["sla_deadline"] == "2026-05-21T12:00:00Z"

    def test_audit_columns_present(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=CRM_SLA_VIOLADO)
        saved = _saved_event(mock_db)
        assert isinstance(saved.event_id, uuid.UUID)
        assert saved.ingested_at is not None
        assert str(saved.event_id) == response.json()["event_id"]


# =============================================================================
# Casos Fallidos — validation rejects garbage before reaching the DB
# =============================================================================

class TestValidationFailures:
    """All invalid inputs must return 422 and never call db.add()."""

    # --- missing required fields -------------------------------------------

    def test_missing_source_returns_422(self, client: TestClient, mock_db: MagicMock):
        response = client.post(
            "/v1/events",
            json={"event_type": "pedido_creado", "payload": {"order_id": "ORD-001"}},
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    def test_missing_event_type_returns_422(self, client: TestClient, mock_db: MagicMock):
        response = client.post(
            "/v1/events",
            json={"source": "orders", "payload": {"order_id": "ORD-001"}},
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    def test_completely_empty_body_returns_422(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json={})
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    # --- constraint violations ---------------------------------------------

    def test_empty_source_string_returns_422(self, client: TestClient, mock_db: MagicMock):
        """min_length=1 on source — empty string is not allowed."""
        response = client.post(
            "/v1/events",
            json={"source": "", "event_type": "pedido_creado", "payload": {}},
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    def test_empty_event_type_string_returns_422(self, client: TestClient, mock_db: MagicMock):
        response = client.post(
            "/v1/events",
            json={"source": "orders", "event_type": "", "payload": {}},
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    def test_source_exceeding_max_length_returns_422(self, client: TestClient, mock_db: MagicMock):
        """max_length=50 on source."""
        response = client.post(
            "/v1/events",
            json={"source": "x" * 51, "event_type": "any", "payload": {}},
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    # --- wrong payload types -----------------------------------------------

    def test_payload_as_string_returns_422(self, client: TestClient, mock_db: MagicMock):
        """payload must be a JSON object — a string is rejected."""
        response = client.post(
            "/v1/events",
            json={
                "source": "orders",
                "event_type": "pedido_creado",
                "payload": "this is not an object",
            },
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    def test_payload_as_array_returns_422(self, client: TestClient, mock_db: MagicMock):
        """Arrays are not valid payload — schema requires a JSON object."""
        response = client.post(
            "/v1/events",
            json={
                "source": "orders",
                "event_type": "pedido_creado",
                "payload": [1, 2, 3],
            },
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    def test_payload_as_integer_returns_422(self, client: TestClient, mock_db: MagicMock):
        response = client.post(
            "/v1/events",
            json={"source": "orders", "event_type": "pedido_creado", "payload": 99},
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    def test_payload_as_null_returns_422(self, client: TestClient, mock_db: MagicMock):
        response = client.post(
            "/v1/events",
            json={"source": "orders", "event_type": "pedido_creado", "payload": None},
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    # --- malformed HTTP body -----------------------------------------------

    def test_corrupt_json_body_returns_422(self, client: TestClient, mock_db: MagicMock):
        """Truncated JSON — FastAPI must reject before Pydantic even runs."""
        response = client.post(
            "/v1/events",
            content=b'{"source": "orders", "event_type": "pedido_creado", "payload":',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
        mock_db.add.assert_not_called()

    # --- error response shape -----------------------------------------------

    def test_422_response_contains_detail_key(self, client: TestClient, mock_db: MagicMock):
        """All validation errors must return a parseable detail for debugging."""
        response = client.post("/v1/events", json={"event_type": "pedido_creado"})
        body = response.json()
        assert "detail" in body
        assert isinstance(body["detail"], list)
        assert len(body["detail"]) >= 1

    def test_422_detail_names_missing_field(self, client: TestClient, mock_db: MagicMock):
        """The error detail must identify which field is missing."""
        response = client.post("/v1/events", json={"event_type": "pedido_creado"})
        detail = response.json()["detail"]
        fields_in_error = [
            str(e.get("loc", "")) for e in detail
        ]
        assert any("source" in f for f in fields_in_error)


# =============================================================================
# Audit metadata — server-side generation guarantees
# =============================================================================

class TestAuditMetadata:
    """
    Verify that event_id and ingested_at are ALWAYS generated by the server.
    The client sends only source / event_type / payload — nothing else.
    """

    def test_event_id_is_uuid_v4(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        event_id = uuid.UUID(response.json()["event_id"])
        assert event_id.version == 4

    def test_event_id_in_db_is_uuid_instance(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        saved = _saved_event(mock_db)
        assert isinstance(saved.event_id, uuid.UUID), (
            f"Expected uuid.UUID, got {type(saved.event_id)}"
        )

    def test_event_id_db_matches_response(self, client: TestClient, mock_db: MagicMock):
        """The UUID the client receives must be the same one stored in the DB."""
        response = client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        saved = _saved_event(mock_db)
        assert str(saved.event_id) == response.json()["event_id"]

    def test_ingested_at_is_timezone_aware_utc(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        saved = _saved_event(mock_db)
        assert saved.ingested_at.tzinfo is not None, "ingested_at must carry tz info"
        offset_seconds = saved.ingested_at.utcoffset().total_seconds()
        assert offset_seconds == 0.0, f"Expected UTC (offset=0 s), got {offset_seconds} s"

    def test_ingested_at_is_close_to_now(self, client: TestClient, mock_db: MagicMock):
        """ingested_at must be within 3 seconds of the test execution."""
        before = datetime.now(tz=timezone.utc)
        client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        after = datetime.now(tz=timezone.utc)
        saved = _saved_event(mock_db)
        assert before <= saved.ingested_at <= after, (
            f"ingested_at={saved.ingested_at} not in window [{before}, {after}]"
        )

    def test_two_requests_get_different_event_ids(self, client: TestClient, mock_db: MagicMock):
        id1 = client.post("/v1/events", json=ORDERS_PEDIDO_CREADO).json()["event_id"]
        id2 = client.post("/v1/events", json=CRM_TICKET_RESUELTO).json()["event_id"]
        assert id1 != id2

    def test_client_cannot_inject_event_id(self, client: TestClient, mock_db: MagicMock):
        """
        Even if a client sends event_id in the body, it must be ignored.
        EventCreate schema has no event_id field — Pydantic strips unknown keys.
        """
        payload_with_injected_id = {
            **ORDERS_PEDIDO_CREADO,
            "event_id": "00000000-0000-0000-0000-000000000000",
        }
        response = client.post("/v1/events", json=payload_with_injected_id)
        assert response.status_code == 202
        returned_id = response.json()["event_id"]
        assert returned_id != "00000000-0000-0000-0000-000000000000"

    def test_client_cannot_inject_ingested_at(self, client: TestClient, mock_db: MagicMock):
        """ingested_at is not in the client schema — injection attempts are silently dropped."""
        payload_with_injected_ts = {
            **ORDERS_PEDIDO_CREADO,
            "ingested_at": "1970-01-01T00:00:00Z",
        }
        response = client.post("/v1/events", json=payload_with_injected_ts)
        assert response.status_code == 202
        # The DB value must NOT be the epoch injected by the client
        saved = _saved_event(mock_db)
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        assert abs((saved.ingested_at - epoch).total_seconds()) > 1_000_000

    def test_processed_flag_defaults_to_false(self, client: TestClient, mock_db: MagicMock):
        """New events enter the Bronze layer unprocessed — ETL promotes them later."""
        client.post("/v1/events", json=ORDERS_PEDIDO_CREADO)
        saved = _saved_event(mock_db)
        assert saved.processed is False

    def test_no_db_write_on_validation_failure(self, client: TestClient, mock_db: MagicMock):
        """Nothing must touch the DB when the input is rejected by Pydantic."""
        client.post("/v1/events", json={"source": ""})
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
