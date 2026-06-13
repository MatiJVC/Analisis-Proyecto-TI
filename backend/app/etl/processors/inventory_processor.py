from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.warehouse.fact_inventory_movements import FactInventoryMovement
from app.models.warehouse.fact_inventory_alerts import FactInventoryAlert

_MOVEMENT_TYPES = {
    "stock_received",
    "stock_reserved",
    "stock_dispatched",
    "stock_adjusted",
    "stock_transfer_initiated",
}

_ALERT_TYPES = {
    "critical_threshold_reached",
    "stock_out_error",
}


class InventoryProcessingError(Exception):
    pass


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _str(value: Any) -> Optional[str]:
    return str(value) if value is not None else None


def _handle_movement(db: Session, raw_event: Any) -> FactInventoryMovement:
    payload: Dict[str, Any] = raw_event.payload or {}
    sku_id = payload.get("sku_id")
    if not sku_id:
        raise InventoryProcessingError("Campo requerido faltante: sku_id")

    # Determinar timestamp del movimiento: created_at del payload o ahora
    movement_at = (
        _parse_dt(payload.get("created_at"))
        or _parse_dt(payload.get("movement_at"))
        or datetime.now(tz=timezone.utc)
    )

    movement = FactInventoryMovement(
        event_type=raw_event.event_type,
        sku_id=str(sku_id),
        location_id=_str(payload.get("location_id")),
        quantity=payload.get("quantity") or payload.get("quantity_received"),
        reservation_id=_str(payload.get("reservation_id")),
        order_id=_str(payload.get("order_id")),
        expires_at=_parse_dt(payload.get("expires_at")),
        raw_event_id=raw_event.event_id,
        movement_at=movement_at,
    )
    db.add(movement)
    db.flush()
    return movement


def _handle_alert(db: Session, raw_event: Any) -> FactInventoryAlert:
    payload: Dict[str, Any] = raw_event.payload or {}
    sku_id = payload.get("sku_id")
    if not sku_id:
        raise InventoryProcessingError("Campo requerido faltante: sku_id")

    current_stock = payload.get("current_stock")
    alert = FactInventoryAlert(
        event_type=raw_event.event_type,
        sku_id=str(sku_id),
        location_id=_str(payload.get("location_id")),
        current_stock=int(current_stock) if current_stock is not None else None,
        threshold_limite=payload.get("threshold_limite"),
        is_stock_out=(raw_event.event_type == "stock_out_error" or current_stock == 0),
        raw_event_id=raw_event.event_id,
        alert_at=datetime.now(tz=timezone.utc),
    )
    db.add(alert)
    db.flush()
    return alert


def process_inventory_event(db: Session, raw_event: Any) -> Optional[Union[FactInventoryMovement, FactInventoryAlert]]:
    try:
        if raw_event.event_type in _MOVEMENT_TYPES:
            return _handle_movement(db, raw_event)
        if raw_event.event_type in _ALERT_TYPES:
            return _handle_alert(db, raw_event)
        raise InventoryProcessingError(
            f"event_type no soportado para inventory: {raw_event.event_type}"
        )
    except InventoryProcessingError:
        raise
    except SQLAlchemyError:
        raise
    except Exception as e:
        raise InventoryProcessingError(str(e)) from e
