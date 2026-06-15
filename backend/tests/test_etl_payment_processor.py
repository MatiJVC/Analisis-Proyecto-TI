"""
Tests para el payment ETL processor (process_payment_event).

Cubre:
  - Routing correcto por event_type a cada sub-processor
  - ValueError para event_type desconocido
  - Validación de payload (campos requeridos, monto negativo) vía Pydantic real
  - db.add + db.flush llamados por _process_intento_pago y _process_cierre_diario
  - Hashing SHA-256 del token: register_payment_attempt NO almacena el token en claro

Los tests de routing/flush parchean las funciones de servicio para evitar
dependencia de DB real. Los tests de validación de payload NO parchean el
schema — se usa la validación Pydantic real para que un cambio de modelo
rompa el test en lugar de pasar inadvertido.
"""
import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.etl.processors.payment_processor import process_payment_event


NOW = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

INTENTO_PAYLOAD = {
    "transaction_id": str(uuid.uuid4()),
    "order_id": "ORD-001",
    "subscription_id": None,
    "monto": "9990.00",
    "token_transaccion": "tok_test_secret",
    "timestamp_evento": NOW.isoformat(),
}

CONFIRMAR_PAYLOAD = {
    "token_transaccion": "tok_test_secret",
    "transaction_id": None,
    "approved": True,
    "codigo_error": None,
    "timestamp_evento": NOW.isoformat(),
}

CIERRE_PAYLOAD = {
    "fecha": "2026-06-15",
    "reported_total": "1000000.00",
    "reported_count": 42,
    "reference_id": "REF-2026-001",
    "timestamp_event": NOW.isoformat(),
}


def _raw(event_type: str, payload: dict):
    raw = MagicMock()
    raw.event_type = event_type
    raw.payload = payload
    return raw


# ─── Routing ──────────────────────────────────────────────────────────────────

class TestRouting:
    def test_unknown_event_type_raises_value_error(self):
        with pytest.raises(ValueError, match="desconocido"):
            process_payment_event(MagicMock(), _raw("tipo_inventado", {}))

    def test_intento_pago_calls_register_payment_attempt(self):
        db = MagicMock()
        fake_fact = MagicMock()
        with (
            patch("app.pagos.services.payment_service.register_payment_attempt", return_value=fake_fact) as mock_reg,
            patch("app.pagos.models.fact_payments_events.FactPaymentsEvent"),
        ):
            process_payment_event(db, _raw("intento_pago", INTENTO_PAYLOAD))
        mock_reg.assert_called_once()

    def test_confirmar_pago_calls_confirm_payment(self):
        db = MagicMock()
        fake_fact = MagicMock()
        with (
            patch("app.pagos.services.payment_service.confirm_payment", return_value=fake_fact) as mock_confirm,
            patch("app.pagos.models.fact_payments_events.FactPaymentsEvent"),
        ):
            db.get.return_value = None
            process_payment_event(db, _raw("confirmar_pago", CONFIRMAR_PAYLOAD))
        mock_confirm.assert_called_once()

    def test_cierre_diario_calls_process_cierre_diario(self):
        db = MagicMock()
        with patch("app.pagos.services.closure_service.process_cierre_diario") as mock_cierre:
            mock_cierre.return_value = MagicMock(id=1, estado_id=2)
            process_payment_event(db, _raw("cierre_diario_completado", CIERRE_PAYLOAD))
        mock_cierre.assert_called_once()


# ─── intento_pago — db writes ─────────────────────────────────────────────────

class TestIntentoPayoDBWrites:
    def test_db_add_called_once(self):
        db = MagicMock()
        fake_fact = MagicMock()
        with (
            patch("app.pagos.services.payment_service.register_payment_attempt", return_value=fake_fact),
            patch("app.pagos.models.fact_payments_events.FactPaymentsEvent"),
        ):
            process_payment_event(db, _raw("intento_pago", INTENTO_PAYLOAD))
        db.add.assert_called_once()

    def test_db_flush_called_once(self):
        db = MagicMock()
        fake_fact = MagicMock()
        with (
            patch("app.pagos.services.payment_service.register_payment_attempt", return_value=fake_fact),
            patch("app.pagos.models.fact_payments_events.FactPaymentsEvent"),
        ):
            process_payment_event(db, _raw("intento_pago", INTENTO_PAYLOAD))
        db.flush.assert_called_once()


# ─── cierre_diario — db writes ────────────────────────────────────────────────

class TestCierreDiarioDBWrites:
    def test_db_flush_called_once(self):
        db = MagicMock()
        with patch("app.pagos.services.closure_service.process_cierre_diario") as mock_cierre:
            mock_cierre.return_value = MagicMock(id=1, estado_id=2)
            process_payment_event(db, _raw("cierre_diario_completado", CIERRE_PAYLOAD))
        db.flush.assert_called_once()


