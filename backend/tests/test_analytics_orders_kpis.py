"""
Tests de integración — funciones KPI de orders_kpis.py.

Usan SQLite en memoria para ejecutar queries SQL reales contra fact_orders.
Un bug en el nombre de columna (ej: 'delivery_completed' → 'delivered'),
un filtro incorrecto (ej: status='completed' en vez de 'paid'), o una
agregación equivocada (COUNT en vez de SUM) sería detectado aquí pero
no por tests con MagicMock.

Fixture 'db_session' provisto por conftest.py.
"""
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.analytics.orders_kpis import (
    get_average_order_value,
    get_delivery_rate,
    get_fulfillment_rate,
    get_orders_by_channel,
    get_orders_by_status,
    get_payment_failure_rate,
    get_payment_success_rate,
    get_revenue_total,
    get_stock_reservation_rate,
    get_total_orders,
)
from app.models import FactOrder


# ─── Helper ──────────────────────────────────────────────────────────────────

def _order(order_id: int, **kwargs) -> FactOrder:
    """Crea una instancia FactOrder con valores por defecto sobreescribibles."""
    defaults = {
        "customer_id": 1,
        "sales_channel": "web",
        "status": "created",
        "total_amount": 10000.0,
        "total_items": 1,
        "payment_success": False,
        "stock_reserved": False,
        "delivery_completed": False,
        "processing_time_seconds": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return FactOrder(order_id=order_id, **defaults)


def _seed(db: Session, *orders: FactOrder) -> None:
    for o in orders:
        db.add(o)
    db.flush()


# ─── get_total_orders ─────────────────────────────────────────────────────────

class TestGetTotalOrders:
    def test_tabla_vacia_devuelve_cero(self, db_session: Session):
        assert get_total_orders(db_session) == 0

    def test_cuenta_todas_las_filas(self, db_session: Session):
        _seed(db_session, _order(1), _order(2), _order(3))
        assert get_total_orders(db_session) == 3

    def test_devuelve_int(self, db_session: Session):
        _seed(db_session, _order(10))
        assert isinstance(get_total_orders(db_session), int)


# ─── get_delivery_rate ────────────────────────────────────────────────────────

class TestGetDeliveryRate:
    def test_tabla_vacia_devuelve_cero(self, db_session: Session):
        assert get_delivery_rate(db_session) == 0.0

    def test_todas_entregadas(self, db_session: Session):
        _seed(db_session,
              _order(1, delivery_completed=True),
              _order(2, delivery_completed=True))
        assert get_delivery_rate(db_session) == 1.0

    def test_ninguna_entregada(self, db_session: Session):
        _seed(db_session, _order(1), _order(2))
        assert get_delivery_rate(db_session) == 0.0

    def test_entrega_parcial_un_tercio(self, db_session: Session):
        _seed(db_session,
              _order(1, delivery_completed=True),
              _order(2),
              _order(3))
        assert get_delivery_rate(db_session) == round(1 / 3, 2)

    def test_columna_correcta_no_confunde_con_status(self, db_session: Session):
        """Verifica que filtra por 'delivery_completed' (Boolean), no por status."""
        _seed(db_session,
              _order(1, status="delivered", delivery_completed=False),
              _order(2, delivery_completed=True))
        # Solo orden 2 tiene delivery_completed=True → 0.5
        assert get_delivery_rate(db_session) == 0.5


# ─── get_payment_failure_rate / get_payment_success_rate ─────────────────────

class TestGetPaymentRates:
    def test_tasa_fallida_cero_sin_intentos(self, db_session: Session):
        _seed(db_session, _order(1, status="created"))
        assert get_payment_failure_rate(db_session) == 0.0

    def test_un_fallido_de_dos_intentos(self, db_session: Session):
        _seed(db_session,
              _order(1, status="paid"),
              _order(2, status="payment_failed"))
        assert get_payment_failure_rate(db_session) == 0.5

    def test_tasa_exitosa_todos_pagados(self, db_session: Session):
        _seed(db_session,
              _order(1, status="paid"),
              _order(2, status="paid"))
        assert get_payment_success_rate(db_session) == 1.0

    def test_tasas_suman_uno(self, db_session: Session):
        """Con un mix de pagados y fallidos, éxito + fallo = 1.0."""
        _seed(db_session,
              _order(1, status="paid"),
              _order(2, status="paid"),
              _order(3, status="payment_failed"))
        s = get_payment_success_rate(db_session)
        f = get_payment_failure_rate(db_session)
        assert round(s + f, 10) == 1.0

    def test_ordenes_en_otros_estados_no_se_cuentan(self, db_session: Session):
        """status='created' o 'stock_reserved' no son intentos de pago."""
        _seed(db_session,
              _order(1, status="created"),
              _order(2, status="stock_reserved"),
              _order(3, status="paid"))
        # Solo orden 3 es intento de pago → success rate = 1.0
        assert get_payment_success_rate(db_session) == 1.0


# ─── get_revenue_total ────────────────────────────────────────────────────────

class TestGetRevenueTotal:
    def test_tabla_vacia_devuelve_cero(self, db_session: Session):
        assert get_revenue_total(db_session) == 0.0

    def test_suma_solo_ordenes_con_pago_exitoso(self, db_session: Session):
        _seed(db_session,
              _order(1, payment_success=True,  total_amount=30000.0),
              _order(2, payment_success=True,  total_amount=20000.0),
              _order(3, payment_success=False, total_amount=99999.0))  # no debe sumarse
        assert get_revenue_total(db_session) == 50000.0

    def test_excluye_ordenes_sin_pago(self, db_session: Session):
        _seed(db_session, _order(1, payment_success=False, total_amount=99999.0))
        assert get_revenue_total(db_session) == 0.0


# ─── get_average_order_value ─────────────────────────────────────────────────

class TestGetAverageOrderValue:
    def test_tabla_vacia_devuelve_cero(self, db_session: Session):
        assert get_average_order_value(db_session) == 0.0

    def test_promedio_correcto(self, db_session: Session):
        # revenue = 40 000, total_orders = 2 → avg = 20 000
        _seed(db_session,
              _order(1, payment_success=True, total_amount=10000.0),
              _order(2, payment_success=True, total_amount=30000.0))
        assert get_average_order_value(db_session) == 20000.0


# ─── get_stock_reservation_rate ──────────────────────────────────────────────

class TestGetStockReservationRate:
    def test_sin_reservas_devuelve_cero(self, db_session: Session):
        _seed(db_session, _order(1, stock_reserved=False))
        assert get_stock_reservation_rate(db_session) == 0.0

    def test_reserva_parcial(self, db_session: Session):
        _seed(db_session,
              _order(1, stock_reserved=True),
              _order(2, stock_reserved=False))
        assert get_stock_reservation_rate(db_session) == 0.5


# ─── get_fulfillment_rate ─────────────────────────────────────────────────────

class TestGetFulfillmentRate:
    def test_tabla_vacia_devuelve_cero(self, db_session: Session):
        assert get_fulfillment_rate(db_session) == 0.0

    def test_requiere_status_paid_y_delivery_completed(self, db_session: Session):
        """
        Solo cuenta como 'fulfilled' si status='paid' AND delivery_completed=True.
        Un 'paid' sin entrega y un 'delivered' sin status 'paid' no cuentan.
        """
        _seed(db_session,
              _order(1, status="paid",      delivery_completed=True),   # ✓ fulfilled
              _order(2, status="paid",      delivery_completed=False),  # ✗ sin entrega
              _order(3, status="delivered", delivery_completed=True))   # ✗ status incorrecto
        assert get_fulfillment_rate(db_session) == round(1 / 3, 2)


# ─── get_orders_by_channel ────────────────────────────────────────────────────

class TestGetOrdersByChannel:
    def test_tabla_vacia_devuelve_lista_vacia(self, db_session: Session):
        assert get_orders_by_channel(db_session) == []

    def test_agrupa_por_canal(self, db_session: Session):
        _seed(db_session,
              _order(1, sales_channel="web", total_amount=10000.0),
              _order(2, sales_channel="web", total_amount=20000.0),
              _order(3, sales_channel="app", total_amount=5000.0))
        result = {ch: (cnt, rev) for ch, cnt, rev in get_orders_by_channel(db_session)}
        assert result["web"] == (2, 30000.0)
        assert result["app"] == (1, 5000.0)

    def test_resultado_tiene_tres_campos_por_fila(self, db_session: Session):
        _seed(db_session, _order(1, sales_channel="web"))
        row = get_orders_by_channel(db_session)[0]
        assert len(row) == 3  # (channel, count, revenue)


# ─── get_orders_by_status ─────────────────────────────────────────────────────

class TestGetOrdersByStatus:
    def test_tabla_vacia_devuelve_lista_vacia(self, db_session: Session):
        assert get_orders_by_status(db_session) == []

    def test_agrupa_por_status(self, db_session: Session):
        _seed(db_session,
              _order(1, status="created"),
              _order(2, status="paid"),
              _order(3, status="paid"))
        by_status = dict(get_orders_by_status(db_session))
        assert by_status["created"] == 1
        assert by_status["paid"] == 2

    def test_resultado_tiene_dos_campos_por_fila(self, db_session: Session):
        _seed(db_session, _order(1))
        row = get_orders_by_status(db_session)[0]
        assert len(row) == 2  # (status, count)
