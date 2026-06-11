"""
Tests de integración — process_order_event (ETL processor).

A diferencia de los tests unitarios con MagicMock, estos tests usan SQLite
en memoria para ejecutar queries SQLAlchemy reales.  Bugs como un filtro
incorrecto en la búsqueda de orden existente, un nombre de columna mal
escrito, o un flag que no se actualiza quedarían expuestos aquí.

Fixture 'db_session' provisto por conftest.py.
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.etl.processors.order_processor import (
    OrderPayloadValidationError,
    process_order_event,
)
from app.models import FactOrder
from app.models.raw.raw_events import RawEvent


# ─── Helper ──────────────────────────────────────────────────────────────────

def _raw(event_type: str, payload: dict) -> RawEvent:
    """RawEvent en memoria (no persistido). El processor solo lee sus atributos."""
    return RawEvent(
        event_id=uuid.uuid4(),
        source="orders",
        event_type=event_type,
        payload=payload,
        ingested_at=datetime.now(tz=timezone.utc),
        processed=False,
    )


BASE = {
    "order_id": 1001,
    "customer_id": 501,
    "sales_channel": "web",
    "total_amount": 49990.0,
    "total_items": 2,
}


# ─── Creación ────────────────────────────────────────────────────────────────

class TestCrearNuevaOrden:
    """pedido_creado → INSERT en fact_orders."""

    def test_inserta_fila_en_db(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        result = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert result is not None

    def test_status_inicial_es_created(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.status == "created"

    def test_customer_id_almacenado(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.customer_id == 501

    def test_total_amount_almacenado(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.total_amount == 49990.0

    def test_sales_channel_almacenado(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.sales_channel == "web"

    def test_payment_success_por_defecto_false(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.payment_success is False

    def test_no_duplica_filas(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        count = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).count()
        assert count == 1


# ─── Actualización (UPDATE sobre registro existente) ─────────────────────────

class TestActualizarOrdenExistente:
    """Eventos subsiguientes sobre la misma order_id hacen UPDATE, no INSERT."""

    def test_pedido_pagado_actualiza_status(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        process_order_event(db_session, _raw("pedido_pagado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.status == "paid"

    def test_pedido_pagado_activa_payment_success(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        process_order_event(db_session, _raw("pedido_pagado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.payment_success is True

    def test_pago_fallido_desactiva_payment_success(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        process_order_event(db_session, _raw("pago_fallido", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.payment_success is False
        assert order.status == "payment_failed"

    def test_stock_reservado_activa_flag_y_status(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        process_order_event(db_session, _raw("stock_reservado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.stock_reserved is True
        assert order.status == "stock_reserved"

    def test_no_crea_fila_duplicada_al_actualizar(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        process_order_event(db_session, _raw("pedido_pagado", BASE))
        count = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).count()
        assert count == 1


# ─── Entrega y cálculo de processing_time ────────────────────────────────────

class TestEntrega:
    def test_pedido_entregado_activa_delivery_completed(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        process_order_event(db_session, _raw("pedido_entregado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.delivery_completed is True

    def test_pedido_entregado_status_delivered(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        process_order_event(db_session, _raw("pedido_entregado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.status == "delivered"

    def test_processing_time_calculado_al_entregar(self, db_session: Session):
        process_order_event(db_session, _raw("pedido_creado", BASE))
        process_order_event(db_session, _raw("pedido_entregado", BASE))
        order = db_session.query(FactOrder).filter(FactOrder.order_id == 1001).first()
        assert order.processing_time_seconds is not None
        assert order.processing_time_seconds >= 0


# ─── Validación de payload ────────────────────────────────────────────────────

class TestValidacionPayload:
    def test_orden_sin_order_id_lanza_error(self, db_session: Session):
        payload = {k: v for k, v in BASE.items() if k != "order_id"}
        with pytest.raises(OrderPayloadValidationError):
            process_order_event(db_session, _raw("pedido_creado", payload))

    def test_orden_sin_customer_id_lanza_error(self, db_session: Session):
        payload = {k: v for k, v in BASE.items() if k != "customer_id"}
        with pytest.raises(OrderPayloadValidationError):
            process_order_event(db_session, _raw("pedido_creado", payload))

    def test_error_validacion_no_crea_fila(self, db_session: Session):
        payload = {k: v for k, v in BASE.items() if k != "order_id"}
        with pytest.raises(OrderPayloadValidationError):
            process_order_event(db_session, _raw("pedido_creado", payload))
        assert db_session.query(FactOrder).count() == 0

    def test_order_id_nulo_lanza_error(self, db_session: Session):
        payload = {**BASE, "order_id": None}
        with pytest.raises(OrderPayloadValidationError):
            process_order_event(db_session, _raw("pedido_creado", payload))
