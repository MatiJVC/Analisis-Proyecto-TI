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
    get_all_kpis,
    get_orders_by_channel,
    get_orders_by_status,
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


# ─── get_all_kpis ─────────────────────────────────────────────────────────────

class TestGetAllKpis:
    def test_tabla_vacia_devuelve_ceros(self, db_session: Session):
        result = get_all_kpis(db_session)
        assert result["total_orders"] == 0
        assert result["delivery_rate"] == 0.0
        assert result["payment_failure_rate"] == 0.0
        assert result["payment_success_rate"] == 0.0
        assert result["revenue_total"] == 0.0
        assert result["average_order_value"] == 0.0
        assert result["stock_reservation_rate"] == 0.0
        assert result["fulfillment_rate"] == 0.0
        assert result["sla_compliance"] == 0.0

    def test_total_orders(self, db_session: Session):
        _seed(db_session, _order(1), _order(2), _order(3))
        assert get_all_kpis(db_session)["total_orders"] == 3

    def test_delivery_rate_parcial(self, db_session: Session):
        _seed(db_session,
              _order(1, delivery_completed=True),
              _order(2),
              _order(3))
        assert get_all_kpis(db_session)["delivery_rate"] == round(1 / 3, 2)

    def test_delivery_rate_columna_correcta(self, db_session: Session):
        """Verifica que filtra por delivery_completed (Boolean), no por status."""
        _seed(db_session,
              _order(1, status="delivered", delivery_completed=False),
              _order(2, delivery_completed=True))
        assert get_all_kpis(db_session)["delivery_rate"] == 0.5

    def test_payment_rates_suman_uno(self, db_session: Session):
        _seed(db_session,
              _order(1, status="paid"),
              _order(2, status="paid"),
              _order(3, status="payment_failed"))
        result = get_all_kpis(db_session)
        assert round(result["payment_success_rate"] + result["payment_failure_rate"], 10) == 1.0

    def test_payment_rates_cero_sin_intentos(self, db_session: Session):
        _seed(db_session, _order(1, status="created"))
        result = get_all_kpis(db_session)
        assert result["payment_failure_rate"] == 0.0
        assert result["payment_success_rate"] == 0.0

    def test_ordenes_en_otros_estados_no_cuentan_como_intentos(self, db_session: Session):
        _seed(db_session,
              _order(1, status="created"),
              _order(2, status="stock_reserved"),
              _order(3, status="paid"))
        assert get_all_kpis(db_session)["payment_success_rate"] == 1.0

    def test_revenue_solo_pagos_exitosos(self, db_session: Session):
        _seed(db_session,
              _order(1, payment_success=True,  total_amount=30000.0),
              _order(2, payment_success=True,  total_amount=20000.0),
              _order(3, payment_success=False, total_amount=99999.0))
        assert get_all_kpis(db_session)["revenue_total"] == 50000.0

    def test_average_order_value(self, db_session: Session):
        _seed(db_session,
              _order(1, payment_success=True, total_amount=10000.0),
              _order(2, payment_success=True, total_amount=30000.0))
        assert get_all_kpis(db_session)["average_order_value"] == 20000.0

    def test_stock_reservation_rate(self, db_session: Session):
        _seed(db_session,
              _order(1, stock_reserved=True),
              _order(2, stock_reserved=False))
        assert get_all_kpis(db_session)["stock_reservation_rate"] == 0.5

    def test_fulfillment_requiere_paid_y_delivery_completed(self, db_session: Session):
        """Solo cuenta como fulfilled si status='paid' AND delivery_completed=True."""
        _seed(db_session,
              _order(1, status="paid",      delivery_completed=True),   # fulfilled
              _order(2, status="paid",      delivery_completed=False),  # sin entrega
              _order(3, status="delivered", delivery_completed=True))   # status incorrecto
        assert get_all_kpis(db_session)["fulfillment_rate"] == round(1 / 3, 2)

    def test_devuelve_todas_las_claves(self, db_session: Session):
        result = get_all_kpis(db_session)
        expected_keys = {
            "total_orders", "delivery_rate", "payment_failure_rate",
            "payment_success_rate", "avg_processing_time_hours",
            "revenue_total", "average_order_value", "sla_compliance",
            "stock_reservation_rate", "fulfillment_rate",
        }
        assert expected_keys.issubset(result.keys())


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