# ─── Validación de payload (Pydantic real, sin mocks de schema) ───────────────

class TestIntentoPayloadValidation:
    def test_missing_token_raises(self):
        payload = {k: v for k, v in INTENTO_PAYLOAD.items() if k != "token_transaccion"}
        with pytest.raises(Exception):
            process_payment_event(MagicMock(), _raw("intento_pago", payload))

    def test_missing_monto_raises(self):
        payload = {k: v for k, v in INTENTO_PAYLOAD.items() if k != "monto"}
        with pytest.raises(Exception):
            process_payment_event(MagicMock(), _raw("intento_pago", payload))

    def test_missing_transaction_id_raises(self):
        payload = {k: v for k, v in INTENTO_PAYLOAD.items() if k != "transaction_id"}
        with pytest.raises(Exception):
            process_payment_event(MagicMock(), _raw("intento_pago", payload))

    def test_negative_monto_raises(self):
        payload = {**INTENTO_PAYLOAD, "monto": "-1.00"}
        with pytest.raises(Exception):
            process_payment_event(MagicMock(), _raw("intento_pago", payload))


class TestConfirmarPayloadValidation:
    def test_missing_token_raises(self):
        payload = {k: v for k, v in CONFIRMAR_PAYLOAD.items() if k != "token_transaccion"}
        with pytest.raises(Exception):
            process_payment_event(MagicMock(), _raw("confirmar_pago", payload))

    def test_missing_approved_raises(self):
        payload = {k: v for k, v in CONFIRMAR_PAYLOAD.items() if k != "approved"}
        with pytest.raises(Exception):
            process_payment_event(MagicMock(), _raw("confirmar_pago", payload))


class TestCierrePayloadValidation:
    def test_missing_fecha_raises(self):
        payload = {k: v for k, v in CIERRE_PAYLOAD.items() if k != "fecha"}
        with pytest.raises(Exception):
            process_payment_event(MagicMock(), _raw("cierre_diario_completado", payload))

    def test_missing_reported_total_raises(self):
        payload = {k: v for k, v in CIERRE_PAYLOAD.items() if k != "reported_total"}
        with pytest.raises(Exception):
            process_payment_event(MagicMock(), _raw("cierre_diario_completado", payload))

    def test_missing_reported_count_raises(self):
        payload = {k: v for k, v in CIERRE_PAYLOAD.items() if k != "reported_count"}
        with pytest.raises(Exception):
            process_payment_event(MagicMock(), _raw("cierre_diario_completado", payload))


# ─── Token hashing (payment_service) ──────────────────────────────────────────

class TestTokenHashing:
    """
    register_payment_attempt debe almacenar SHA-256(token), nunca el valor en claro.
    Esto protege los tokens de pago en caso de una brecha de BD.
    """

    def test_hash_function_is_sha256(self):
        from app.pagos.services.payment_service import _hash_token
        token = "tok_test_secret"
        assert _hash_token(token) == hashlib.sha256(token.encode()).hexdigest()

    def test_hash_output_is_64_hex_chars(self):
        from app.pagos.services.payment_service import _hash_token
        result = _hash_token("any_token")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_tokens_produce_different_hashes(self):
        from app.pagos.services.payment_service import _hash_token
        assert _hash_token("token_a") != _hash_token("token_b")

    def test_register_attempt_stores_hashed_token_not_plaintext(self):
        """FactPagos.token_transaccion must be the SHA-256 digest, not the raw token."""
        from app.pagos.services.payment_service import register_payment_attempt, _hash_token

        db = MagicMock()
        # get_or_create_estado finds the existing estado via one_or_none()
        mock_estado = MagicMock(id=1)
        db.query.return_value.filter.return_value.one_or_none.return_value = mock_estado

        added = []
        db.add.side_effect = lambda obj: added.append(obj)

        payload = {
            "transaction_id": uuid.uuid4(),
            "order_id": None,
            "subscription_id": None,
            "monto": Decimal("5000.00"),
            "token_transaccion": "raw_secret_token",
            "timestamp_evento": NOW,
        }
        register_payment_attempt(db, payload)

        # Only one db.add() call — for FactPagos (estado was found, not inserted)
        assert len(added) == 1
        stored_token = added[0].token_transaccion
        assert stored_token == _hash_token("raw_secret_token"), (
            "token_transaccion must be stored as a SHA-256 digest"
        )
        assert stored_token != "raw_secret_token", (
            "raw token must never be persisted to the database"
        )
