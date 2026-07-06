"""
Tests para Notification ETL processor.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.etl.processors.notification_proccessor import (
    process_notification_event,
    NotificationPayloadValidationError
)
from app.models import FactNotifications


def _make_raw(event_type: str, payload: dict):
    raw = MagicMock()
    raw.event_type = event_type
    raw.payload = payload
    return raw


def _make_db(existing=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing
    return db


class TestNotificationETL:
    def test_notificacion_enviada_creates_new(self):
        db = _make_db(None)
        raw = _make_raw(
            "notificacion_enviada",
            {
                "id_notificacion": "ntf_123",
                "canal_usado": "sms",
                "intentos": 1,
                "destinatario_telefono": "+56912345678"
            }
        )
        fact = process_notification_event(db, raw)
        assert fact is not None
        assert fact.id_notificacion == "ntf_123"
        assert fact.canal_original == "sms"
        assert fact.canal_usado == "sms"
        assert fact.estado == "enviado"
        assert fact.destinatario_telefono == "+56912345678"
        db.add.assert_called()

    def test_notificacion_fallida_creates_new_if_missing(self):
        db = _make_db(None)
        raw = _make_raw(
            "notificacion_fallida",
            {
                "id_notificacion": "ntf_456",
                "canal_usado": "email",
                "intentos": 2
            }
        )
        fact = process_notification_event(db, raw)
        assert fact is not None
        assert fact.id_notificacion == "ntf_456"
        assert fact.canal_original == "email"
        assert fact.canal_usado == "email"
        assert fact.estado == "fallido"
        assert fact.intentos == 2
        db.add.assert_called()

    def test_notificacion_entregada_creates_new_if_missing(self):
        db = _make_db(None)
        raw = _make_raw(
            "notificacion_entregada",
            {
                "id_notificacion": "ntf_789",
                "canal_usado": "push"
            }
        )
        fact = process_notification_event(db, raw)
        assert fact is not None
        assert fact.id_notificacion == "ntf_789"
        assert fact.estado == "entregado"
        assert fact.canal_usado == "push"
        db.add.assert_called()

    def test_fallback_activado_creates_new_if_missing(self):
        db = _make_db(None)
        raw = _make_raw(
            "fallback_activado",
            {
                "id_notificacion": "ntf_abc",
                "canal_fallback": "email",
                "canal_original": "sms"
            }
        )
        fact = process_notification_event(db, raw)
        assert fact is not None
        assert fact.id_notificacion == "ntf_abc"
        assert fact.canal_original == "sms"
        assert fact.canal_usado == "email"
        assert fact.fallback_activado is True
        # Original intentos is 1 (default during creation), incremented by 1 in fallback
        assert fact.intentos == 2
        db.add.assert_called()

    def test_missing_id_notificacion_raises_validation_error(self):
        db = _make_db(None)
        raw = _make_raw(
            "notificacion_enviada",
            {
                "canal_usado": "sms"
            }
        )
        with pytest.raises(NotificationPayloadValidationError):
            process_notification_event(db, raw)
