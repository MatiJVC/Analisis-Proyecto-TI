"""
Tests para el processor IoT.

Cubre la normalización de anomalías cuando llega telemetría válida.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock


def _make_raw(event_type: str, payload: dict):
    raw = MagicMock()
    raw.event_type = event_type
    raw.payload = payload
    raw.ingested_at = datetime(2026, 7, 3, 2, 40, 0, tzinfo=timezone.utc)
    raw.event_id = 1
    return raw


def _make_db(existing=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing
    return db


class TestIoTTelemetryRecovery:
    def test_telemetry_received_clears_previous_anomaly_when_battery_is_ok(self):
        from app.etl.processors.iot_processor import process_iot_event

        existing = MagicMock()
        existing.sensor_id = "OXI-001"
        existing.asset_id = "PATIENT-001"
        existing.sensor_type = "pulse_oximeter"
        existing.has_anomaly = True
        existing.low_battery_alert = True
        existing.is_online = False

        db = _make_db(existing=existing)
        raw = _make_raw("telemetry_received", {
            "sensor_id": "OXI-001",
            "asset_id": "PATIENT-001",
            "sensor_type": "pulse_oximeter",
            "battery": 85,
            "signal_strength": -45,
            "connection_status": "connected",
            "temperature": 37.1,
        })

        process_iot_event(db, raw)

        assert existing.has_anomaly is False
        assert existing.low_battery_alert is False
        assert existing.is_online is True
        assert db.flush.called

    def test_telemetry_received_keeps_anomaly_when_battery_is_still_low(self):
        from app.etl.processors.iot_processor import process_iot_event

        existing = MagicMock()
        existing.sensor_id = "BP-001"
        existing.asset_id = "PATIENT-001"
        existing.sensor_type = "sphygmomanometer"
        existing.has_anomaly = True
        existing.low_battery_alert = True
        existing.is_online = False

        db = _make_db(existing=existing)
        raw = _make_raw("telemetry_received", {
            "sensor_id": "BP-001",
            "asset_id": "PATIENT-001",
            "sensor_type": "sphygmomanometer",
            "battery": 5,
            "signal_strength": -80,
            "connection_status": "connected",
        })

        process_iot_event(db, raw)

        assert existing.has_anomaly is True
        assert existing.low_battery_alert is True
        assert existing.is_online is True