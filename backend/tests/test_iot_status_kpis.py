"""
Tests para el cálculo de estado y tipos de sensores IoT.

Verifica que el backend trabaje sobre el último estado por sensor,
con paginación y filtro activo/inactivo.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock


def _make_db(rows):
    query = MagicMock()
    query.order_by.return_value = query
    query.all.return_value = rows

    db = MagicMock()
    db.query.return_value = query
    return db


class TestIoTStatusPagination:
    def test_paginates_latest_rows_and_filters_active_sensors(self):
        from app.analytics.iot_kpis import get_sensors_status

        rows = [
            ("A-001", "ASSET-1", "thermometer", True, 80.0, datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 1, tzinfo=timezone.utc), 2),
            ("A-001", "ASSET-1", "thermometer", False, 80.0, datetime(2026, 7, 3, 9, 0, tzinfo=timezone.utc), None, True, True, datetime(2026, 7, 3, 9, 1, tzinfo=timezone.utc), 1),
            ("B-001", "ASSET-2", "pulse_oximeter", False, 40.0, datetime(2026, 7, 3, 10, 5, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 6, tzinfo=timezone.utc), 4),
            ("C-001", "ASSET-3", "glucometer", True, 90.0, datetime(2026, 7, 3, 10, 7, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 8, tzinfo=timezone.utc), 6),
        ]
        db = _make_db(rows)

        result = get_sensors_status(db, limit=2, offset=1, status="all")

        assert result["total_sensors"] == 3
        assert result["online_count"] == 2
        assert result["offline_count"] == 1
        assert [sensor["sensor_id"] for sensor in result["sensors"]] == ["B-001", "C-001"]

    def test_filters_active_sensor_list(self):
        from app.analytics.iot_kpis import get_sensors_status

        rows = [
            ("A-001", "ASSET-1", "thermometer", True, 80.0, datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 1, tzinfo=timezone.utc), 2),
            ("B-001", "ASSET-2", "pulse_oximeter", False, 40.0, datetime(2026, 7, 3, 10, 5, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 6, tzinfo=timezone.utc), 4),
        ]
        db = _make_db(rows)

        result = get_sensors_status(db, limit=10, offset=0, status="active")

        assert result["total_sensors"] == 1
        assert result["online_count"] == 1
        assert result["offline_count"] == 0
        assert len(result["sensors"]) == 1
        assert result["sensors"][0]["sensor_id"] == "A-001"

    def test_search_filters_across_sensor_fields_before_pagination(self):
        from app.analytics.iot_kpis import get_sensors_status

        rows = [
            ("A-001", "MEDKIT-001", "thermometer", True, 80.0, datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 1, tzinfo=timezone.utc), 2),
            ("B-001", "PATIENT-001", "pulse_oximeter", False, 40.0, datetime(2026, 7, 3, 10, 5, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 6, tzinfo=timezone.utc), 4),
            ("C-001", "PATIENT-002", "glucometer", True, 90.0, datetime(2026, 7, 3, 10, 7, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 8, tzinfo=timezone.utc), 6),
        ]
        db = _make_db(rows)

        result = get_sensors_status(db, limit=10, offset=0, status="all", search="patient-001")

        assert result["total_sensors"] == 1
        assert len(result["sensors"]) == 1
        assert result["sensors"][0]["sensor_id"] == "B-001"


class TestIoTByTypeAggregation:
    def test_groups_by_latest_sensor_state(self):
        from app.analytics.iot_kpis import get_sensors_by_type

        rows = [
            ("A-001", "ASSET-1", "thermometer", True, 80.0, datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 1, tzinfo=timezone.utc), 2),
            ("B-001", "ASSET-2", "pulse_oximeter", False, 40.0, datetime(2026, 7, 3, 10, 5, tzinfo=timezone.utc), None, True, True, datetime(2026, 7, 3, 10, 6, tzinfo=timezone.utc), 4),
            ("C-001", "ASSET-3", "thermometer", True, 90.0, datetime(2026, 7, 3, 10, 7, tzinfo=timezone.utc), None, False, False, datetime(2026, 7, 3, 10, 8, tzinfo=timezone.utc), 6),
        ]
        db = _make_db(rows)

        result = get_sensors_by_type(db)
        metrics = {item["sensor_type"]: item for item in result}

        assert metrics["thermometer"]["count"] == 2
        assert metrics["thermometer"]["online_count"] == 2
        assert metrics["thermometer"]["offline_count"] == 0
        assert metrics["thermometer"]["anomaly_count"] == 0
        assert metrics["pulse_oximeter"]["count"] == 1
        assert metrics["pulse_oximeter"]["offline_count"] == 1