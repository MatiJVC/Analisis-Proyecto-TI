"""
Tests unitarios de confirm_payment en payment_service.

Verifica que approved:false se mapea correctamente según la causa:
  - approved:true                          → Aprobado
  - approved:false + código de monto       → discrepancia_de_monto
  - approved:false + rechazo banco/saldo   → Rechazado
  - transaction_id no coincide             → discrepancia_de_transacciones (previo al approved)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion
from app.pagos.models.fact_pagos import FactPagos
from app.pagos.services.payment_service import confirm_payment


TOKEN = "tok_live_abc123xyz"
TX_ID = uuid.uuid4()
TIMESTAMP = datetime(2026, 6, 29, 14, 5, 2, tzinfo=timezone.utc)


def _mock_estado(nombre: str, id_: int) -> DimEstadosConciliacion:
    estado = MagicMock(spec=DimEstadosConciliacion)
    estado.id = id_
    estado.nombre = nombre
    return estado


def _mock_fact(transaction_id=None) -> FactPagos:
    fact = MagicMock(spec=FactPagos)
    fact.transaction_id = transaction_id or TX_ID
    fact.estado_conciliacion_id = 1
    fact.error_code_id = None
    fact.timestamp_evento = TIMESTAMP
    return fact


@pytest.fixture
def db_with_fact():
    """DB mock que devuelve un FactPagos al hacer query por token."""
    db = MagicMock()
    fact = _mock_fact()
    chain = db.query.return_value.filter.return_value.order_by.return_value.with_for_update.return_value
    chain.first.return_value = fact
    chain.one_or_none.return_value = fact
    return db, fact


class TestConfirmPaymentAprobado:

    @patch("app.pagos.services.payment_service.get_error_code_id", return_value=None)
    @patch("app.pagos.services.payment_service.get_or_create_estado")
    def test_approved_true_estado_aprobado(self, mock_estado_fn, mock_error_fn, db_with_fact):
        db, fact = db_with_fact
        mock_estado_fn.return_value = _mock_estado("Aprobado", id_=2)

        confirm_payment(db, TOKEN, {"approved": True, "timestamp_evento": TIMESTAMP})

        mock_estado_fn.assert_called_once_with(db, "Aprobado")

    @patch("app.pagos.services.payment_service.get_error_code_id", return_value=None)
    @patch("app.pagos.services.payment_service.get_or_create_estado")
    def test_approved_true_limpia_error_code(self, mock_estado_fn, mock_error_fn, db_with_fact):
        db, fact = db_with_fact
        mock_estado_fn.return_value = _mock_estado("Aprobado", id_=2)

        confirm_payment(db, TOKEN, {"approved": True, "timestamp_evento": TIMESTAMP})

        assert fact.error_code_id is None


class TestConfirmPaymentRechazado:

    @patch("app.pagos.services.payment_service.get_error_code_id", return_value=7)
    @patch("app.pagos.services.payment_service.get_or_create_estado")
    def test_approved_false_sin_keyword_monto_es_rechazado(self, mock_estado_fn, mock_error_fn, db_with_fact):
        """Rechazo por banco o saldo insuficiente → Rechazado, no discrepancia_de_monto."""
        db, fact = db_with_fact
        mock_estado_fn.return_value = _mock_estado("Rechazado", id_=5)

        confirm_payment(db, TOKEN, {
            "approved": False,
            "codigo_error": "ERR_BANCO_RECHAZA",
            "timestamp_evento": TIMESTAMP,
        })

        mock_estado_fn.assert_called_once_with(db, "Rechazado")

    @patch("app.pagos.services.payment_service.get_error_code_id", return_value=None)
    @patch("app.pagos.services.payment_service.get_or_create_estado")
    def test_approved_false_sin_codigo_error_es_rechazado(self, mock_estado_fn, mock_error_fn, db_with_fact):
        """approved:false sin código → Rechazado."""
        db, fact = db_with_fact
        mock_estado_fn.return_value = _mock_estado("Rechazado", id_=5)

        confirm_payment(db, TOKEN, {
            "approved": False,
            "codigo_error": None,
            "timestamp_evento": TIMESTAMP,
        })

        mock_estado_fn.assert_called_once_with(db, "Rechazado")

    @patch("app.pagos.services.payment_service.get_error_code_id", return_value=3)
    @patch("app.pagos.services.payment_service.get_or_create_estado")
    def test_approved_false_con_keyword_monto_es_discrepancia_monto(self, mock_estado_fn, mock_error_fn, db_with_fact):
        """approved:false con error_code que contiene 'monto' → discrepancia_de_monto."""
        db, fact = db_with_fact
        mock_estado_fn.return_value = _mock_estado("discrepancia_de_monto", id_=3)

        confirm_payment(db, TOKEN, {
            "approved": False,
            "codigo_error": "ERR_MONTO_DIFERENTE",
            "timestamp_evento": TIMESTAMP,
        })

        mock_estado_fn.assert_called_once_with(db, "discrepancia_de_monto")

    @patch("app.pagos.services.payment_service.get_error_code_id", return_value=3)
    @patch("app.pagos.services.payment_service.get_or_create_estado")
    def test_approved_false_con_keyword_amount_es_discrepancia_monto(self, mock_estado_fn, mock_error_fn, db_with_fact):
        """Soporta 'amount' en inglés como keyword de discrepancia."""
        db, fact = db_with_fact
        mock_estado_fn.return_value = _mock_estado("discrepancia_de_monto", id_=3)

        confirm_payment(db, TOKEN, {
            "approved": False,
            "codigo_error": "AMOUNT_MISMATCH",
            "timestamp_evento": TIMESTAMP,
        })

        mock_estado_fn.assert_called_once_with(db, "discrepancia_de_monto")


class TestConfirmPaymentTransactionMismatch:

    @patch("app.pagos.services.payment_service.get_error_code_id", return_value=4)
    @patch("app.pagos.services.payment_service.get_or_create_estado")
    def test_transaction_id_diferente_es_discrepancia_transacciones(self, mock_estado_fn, mock_error_fn, db_with_fact):
        """Si transaction_id no coincide, el estado es discrepancia_de_transacciones antes de revisar approved."""
        db, fact = db_with_fact
        mock_estado_fn.return_value = _mock_estado("discrepancia_de_transacciones", id_=4)
        otro_tx = uuid.uuid4()

        confirm_payment(db, TOKEN, {
            "approved": True,
            "transaction_id": otro_tx,
            "timestamp_evento": TIMESTAMP,
        })

        mock_estado_fn.assert_called_once_with(db, "discrepancia_de_transacciones")

    @patch("app.pagos.services.payment_service.get_error_code_id", return_value=None)
    @patch("app.pagos.services.payment_service.get_or_create_estado")
    def test_token_no_encontrado_lanza_valueerror(self, mock_estado_fn, mock_error_fn):
        db = MagicMock()
        chain = db.query.return_value.filter.return_value.order_by.return_value.with_for_update.return_value
        chain.first.return_value = None
        chain.one_or_none.return_value = None

        with pytest.raises(ValueError, match="No payment found"):
            confirm_payment(db, "token_inexistente", {"approved": True, "timestamp_evento": TIMESTAMP})
