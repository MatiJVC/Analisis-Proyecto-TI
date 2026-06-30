"""
Tests de eventos de pagos — POST /v1/events con source=payments.

Cubre el ciclo de vida completo de un pago:
  1. intento_pago       → estado esperando_revisión
  2. pago_exitoso       → estado Aprobado
  3. pago_rechazado     → estado discrepancia_de_monto / discrepancia_de_transacciones
  4. pago_reembolsado   → evento de reversión

Para cada evento se verifica:
  • HTTP 202 y status=acknowledged
  • Payload almacenado íntegro en RawEvent
  • Campos críticos para el ETL (transaction_token, amount, payment_method)
  • Validaciones 422 por campos faltantes o malformados
"""

import uuid as _uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.raw.raw_events import RawEvent


# =============================================================================
# Payloads canónicos — contratos acordados con el módulo de pagos
# =============================================================================

INTENTO_PAGO = {
    "source": "payments",
    "event_type": "intento_pago",
    "payload": {
        "transaction_token": "550e8400-e29b-41d4-a716-446655440000",
        "order_id": "ORD-2026-78901",
        "amount": 149990.00,
        "currency": "CLP",
        "payment_method": "tarjeta_credito",
        "timestamp": "2026-06-17T10:00:00Z",
    },
}

PAGO_EXITOSO = {
    "source": "payments",
    "event_type": "pago_exitoso",
    "payload": {
        "transaction_token": "550e8400-e29b-41d4-a716-446655440000",
        "order_id": "ORD-2026-78901",
        "amount": 149990.00,
        "currency": "CLP",
        "payment_method": "tarjeta_credito",
        "authorization_code": "AUTH-20260617-001",
        "timestamp": "2026-06-17T10:00:45Z",
    },
}

PAGO_RECHAZADO_MONTO = {
    "source": "payments",
    "event_type": "pago_rechazado",
    "payload": {
        "transaction_token": "660e8400-e29b-41d4-a716-446655440001",
        "order_id": "ORD-2026-78902",
        "amount": 89990.00,
        "currency": "CLP",
        "payment_method": "tarjeta_debito",
        "error_code": "ERR_MONTO_INSUFICIENTE",
        "timestamp": "2026-06-17T10:05:00Z",
    },
}

PAGO_RECHAZADO_TRANSACCION = {
    "source": "payments",
    "event_type": "pago_rechazado",
    "payload": {
        "transaction_token": "770e8400-e29b-41d4-a716-446655440002",
        "subscription_id": "SUB-2026-00123",
        "amount": 29990.00,
        "currency": "CLP",
        "payment_method": "billetera_digital",
        "error_code": "ERR_TRANSACCION_DUPLICADA",
        "timestamp": "2026-06-17T10:10:00Z",
    },
}

PAGO_REEMBOLSADO = {
    "source": "payments",
    "event_type": "pago_reembolsado",
    "payload": {
        "transaction_token": "550e8400-e29b-41d4-a716-446655440000",
        "order_id": "ORD-2026-78901",
        "amount": 149990.00,
        "currency": "CLP",
        "refund_reason": "Solicitud del cliente",
        "refunded_at": "2026-06-17T14:00:00Z",
    },
}

PAGO_SUBSCRIPTION = {
    "source": "payments",
    "event_type": "pago_exitoso",
    "payload": {
        "transaction_token": "880e8400-e29b-41d4-a716-446655440003",
        "subscription_id": "SUB-2026-00456",
        "amount": 9990.00,
        "currency": "CLP",
        "payment_method": "transferencia",
        "timestamp": "2026-06-17T11:00:00Z",
    },
}


# =============================================================================
# Helper
# =============================================================================

def _saved(mock_db: MagicMock) -> RawEvent:
    assert mock_db.add.call_count >= 1, "db.add() nunca fue llamado"
    return mock_db.add.call_args[0][0]


# =============================================================================
# 1. intento_pago — inicio de transacción
# =============================================================================

class TestIntentoPago:

    def test_returns_202(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=INTENTO_PAGO).status_code == 202

    def test_status_acknowledged(self, client: TestClient, mock_db: MagicMock):
        body = client.post("/v1/events", json=INTENTO_PAGO).json()
        assert body["status"] == "acknowledged"
        assert "event_id" in body

    def test_source_y_event_type_guardados(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INTENTO_PAGO)
        saved = _saved(mock_db)
        assert saved.source == "payments"
        assert saved.event_type == "intento_pago"

    def test_transaction_token_es_uuid(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INTENTO_PAGO)
        _uuid.UUID(_saved(mock_db).payload["transaction_token"])

    def test_amount_guardado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INTENTO_PAGO)
        assert _saved(mock_db).payload["amount"] == 149990.00

    def test_payment_method_guardado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INTENTO_PAGO)
        assert _saved(mock_db).payload["payment_method"] == "tarjeta_credito"

    def test_order_id_guardado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INTENTO_PAGO)
        assert _saved(mock_db).payload["order_id"] == "ORD-2026-78901"

    def test_processed_defaults_false(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=INTENTO_PAGO)
        assert _saved(mock_db).processed is False


# =============================================================================
# 2. pago_exitoso — transacción aprobada
# =============================================================================

