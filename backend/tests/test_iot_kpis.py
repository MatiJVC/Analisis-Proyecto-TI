"""
Tests para los KPIs de IoT.

Verifica que la tasa de validez y anomalías se calculan sobre el último
estado conocido de cada sensor.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock


def _make_db(rows):
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = rows

    db = MagicMock()
    db.query.return_value = query
    return db


class TestIoTValidityRate:
    def test_uses_latest_row_per_sensor(self):
        from app.analytics.iot_kpis import get_data_validity_rate, get_anomalies_detected

        rows = [
            ("BP-001", "PATIENT-001", "sphygmomanometer", True, 93.0, datetime(2026, 7, 3, 2, 34, 0, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 2, 34, 10, tzinfo=timezone.utc), 3),
            ("BP-001", "PATIENT-001", "sphygmomanometer", False, 93.0, datetime(2026, 7, 3, 2, 10, 0, tzinfo=timezone.utc), None, True, True, datetime(2026, 7, 3, 2, 10, 10, tzinfo=timezone.utc), 2),
            ("GLUCO-001", "PATIENT-001", "glucometer", False, 8.0, datetime(2026, 7, 3, 2, 35, 0, tzinfo=timezone.utc), None, True, True, datetime(2026, 7, 3, 2, 35, 10, tzinfo=timezone.utc), 5),
            ("GLUCO-001", "PATIENT-001", "glucometer", True, 8.0, datetime(2026, 7, 3, 1, 55, 0, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 1, 55, 10, tzinfo=timezone.utc), 4),
            ("OXI-001", "PATIENT-001", "pulse_oximeter", True, 77.0, datetime(2026, 7, 3, 2, 36, 0, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 2, 36, 10, tzinfo=timezone.utc), 8),
            ("OXI-001", "PATIENT-001", "pulse_oximeter", False, 77.0, datetime(2026, 7, 3, 2, 5, 0, tzinfo=timezone.utc), None, True, True, datetime(2026, 7, 3, 2, 5, 10, tzinfo=timezone.utc), 1),
        ]
        db = _make_db(rows)

        assert get_data_validity_rate(db) == 0.67
        assert get_anomalies_detected(db) == 1