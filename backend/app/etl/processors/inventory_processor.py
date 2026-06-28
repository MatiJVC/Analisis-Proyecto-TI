from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.warehouse.dim_locations import DimLocation
from app.models.warehouse.dim_products import DimProduct
from app.models.warehouse.fact_inventory_alerts import FactInventoryAlert
from app.models.warehouse.fact_inventory_movements import FactInventoryMovement

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
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _str(value: Any) -> Optional[str]:
    return str(value) if value is not None else None


def _upsert_product(db: Session, sku_id: str, payload: Dict[str, Any]) -> None:
    """Upsert catálogo de producto desde campos opcionales del payload."""
    product_name = payload.get("product_name")
    category = payload.get("category")
    unit = payload.get("unit")
    unit_price = payload.get("unit_price")

    if not any(v is not None for v in [product_name, category, unit, unit_price]):
        return

    now = datetime.now(tz=timezone.utc)
    insert_vals: Dict[str, Any] = {"sku_id": sku_id, "updated_at": now}
    update_vals: Dict[str, Any] = {"updated_at": now}

    if product_name is not None:
        insert_vals["product_name"] = str(product_name)
        update_vals["product_name"] = str(product_name)
    if category is not None:
        insert_vals["category"] = str(category)
        update_vals["category"] = str(category)
    if unit is not None:
        insert_vals["unit"] = str(unit)
        update_vals["unit"] = str(unit)
    if unit_price is not None:
        try:
            insert_vals["unit_price"] = float(unit_price)
            update_vals["unit_price"] = float(unit_price)
        except (TypeError, ValueError):
            pass

    stmt = (
        pg_insert(DimProduct)
        .values(**insert_vals)
        .on_conflict_do_update(index_elements=["sku_id"], set_=update_vals)
    )
    try:
        with db.begin_nested():
            db.execute(stmt)
    except Exception:
        pass


def _upsert_location(db: Session, location_id: str, payload: Dict[str, Any]) -> None:
    """Upsert catálogo de ubicación desde campos opcionales del payload."""
    location_name = payload.get("location_name")
    location_type = payload.get("location_type")
    city = payload.get("city")
    address = payload.get("address")

    if not any(v is not None for v in [location_name, location_type, city, address]):
        return

    now = datetime.now(tz=timezone.utc)
    insert_vals: Dict[str, Any] = {"location_id": location_id, "updated_at": now}
    update_vals: Dict[str, Any] = {"updated_at": now}

    if location_name is not None:
        insert_vals["location_name"] = str(location_name)
        update_vals["location_name"] = str(location_name)
    if location_type is not None:
        insert_vals["location_type"] = str(location_type)
        update_vals["location_type"] = str(location_type)
    if city is not None:
        insert_vals["city"] = str(city)
        update_vals["city"] = str(city)
    if address is not None:
        insert_vals["address"] = str(address)
        update_vals["address"] = str(address)

    stmt = (
        pg_insert(DimLocation)
        .values(**insert_vals)
        .on_conflict_do_update(index_elements=["location_id"], set_=update_vals)
    )
    try:
        with db.begin_nested():
            db.execute(stmt)
    except Exception:
        pass


def _handle_movement(db: Session, raw_event: Any) -> FactInventoryMovement:
    payload: Dict[str, Any] = raw_event.payload or {}
    sku_id = payload.get("sku_id")
    if not sku_id:
        raise InventoryProcessingError("Campo requerido faltante: sku_id")

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

    # Enriquecer dim_products si el evento trae metadata de producto
    _upsert_product(db, str(sku_id), payload)

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

    # Enriquecer dim_products desde alertas (también pueden traer metadata)
    _upsert_product(db, str(sku_id), payload)

    # Enriquecer dim_locations si el evento trae metadata de ubicación
    location_id = payload.get("location_id")
    if location_id is not None:
        _upsert_location(db, str(location_id), payload)

    return alert


def process_inventory_event(
    db: Session, raw_event: Any
) -> Optional[Union[FactInventoryMovement, FactInventoryAlert]]:
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