class TestPagoExitoso:

    def test_returns_202(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=PAGO_EXITOSO).status_code == 202

    def test_source_payments(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_EXITOSO)
        assert _saved(mock_db).source == "payments"
        assert _saved(mock_db).event_type == "pago_exitoso"

    def test_token_consistente_con_intento(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_EXITOSO)
        assert (
            _saved(mock_db).payload["transaction_token"]
            == INTENTO_PAGO["payload"]["transaction_token"]
        )

    def test_authorization_code_presente(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_EXITOSO)
        assert "authorization_code" in _saved(mock_db).payload

    def test_amount_preservado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_EXITOSO)
        assert _saved(mock_db).payload["amount"] == 149990.00

    def test_payment_method_preservado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_EXITOSO)
        assert _saved(mock_db).payload["payment_method"] == "tarjeta_credito"

    def test_pago_subscription_sin_order_id(self, client: TestClient, mock_db: MagicMock):
        """Un pago puede referenciar una suscripción en vez de una orden."""
        assert client.post("/v1/events", json=PAGO_SUBSCRIPTION).status_code == 202
        p = _saved(mock_db).payload
        assert "subscription_id" in p
        assert p["subscription_id"] == "SUB-2026-00456"


# =============================================================================
# 3. pago_rechazado — distintas causas de fallo
# =============================================================================

class TestPagoRechazado:

    def test_returns_202_rechazo_monto(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=PAGO_RECHAZADO_MONTO).status_code == 202

    def test_returns_202_rechazo_transaccion(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=PAGO_RECHAZADO_TRANSACCION).status_code == 202

    def test_error_code_monto_guardado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_RECHAZADO_MONTO)
        assert _saved(mock_db).payload["error_code"] == "ERR_MONTO_INSUFICIENTE"

    def test_error_code_transaccion_guardado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_RECHAZADO_TRANSACCION)
        assert _saved(mock_db).payload["error_code"] == "ERR_TRANSACCION_DUPLICADA"

    def test_payment_method_en_rechazo(self, client: TestClient, mock_db: MagicMock):
        """El método de pago se guarda incluso en rechazos para analítica."""
        client.post("/v1/events", json=PAGO_RECHAZADO_MONTO)
        assert _saved(mock_db).payload["payment_method"] == "tarjeta_debito"

    def test_rechazo_subscription_sin_order_id(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_RECHAZADO_TRANSACCION)
        p = _saved(mock_db).payload
        assert "subscription_id" in p
        assert "order_id" not in p

    def test_tokens_distintos_por_transaccion(self, client: TestClient, mock_db: MagicMock):
        """Cada transacción rechazada debe tener su propio token único."""
        assert (
            PAGO_RECHAZADO_MONTO["payload"]["transaction_token"]
            != PAGO_RECHAZADO_TRANSACCION["payload"]["transaction_token"]
        )


# =============================================================================
# 4. pago_reembolsado — reversión de un pago exitoso
# =============================================================================

class TestPagoReembolsado:

    def test_returns_202(self, client: TestClient, mock_db: MagicMock):
        assert client.post("/v1/events", json=PAGO_REEMBOLSADO).status_code == 202

    def test_event_type_correcto(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_REEMBOLSADO)
        assert _saved(mock_db).event_type == "pago_reembolsado"

    def test_token_referencia_al_pago_original(self, client: TestClient, mock_db: MagicMock):
        """El reembolso debe referenciar el mismo token que el pago_exitoso."""
        client.post("/v1/events", json=PAGO_REEMBOLSADO)
        assert (
            _saved(mock_db).payload["transaction_token"]
            == PAGO_EXITOSO["payload"]["transaction_token"]
        )

    def test_amount_del_reembolso_guardado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_REEMBOLSADO)
        assert _saved(mock_db).payload["amount"] == 149990.00

    def test_refund_reason_guardado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_REEMBOLSADO)
        assert "refund_reason" in _saved(mock_db).payload

    def test_refunded_at_timestamp_guardado(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_REEMBOLSADO)
        assert "refunded_at" in _saved(mock_db).payload


# =============================================================================
# 5. Audit metadata
# =============================================================================

class TestPagoAuditMetadata:

    def test_event_id_es_uuid_v4(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=PAGO_EXITOSO)
        event_id = _uuid.UUID(response.json()["event_id"])
        assert event_id.version == 4

    def test_event_id_coincide_entre_respuesta_y_db(self, client: TestClient, mock_db: MagicMock):
        response = client.post("/v1/events", json=PAGO_EXITOSO)
        assert str(_saved(mock_db).event_id) == response.json()["event_id"]

    def test_ingested_at_timezone_aware(self, client: TestClient, mock_db: MagicMock):
        client.post("/v1/events", json=PAGO_EXITOSO)
        assert _saved(mock_db).ingested_at.tzinfo is not None

    def test_dos_pagos_distintos_event_ids_distintos(self, client: TestClient, mock_db: MagicMock):
        id1 = client.post("/v1/events", json=INTENTO_PAGO).json()["event_id"]
        id2 = client.post("/v1/events", json=PAGO_EXITOSO).json()["event_id"]
        assert id1 != id2


# =============================================================================
# 6. Validaciones — rechaza payloads inválidos
# =============================================================================

class TestPagoValidaciones:

    def test_missing_source_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {k: v for k, v in PAGO_EXITOSO.items() if k != "source"}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()

    def test_missing_event_type_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {k: v for k, v in PAGO_EXITOSO.items() if k != "event_type"}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()

    def test_payload_lista_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {**PAGO_EXITOSO, "payload": ["no", "es", "objeto"]}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()

    def test_payload_nulo_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {**PAGO_EXITOSO, "payload": None}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()

    def test_source_vacio_devuelve_422(self, client: TestClient, mock_db: MagicMock):
        bad = {**PAGO_EXITOSO, "source": ""}
        assert client.post("/v1/events", json=bad).status_code == 422
        mock_db.add.assert_not_called()
