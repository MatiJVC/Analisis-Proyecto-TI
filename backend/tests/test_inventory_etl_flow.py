"""
Prueba de flujo ETL — eventos de inventario (source=inventory)

Cubre tres niveles del pipeline:
  §1  Schema InventoryEventCreate — validación al llegar al endpoint
  §2  Procesador ETL inventory_processor — Bronze → Warehouse
  §3  Endpoint HTTP POST /v1/events — respuestas 202 / 422

Tipos testeados:
  Movimientos  stock_received, stock_reserved, stock_dispatched,
               stock_adjusted, stock_transfer_initiated
  Alertas      critical_threshold_reached, stock_out_error
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.etl.processors.inventory_processor import (
    InventoryProcessingError,
    process_inventory_event,
)
from app.models.raw.raw_events import RawEvent
from app.models.warehouse.fact_inventory_alerts import FactInventoryAlert
from app.models.warehouse.fact_inventory_movements import FactInventoryMovement
from app.schemas.inventory_event_schema import InventoryEventCreate


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_raw(event_type: str, payload: dict, source: str = "inventory") -> RawEvent:
    return RawEvent(
        event_id=uuid.uuid4(),
        source=source,
        event_type=event_type,
        payload=payload,
        processed=False,
        ingested_at=datetime.now(tz=timezone.utc),
    )


def _added_of(mock_db: MagicMock, cls):
    return [call[0][0] for call in mock_db.add.call_args_list if isinstance(call[0][0], cls)]


def _movement(mock_db: MagicMock) -> FactInventoryMovement:
    rows = _added_of(mock_db, FactInventoryMovement)
    assert rows, "El procesador nunca llamó db.add(FactInventoryMovement(...))"
    return rows[0]


def _alert(mock_db: MagicMock) -> FactInventoryAlert:
    rows = _added_of(mock_db, FactInventoryAlert)
    assert rows, "El procesador nunca llamó db.add(FactInventoryAlert(...))"
    return rows[0]


# ─── Payloads de referencia ───────────────────────────────────────────────────

_NOW   = datetime.now(tz=timezone.utc)
_LATER = _NOW + timedelta(hours=24)

STOCK_RESERVED_PAYLOAD = {
    "reservation_id": "550e8400-e29b-41d4-a716-446655440000",
    "order_id":       "ord-2026-00123",
    "sku_id":         "SKU-PROD-001",
    "location_id":    "a3bb189e-8bf9-3888-9912-ace4e6543002",
    "quantity":       5,
    "created_at":     _NOW.isoformat(),
    "expires_at":     _LATER.isoformat(),
}

STOCK_RECEIVED_PAYLOAD = {
    "sku_id":            "SKU-PROD-001",
    "location_id":       42,
    "quantity_received": 100,
    "received_at":       "2026-06-28T08:30:00Z",
}

STOCK_DISPATCHED_PAYLOAD = {
    "sku_id":      "SKU-PROD-002",
    "location_id": "loc-001",
    "quantity":    20,
}

CRITICAL_ALERT_PAYLOAD = {
    "sku_id":           "SKU-PROD-001",
    "location_id":      "a3bb189e-8bf9-3888-9912-ace4e6543002",
    "current_stock":    2,
    "threshold_limite": 10,
}

STOCK_OUT_PAYLOAD = {
    "sku_id":           "SKU-PROD-001",
    "location_id":      "a3bb189e-8bf9-3888-9912-ace4e6543002",
    "current_stock":    0,
    "threshold_limite": 10,
}


# ─── Fixture de sesión mock ───────────────────────────────────────────────────

@pytest.fixture
def db() -> MagicMock:
    return MagicMock()


# ═══════════════════════════════════════════════════════════════════════════════
# §1 — Validación de schema (InventoryEventCreate)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemaStockReserved:

    def test_payload_valido_no_lanza(self):
        InventoryEventCreate(
            source="inventory",
            event_type="stock_reserved",
            payload=STOCK_RESERVED_PAYLOAD,
        )

    def test_quantity_cero_rechazado(self):
        with pytest.raises(ValidationError, match="quantity"):
            InventoryEventCreate(
                source="inventory",
                event_type="stock_reserved",
                payload={**STOCK_RESERVED_PAYLOAD, "quantity": 0},
            )

    def test_expires_at_antes_de_created_at_rechazado(self):
        with pytest.raises(ValidationError):
            InventoryEventCreate(
                source="inventory",
                event_type="stock_reserved",
                payload={
                    **STOCK_RESERVED_PAYLOAD,
                    "created_at": _LATER.isoformat(),
                    "expires_at": _NOW.isoformat(),
                },
            )

    def test_falta_reservation_id_rechazado(self):
        incompleto = {k: v for k, v in STOCK_RESERVED_PAYLOAD.items() if k != "reservation_id"}
        with pytest.raises(ValidationError):
            InventoryEventCreate(source="inventory", event_type="stock_reserved", payload=incompleto)

    def test_falta_sku_id_rechazado(self):
        incompleto = {k: v for k, v in STOCK_RESERVED_PAYLOAD.items() if k != "sku_id"}
        with pytest.raises(ValidationError):
            InventoryEventCreate(source="inventory", event_type="stock_reserved", payload=incompleto)


class TestSchemaAlertTypes:

    @pytest.mark.parametrize("event_type", ["critical_threshold_reached", "stock_out_error"])
    def test_payload_valido_no_lanza(self, event_type):
        InventoryEventCreate(
            source="inventory",
            event_type=event_type,
            payload=CRITICAL_ALERT_PAYLOAD,
        )

    @pytest.mark.parametrize("event_type", ["critical_threshold_reached", "stock_out_error"])
    def test_falta_current_stock_rechazado(self, event_type):
        incompleto = {k: v for k, v in CRITICAL_ALERT_PAYLOAD.items() if k != "current_stock"}
        with pytest.raises(ValidationError):
            InventoryEventCreate(source="inventory", event_type=event_type, payload=incompleto)

    @pytest.mark.parametrize("event_type", ["critical_threshold_reached", "stock_out_error"])
    def test_current_stock_negativo_rechazado(self, event_type):
        with pytest.raises(ValidationError, match="current_stock"):
            InventoryEventCreate(
                source="inventory",
                event_type=event_type,
                payload={**CRITICAL_ALERT_PAYLOAD, "current_stock": -1},
            )

    @pytest.mark.parametrize("event_type", ["critical_threshold_reached", "stock_out_error"])
    def test_falta_threshold_limite_rechazado(self, event_type):
        incompleto = {k: v for k, v in CRITICAL_ALERT_PAYLOAD.items() if k != "threshold_limite"}
        with pytest.raises(ValidationError):
            InventoryEventCreate(source="inventory", event_type=event_type, payload=incompleto)


class TestSchemaGenericMovementTypes:

    @pytest.mark.parametrize("event_type", [
        "stock_received", "stock_dispatched", "stock_adjusted", "stock_transfer_initiated",
    ])
    def test_con_sku_id_no_lanza(self, event_type):
        InventoryEventCreate(
            source="inventory",
            event_type=event_type,
            payload={"sku_id": "SKU-001", "quantity": 10},
        )

    @pytest.mark.parametrize("event_type", [
        "stock_received", "stock_dispatched", "stock_adjusted", "stock_transfer_initiated",
    ])
    def test_sin_sku_id_rechazado(self, event_type):
        with pytest.raises(ValidationError, match="sku_id"):
            InventoryEventCreate(
                source="inventory",
                event_type=event_type,
                payload={"quantity": 10},
            )

    def test_event_type_invalido_rechazado(self):
        with pytest.raises(ValidationError):
            InventoryEventCreate(
                source="inventory",
                event_type="stock_teleportado",
                payload={"sku_id": "SKU-001"},
            )

    def test_source_distinto_de_inventory_rechazado(self):
        with pytest.raises(ValidationError):
            InventoryEventCreate(
                source="payments",
                event_type="stock_received",
                payload=STOCK_RECEIVED_PAYLOAD,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# §2 — Procesador ETL (process_inventory_event)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProcesadorStockReceived:

    def test_crea_fact_inventory_movement(self, db):
        raw = _make_raw("stock_received", STOCK_RECEIVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _added_of(db, FactInventoryMovement)

    def test_sku_id_correcto(self, db):
        raw = _make_raw("stock_received", STOCK_RECEIVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _movement(db).sku_id == "SKU-PROD-001"

    def test_quantity_received_mapeado(self, db):
        raw = _make_raw("stock_received", STOCK_RECEIVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _movement(db).quantity == 100

    def test_movement_at_usa_received_at(self, db):
        raw = _make_raw("stock_received", STOCK_RECEIVED_PAYLOAD)
        process_inventory_event(db, raw)
        mov = _movement(db)
        assert mov.movement_at.year == 2026
        assert mov.movement_at.month == 6
        assert mov.movement_at.day == 28

    def test_raw_event_id_vinculado(self, db):
        raw = _make_raw("stock_received", STOCK_RECEIVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _movement(db).raw_event_id == raw.event_id

    def test_sin_sku_id_lanza_error(self, db):
        raw = _make_raw("stock_received", {"quantity_received": 50})
        with pytest.raises(InventoryProcessingError, match="sku_id"):
            process_inventory_event(db, raw)

    def test_sin_sku_id_no_escribe_en_warehouse(self, db):
        raw = _make_raw("stock_received", {"quantity_received": 50})
        with pytest.raises(InventoryProcessingError):
            process_inventory_event(db, raw)
        assert not _added_of(db, FactInventoryMovement)

    def test_flush_llamado(self, db):
        raw = _make_raw("stock_received", STOCK_RECEIVED_PAYLOAD)
        process_inventory_event(db, raw)
        db.flush.assert_called()


class TestProcesadorStockReserved:

    def test_crea_fact_inventory_movement(self, db):
        raw = _make_raw("stock_reserved", STOCK_RESERVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _added_of(db, FactInventoryMovement)

    def test_reservation_id_mapeado(self, db):
        raw = _make_raw("stock_reserved", STOCK_RESERVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _movement(db).reservation_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_order_id_mapeado(self, db):
        raw = _make_raw("stock_reserved", STOCK_RESERVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _movement(db).order_id == "ord-2026-00123"

    def test_quantity_mapeado(self, db):
        raw = _make_raw("stock_reserved", STOCK_RESERVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _movement(db).quantity == 5

    def test_expires_at_mapeado(self, db):
        raw = _make_raw("stock_reserved", STOCK_RESERVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _movement(db).expires_at is not None

    def test_movement_at_usa_created_at(self, db):
        raw = _make_raw("stock_reserved", STOCK_RESERVED_PAYLOAD)
        process_inventory_event(db, raw)
        mov = _movement(db)
        assert mov.movement_at is not None
        assert mov.movement_at.tzinfo is not None

    def test_no_crea_alerta(self, db):
        raw = _make_raw("stock_reserved", STOCK_RESERVED_PAYLOAD)
        process_inventory_event(db, raw)
        assert not _added_of(db, FactInventoryAlert)


class TestProcesadorMovimientosGenericos:

    @pytest.mark.parametrize("event_type", [
        "stock_dispatched", "stock_adjusted", "stock_transfer_initiated",
    ])
    def test_crea_fact_inventory_movement(self, db, event_type):
        raw = _make_raw(event_type, STOCK_DISPATCHED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _added_of(db, FactInventoryMovement)

    @pytest.mark.parametrize("event_type", [
        "stock_dispatched", "stock_adjusted", "stock_transfer_initiated",
    ])
    def test_event_type_correcto_en_fact(self, db, event_type):
        raw = _make_raw(event_type, STOCK_DISPATCHED_PAYLOAD)
        process_inventory_event(db, raw)
        assert _movement(db).event_type == event_type

    @pytest.mark.parametrize("event_type", [
        "stock_dispatched", "stock_adjusted", "stock_transfer_initiated",
    ])
    def test_no_crea_alerta(self, db, event_type):
        raw = _make_raw(event_type, STOCK_DISPATCHED_PAYLOAD)
        process_inventory_event(db, raw)
        assert not _added_of(db, FactInventoryAlert)

    @pytest.mark.parametrize("event_type", [
        "stock_dispatched", "stock_adjusted", "stock_transfer_initiated",
    ])
    def test_sin_sku_id_lanza_error(self, db, event_type):
        raw = _make_raw(event_type, {"quantity": 10})
        with pytest.raises(InventoryProcessingError, match="sku_id"):
            process_inventory_event(db, raw)


class TestProcesadorCriticalThresholdReached:

    def test_crea_fact_inventory_alert(self, db):
        raw = _make_raw("critical_threshold_reached", CRITICAL_ALERT_PAYLOAD)
        process_inventory_event(db, raw)
        assert _added_of(db, FactInventoryAlert)

    def test_sku_id_correcto(self, db):
        raw = _make_raw("critical_threshold_reached", CRITICAL_ALERT_PAYLOAD)
        process_inventory_event(db, raw)
        assert _alert(db).sku_id == "SKU-PROD-001"

    def test_current_stock_mapeado(self, db):
        raw = _make_raw("critical_threshold_reached", CRITICAL_ALERT_PAYLOAD)
        process_inventory_event(db, raw)
        assert _alert(db).current_stock == 2

    def test_threshold_limite_mapeado(self, db):
        raw = _make_raw("critical_threshold_reached", CRITICAL_ALERT_PAYLOAD)
        process_inventory_event(db, raw)
        assert _alert(db).threshold_limite == 10

    def test_is_stock_out_false_cuando_stock_positivo(self, db):
        raw = _make_raw("critical_threshold_reached", CRITICAL_ALERT_PAYLOAD)
        process_inventory_event(db, raw)
        assert _alert(db).is_stock_out is False

    def test_is_stock_out_true_cuando_stock_cero(self, db):
        payload = {**CRITICAL_ALERT_PAYLOAD, "current_stock": 0}
        raw = _make_raw("critical_threshold_reached", payload)
        process_inventory_event(db, raw)
        assert _alert(db).is_stock_out is True

    def test_no_crea_movement(self, db):
        raw = _make_raw("critical_threshold_reached", CRITICAL_ALERT_PAYLOAD)
        process_inventory_event(db, raw)
        assert not _added_of(db, FactInventoryMovement)

    def test_raw_event_id_vinculado(self, db):
        raw = _make_raw("critical_threshold_reached", CRITICAL_ALERT_PAYLOAD)
        process_inventory_event(db, raw)
        assert _alert(db).raw_event_id == raw.event_id

    def test_flush_llamado(self, db):
        raw = _make_raw("critical_threshold_reached", CRITICAL_ALERT_PAYLOAD)
        process_inventory_event(db, raw)
        db.flush.assert_called()


class TestProcesadorStockOutError:

    def test_crea_fact_inventory_alert(self, db):
        raw = _make_raw("stock_out_error", STOCK_OUT_PAYLOAD)
        process_inventory_event(db, raw)
        assert _added_of(db, FactInventoryAlert)

    def test_is_stock_out_true_por_event_type(self, db):
        raw = _make_raw("stock_out_error", STOCK_OUT_PAYLOAD)
        process_inventory_event(db, raw)
        assert _alert(db).is_stock_out is True

    def test_is_stock_out_true_incluso_con_stock_positivo(self, db):
        # stock_out_error fuerza is_stock_out=True independiente del valor de current_stock
        payload = {**STOCK_OUT_PAYLOAD, "current_stock": 5}
        raw = _make_raw("stock_out_error", payload)
        process_inventory_event(db, raw)
        assert _alert(db).is_stock_out is True

    def test_event_type_en_fact_es_stock_out_error(self, db):
        raw = _make_raw("stock_out_error", STOCK_OUT_PAYLOAD)
        process_inventory_event(db, raw)
        assert _alert(db).event_type == "stock_out_error"


class TestProcesadorErrores:

    def test_event_type_desconocido_lanza_error(self, db):
        raw = _make_raw("stock_teleportado", {"sku_id": "SKU-001"})
        with pytest.raises(InventoryProcessingError, match="no soportado"):
            process_inventory_event(db, raw)

    def test_event_type_desconocido_no_escribe(self, db):
        raw = _make_raw("stock_teleportado", {"sku_id": "SKU-001"})
        with pytest.raises(InventoryProcessingError):
            process_inventory_event(db, raw)
        db.add.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# §3 — Endpoint HTTP POST /v1/events (source=inventory)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndpointStockReserved:

    def test_payload_valido_retorna_202(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "stock_reserved",
            "payload": STOCK_RESERVED_PAYLOAD,
        })
        assert resp.status_code == 202

    def test_respuesta_contiene_event_id_y_acknowledged(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "stock_reserved",
            "payload": STOCK_RESERVED_PAYLOAD,
        })
        body = resp.json()
        assert body["status"] == "acknowledged"
        assert "event_id" in body

    def test_quantity_cero_retorna_422(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "stock_reserved",
            "payload": {**STOCK_RESERVED_PAYLOAD, "quantity": 0},
        })
        assert resp.status_code == 422

    def test_payload_incompleto_sin_reservation_id_retorna_422(self, client):
        incompleto = {k: v for k, v in STOCK_RESERVED_PAYLOAD.items() if k != "reservation_id"}
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "stock_reserved",
            "payload": incompleto,
        })
        assert resp.status_code == 422

    def test_fechas_invertidas_retorna_422(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "stock_reserved",
            "payload": {
                **STOCK_RESERVED_PAYLOAD,
                "created_at": _LATER.isoformat(),
                "expires_at": _NOW.isoformat(),
            },
        })
        assert resp.status_code == 422


class TestEndpointAlertTypes:

    def test_critical_threshold_valido_retorna_202(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "critical_threshold_reached",
            "payload": CRITICAL_ALERT_PAYLOAD,
        })
        assert resp.status_code == 202

    def test_stock_out_error_valido_retorna_202(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "stock_out_error",
            "payload": STOCK_OUT_PAYLOAD,
        })
        assert resp.status_code == 202

    def test_sin_current_stock_retorna_422(self, client):
        incompleto = {k: v for k, v in CRITICAL_ALERT_PAYLOAD.items() if k != "current_stock"}
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "critical_threshold_reached",
            "payload": incompleto,
        })
        assert resp.status_code == 422

    def test_current_stock_negativo_retorna_422(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "critical_threshold_reached",
            "payload": {**CRITICAL_ALERT_PAYLOAD, "current_stock": -1},
        })
        assert resp.status_code == 422

    def test_sin_threshold_limite_retorna_422(self, client):
        incompleto = {k: v for k, v in CRITICAL_ALERT_PAYLOAD.items() if k != "threshold_limite"}
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "critical_threshold_reached",
            "payload": incompleto,
        })
        assert resp.status_code == 422


class TestEndpointGenericMovementTypes:

    def test_stock_received_con_sku_id_retorna_202(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "stock_received",
            "payload": STOCK_RECEIVED_PAYLOAD,
        })
        assert resp.status_code == 202

    def test_stock_received_sin_sku_id_retorna_422(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "stock_received",
            "payload": {"quantity_received": 50},
        })
        assert resp.status_code == 422

    @pytest.mark.parametrize("event_type", [
        "stock_dispatched", "stock_adjusted", "stock_transfer_initiated",
    ])
    def test_con_sku_id_retorna_202(self, client, event_type):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": event_type,
            "payload": {"sku_id": "SKU-PROD-001", "quantity": 10},
        })
        assert resp.status_code == 202

    @pytest.mark.parametrize("event_type", [
        "stock_dispatched", "stock_adjusted", "stock_transfer_initiated",
    ])
    def test_sin_sku_id_retorna_422(self, client, event_type):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": event_type,
            "payload": {"quantity": 10},
        })
        assert resp.status_code == 422

    def test_event_type_invalido_retorna_422(self, client):
        resp = client.post("/v1/events", json={
            "source": "inventory",
            "event_type": "stock_teleportado",
            "payload": {"sku_id": "SKU-001"},
        })
        assert resp.status_code == 422