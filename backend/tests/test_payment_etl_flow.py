"""
Prueba de flujo ETL — eventos de pagos (source=payments)

Verifica que process_payment_event transforma el payload crudo (Bronze)
en un registro FactPagos (Gold) con los valores correctos.

Los tests usan un mock de Session + stubs de los servicios de dimensiones
para que no se necesite una BD real. Se enfoca en la lógica de transformación:
  - transaction_token  → token_transaccion en FactPagos
  - amount             → monto
  - payment_method     → payment_method
  - event_type         → estado_conciliacion_id correcto
  - pago_reembolsado   → no escribe en warehouse (retorno silencioso)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.etl.processors.payment_processor import process_payment_event
from app.pagos.services.payment_service import _hash_token
from app.models.raw.raw_events import RawEvent
from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion
from app.pagos.models.fact_pagos import FactPagos


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_raw_event(event_type: str, payload: dict) -> RawEvent:
    """Crea un RawEvent en-memoria sin necesitar BD."""
    return RawEvent(
        event_id=uuid.uuid4(),
        source="payments",
        event_type=event_type,
        payload=payload,
        processed=False,
        ingested_at=datetime.now(tz=timezone.utc),
    )


def _mock_estado(nombre: str, id_: int = 1) -> DimEstadosConciliacion:
    estado = MagicMock(spec=DimEstadosConciliacion)
    estado.id = id_
    estado.nombre = nombre
    return estado


def _fact_from_db_add(mock_db: MagicMock) -> FactPagos:
    """Extrae el FactPagos que el procesador pasó a db.add()."""
    calls = [
        call[0][0]
        for call in mock_db.add.call_args_list
        if isinstance(call[0][0], FactPagos)
    ]
    assert calls, "El procesador nunca llamó db.add(FactPagos(...))"
    return calls[0]


# ─── Payloads de prueba ───────────────────────────────────────────────────────

INTENTO_PAGO_PAYLOAD = {
    "transaction_token": "550e8400-e29b-41d4-a716-446655440000",
    "order_id": "ORD-2026-78901",
    "amount": 149990.00,
    "currency": "CLP",
    "payment_method": "tarjeta_credito",
    "timestamp": "2026-06-17T10:00:00Z",
}

PAGO_EXITOSO_PAYLOAD = {
    "transaction_token": "550e8400-e29b-41d4-a716-446655440000",
    "order_id": "ORD-2026-78901",
    "amount": 149990.00,
    "currency": "CLP",
    "payment_method": "tarjeta_credito",
    "authorization_code": "AUTH-20260617-001",
    "timestamp": "2026-06-17T10:00:45Z",
}

PAGO_RECHAZADO_MONTO_PAYLOAD = {
    "transaction_token": "660e8400-e29b-41d4-a716-446655440001",
    "order_id": "ORD-2026-78902",
    "amount": 89990.00,
    "currency": "CLP",
    "payment_method": "tarjeta_debito",
    "error_code": "ERR_MONTO_INSUFICIENTE",
    "timestamp": "2026-06-17T10:05:00Z",
}

PAGO_RECHAZADO_TX_PAYLOAD = {
    "transaction_token": "770e8400-e29b-41d4-a716-446655440002",
    "subscription_id": "SUB-2026-00123",
    "amount": 29990.00,
    "currency": "CLP",
    "payment_method": "billetera_digital",
    "error_code": "ERR_TRANSACCION_DUPLICADA",
    "timestamp": "2026-06-17T10:10:00Z",
}

PAGO_REEMBOLSADO_PAYLOAD = {
    "transaction_token": "550e8400-e29b-41d4-a716-446655440000",
    "order_id": "ORD-2026-78901",
    "amount": 149990.00,
    "refund_reason": "Solicitud del cliente",
    "refunded_at": "2026-06-17T14:00:00Z",
}


# ─── Fixture de sesión mock ───────────────────────────────────────────────────

@pytest.fixture
def db() -> MagicMock:
    mock = MagicMock()
    # Simulate no existing FactPagos record (upsert takes the INSERT branch)
    mock.query.return_value.filter.return_value.first.return_value = None
    return mock


# ─── Flujo 1: intento_pago → esperando_revisión ───────────────────────────────

class TestFlujointentoPago:

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_escribe_fact_pagos(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("esperando_revisión", id_=1)
        raw = _make_raw_event("intento_pago", INTENTO_PAGO_PAYLOAD)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert isinstance(fact, FactPagos)

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_estado_esperando_revision(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("esperando_revisión", id_=1)
        raw = _make_raw_event("intento_pago", INTENTO_PAGO_PAYLOAD)

        process_payment_event(db, raw)

        mock_estado_fn.assert_called_once_with(db, "esperando_revisión")

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_monto_y_token_correctos(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("esperando_revisión", id_=1)
        raw = _make_raw_event("intento_pago", INTENTO_PAGO_PAYLOAD)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert float(fact.monto) == 149990.00
        assert fact.token_transaccion == _hash_token("550e8400-e29b-41d4-a716-446655440000")

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_payment_method_y_order_id(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("esperando_revisión", id_=1)
        raw = _make_raw_event("intento_pago", INTENTO_PAGO_PAYLOAD)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert fact.payment_method == "tarjeta_credito"
        assert fact.order_id == "ORD-2026-78901"
        assert fact.subscription_id is None

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_timestamp_parseado(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("esperando_revisión", id_=1)
        raw = _make_raw_event("intento_pago", INTENTO_PAGO_PAYLOAD)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert fact.timestamp_evento is not None
        assert fact.timestamp_evento.tzinfo is not None

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_flush_llamado(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("esperando_revisión", id_=1)
        raw = _make_raw_event("intento_pago", INTENTO_PAGO_PAYLOAD)

        process_payment_event(db, raw)

        db.flush.assert_called()


# ─── Flujo 2: pago_exitoso → Aprobado ────────────────────────────────────────

class TestFlujoPagoExitoso:

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_estado_aprobado(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("Aprobado", id_=2)
        raw = _make_raw_event("pago_exitoso", PAGO_EXITOSO_PAYLOAD)

        process_payment_event(db, raw)

        mock_estado_fn.assert_called_once_with(db, "Aprobado")

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_error_code_id_none(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("Aprobado", id_=2)
        raw = _make_raw_event("pago_exitoso", PAGO_EXITOSO_PAYLOAD)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert fact.error_code_id is None

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_datos_correctos(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("Aprobado", id_=2)
        raw = _make_raw_event("pago_exitoso", PAGO_EXITOSO_PAYLOAD)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert float(fact.monto) == 149990.00
        assert fact.payment_method == "tarjeta_credito"
        assert fact.order_id == "ORD-2026-78901"


# ─── Flujo 3: pago_rechazado por monto → discrepancia_de_monto ───────────────

class TestFlujoPagoRechazadoMonto:

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=5)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_estado_discrepancia_monto(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("discrepancia_de_monto", id_=3)
        raw = _make_raw_event("pago_rechazado", PAGO_RECHAZADO_MONTO_PAYLOAD)

        process_payment_event(db, raw)

        mock_estado_fn.assert_called_once_with(db, "discrepancia_de_monto")

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=5)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_error_code_id_asignado(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("discrepancia_de_monto", id_=3)
        raw = _make_raw_event("pago_rechazado", PAGO_RECHAZADO_MONTO_PAYLOAD)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert fact.error_code_id == 5

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=5)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_datos_correctos(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("discrepancia_de_monto", id_=3)
        raw = _make_raw_event("pago_rechazado", PAGO_RECHAZADO_MONTO_PAYLOAD)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert float(fact.monto) == 89990.00
        assert fact.payment_method == "tarjeta_debito"


# ─── Flujo 4: pago_rechazado por transacción → discrepancia_de_transacciones ──

class TestFlujoPagoRechazadoTransaccion:

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=6)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_estado_discrepancia_transacciones(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("discrepancia_de_transacciones", id_=4)
        raw = _make_raw_event("pago_rechazado", PAGO_RECHAZADO_TX_PAYLOAD)

        process_payment_event(db, raw)

        mock_estado_fn.assert_called_once_with(db, "discrepancia_de_transacciones")

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=6)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_subscription_id_sin_order_id(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("discrepancia_de_transacciones", id_=4)
        raw = _make_raw_event("pago_rechazado", PAGO_RECHAZADO_TX_PAYLOAD)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert fact.subscription_id == "SUB-2026-00123"
        assert fact.order_id is None


# ─── Flujo 4b: pago_rechazado genérico → Rechazado ───────────────────────────

class TestFlujoPagoRechazadoGenerico:

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=7)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_rechazo_banco_sin_keyword_es_rechazado(self, mock_estado_fn, mock_error_fn, db):
        """Rechazo por banco o saldo insuficiente sin keyword de monto/transacción → Rechazado."""
        mock_estado_fn.return_value = _mock_estado("Rechazado", id_=5)
        payload = {**PAGO_RECHAZADO_MONTO_PAYLOAD, "error_code": "ERR_BANCO_RECHAZA"}
        raw = _make_raw_event("pago_rechazado", payload)

        process_payment_event(db, raw)

        mock_estado_fn.assert_called_once_with(db, "Rechazado")

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_rechazo_sin_error_code_es_rechazado(self, mock_estado_fn, mock_error_fn, db):
        """Rechazo sin error_code (banco rechaza sin código) → Rechazado, no esperando_revisión."""
        mock_estado_fn.return_value = _mock_estado("Rechazado", id_=5)
        payload = {k: v for k, v in PAGO_RECHAZADO_MONTO_PAYLOAD.items() if k != "error_code"}
        raw = _make_raw_event("pago_rechazado", payload)

        process_payment_event(db, raw)

        mock_estado_fn.assert_called_once_with(db, "Rechazado")


# ─── Flujo 5: pago_reembolsado → sin escritura warehouse ──────────────────────

class TestFlujoPagoReembolsado:

    def test_no_escribe_en_warehouse(self, db):
        raw = _make_raw_event("pago_reembolsado", PAGO_REEMBOLSADO_PAYLOAD)

        process_payment_event(db, raw)

        fact_calls = [
            call[0][0]
            for call in db.add.call_args_list
            if isinstance(call[0][0], FactPagos)
        ]
        assert not fact_calls, "pago_reembolsado no debe escribir en fact_pagos"

    def test_no_lanza_excepcion(self, db):
        raw = _make_raw_event("pago_reembolsado", PAGO_REEMBOLSADO_PAYLOAD)
        process_payment_event(db, raw)  # no debe fallar


# ─── Flujo 6: validación de campos obligatorios ───────────────────────────────

class TestFlujoValidacion:

    def test_sin_transaction_token_lanza_valueerror(self, db):
        raw = _make_raw_event("intento_pago", {"amount": 100.0})

        with pytest.raises(ValueError, match="transaction_token"):
            process_payment_event(db, raw)

    def test_sin_transaction_token_no_escribe(self, db):
        raw = _make_raw_event("intento_pago", {"amount": 100.0})

        with pytest.raises(ValueError):
            process_payment_event(db, raw)

        db.add.assert_not_called()

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_amount_nulo_usa_cero(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("esperando_revisión", id_=1)
        payload = {**INTENTO_PAGO_PAYLOAD, "amount": None}
        raw = _make_raw_event("intento_pago", payload)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert float(fact.monto) == 0.0

    @patch("app.etl.processors.payment_processor.get_error_code_id", return_value=None)
    @patch("app.etl.processors.payment_processor.get_or_create_estado")
    def test_timestamp_invalido_usa_now(self, mock_estado_fn, mock_error_fn, db):
        mock_estado_fn.return_value = _mock_estado("esperando_revisión", id_=1)
        payload = {**INTENTO_PAGO_PAYLOAD, "timestamp": "no-es-fecha"}
        raw = _make_raw_event("intento_pago", payload)

        process_payment_event(db, raw)

        fact = _fact_from_db_add(db)
        assert fact.timestamp_evento is not None
        assert fact.timestamp_evento.tzinfo is not None
