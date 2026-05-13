"""
Service para cálculos analíticos del dominio Orders.

Contiene funciones para calcular KPIs desde fact_orders.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

from app.models import FactOrder


# ================================================================
# FUNCIONES DE CÁLCULO DE KPIs
# ================================================================

def get_total_orders(db: Session) -> int:
    """Obtiene total de órdenes."""
    return db.query(func.count(FactOrder.id)).scalar() or 0


def get_delivery_rate(db: Session) -> float:
    """
    Calcula tasa de entregas completadas.
    Fórmula: COUNT(delivery_completed=TRUE) / COUNT(*)
    """
    total = db.query(func.count(FactOrder.id)).scalar() or 0
    if total == 0:
        return 0.0
    
    delivered = db.query(func.count(FactOrder.id)).filter(
        FactOrder.delivery_completed == True
    ).scalar() or 0
    
    return round(delivered / total, 2)


def get_payment_failure_rate(db: Session) -> float:
    """
    Calcula tasa de pagos fallidos.
    Fórmula: COUNT(status='payment_failed') / COUNT(status IN ('paid', 'payment_failed'))
    Solo cuenta órdenes que tuvieron intento de pago (basado en status).
    """
    # Contar órdenes con intento de pago (status="paid" O status="payment_failed")
    payment_attempted = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status.in_(["paid", "payment_failed"])
    ).scalar() or 0
    
    if payment_attempted == 0:
        return 0.0
    
    failed = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status == "payment_failed"
    ).scalar() or 0
    
    return round(failed / payment_attempted, 2)


def get_payment_success_rate(db: Session) -> float:
    """
    Calcula tasa de pagos exitosos.
    Fórmula: COUNT(status='paid') / COUNT(status IN ('paid', 'payment_failed'))
    Solo cuenta órdenes que tuvieron intento de pago (basado en status).
    """
    # Contar órdenes con intento de pago (status="paid" O status="payment_failed")
    payment_attempted = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status.in_(["paid", "payment_failed"])
    ).scalar() or 0
    
    if payment_attempted == 0:
        return 0.0
    
    successful = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status == "paid"
    ).scalar() or 0
    
    return round(successful / payment_attempted, 2)


def get_avg_processing_time(db: Session) -> float:
    """
    Calcula tiempo promedio de procesamiento en horas.
    Solo considera órdenes entregadas (delivery_completed=TRUE).
    """
    avg_seconds = db.query(
        func.avg(FactOrder.processing_time_seconds)
    ).filter(
        FactOrder.delivery_completed == True,
        FactOrder.processing_time_seconds.isnot(None),
        FactOrder.processing_time_seconds > 0
    ).scalar()
    
    if avg_seconds is None or avg_seconds == 0:
        return 0.0
    
    hours = float(avg_seconds) / 3600
    return round(hours, 2)


def get_revenue_total(db: Session) -> float:
    """Calcula ingresos totales."""
    total = db.query(func.sum(FactOrder.total_amount)).scalar() or 0.0
    return round(float(total), 2)


def get_average_order_value(db: Session) -> float:
    """Calcula valor promedio por orden."""
    total_orders = get_total_orders(db)
    if total_orders == 0:
        return 0.0
    
    total_revenue = get_revenue_total(db)
    return round(total_revenue / total_orders, 2)


def get_stock_reservation_rate(db: Session) -> float:
    """
    Calcula tasa de órdenes con stock reservado.
    Fórmula: COUNT(stock_reserved=TRUE) / COUNT(*)
    """
    total = db.query(func.count(FactOrder.id)).scalar() or 0
    if total == 0:
        return 0.0
    
    reserved = db.query(func.count(FactOrder.id)).filter(
        FactOrder.stock_reserved == True
    ).scalar() or 0
    
    return round(reserved / total, 2)


def get_fulfillment_rate(db: Session) -> float:
    """
    Calcula tasa de fulfillment completo.
    Fórmula: COUNT(status='paid' AND delivery_completed=TRUE) / COUNT(*)
    """
    total = db.query(func.count(FactOrder.id)).scalar() or 0
    if total == 0:
        return 0.0
    
    fulfilled = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status == "paid",
        FactOrder.delivery_completed == True
    ).scalar() or 0
    
    return round(fulfilled / total, 2)


def get_sla_compliance(db: Session) -> float:
    """
    Calcula cumplimiento SLA.
    SLA = (órdenes con pago exitoso + órdenes entregadas) / (total * 2)
    O interpretado como: (entregas + pagos exitosos) / 2 / 100%
    """
    delivery_rate = get_delivery_rate(db)
    payment_success_rate = get_payment_success_rate(db)
    
    sla = (delivery_rate + payment_success_rate) / 2
    return round(sla, 2)


# ================================================================
# FUNCIONES DE AGREGACIÓN POR DIMENSIÓN
# ================================================================

def get_orders_by_channel(db: Session) -> List[Tuple[str, int, float]]:
    """
    Obtiene distribución de órdenes por canal de venta.
    
    Returns:
        List de tuples: [(channel, count, revenue), ...]
    """
    results = db.query(
        FactOrder.sales_channel,
        func.count(FactOrder.id).label("count"),
        func.sum(FactOrder.total_amount).label("revenue")
    ).group_by(FactOrder.sales_channel).all()
    
    return [(ch, count or 0, float(rev) if rev else 0.0) for ch, count, rev in results]


def get_orders_by_status(db: Session) -> List[Tuple[str, int]]:
    """
    Obtiene distribución de órdenes por estado.
    
    Returns:
        List de tuples: [(status, count), ...]
    """
    results = db.query(
        FactOrder.status,
        func.count(FactOrder.id).label("count")
    ).group_by(FactOrder.status).all()
    
    return [(status, count or 0) for status, count in results]


def get_orders_by_date(db: Session, days: int = 30) -> List[Dict]:
    """
    Obtiene distribución de órdenes por fecha (últimos N días).
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar
        
    Returns:
        List de dicts: [{'date': '2026-05-09', 'count': 25, 'revenue': ...}, ...]
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    results = db.query(
        cast(FactOrder.created_at, Date).label("date"),
        func.count(FactOrder.id).label("order_count"),
        func.sum(FactOrder.total_amount).label("revenue")
    ).filter(
        FactOrder.created_at >= cutoff_date
    ).group_by(
        cast(FactOrder.created_at, Date)
    ).order_by(
        cast(FactOrder.created_at, Date).desc()
    ).all()
    
    timeline = []
    for date, count, revenue in results:
        avg_value = float(revenue) / count if count and revenue else 0.0
        timeline.append({
            "date": date.isoformat(),
            "order_count": count or 0,
            "revenue": round(float(revenue) if revenue else 0.0, 2),
            "avg_order_value": round(avg_value, 2)
        })
    
    return timeline


# ================================================================
# FUNCIONES DE RESPUESTA CONSOLIDADA
# ================================================================

def get_all_kpis(db: Session) -> Dict:
    """
    Calcula todos los KPIs consolidados.
    
    Returns:
        Dict con todos los KPIs principales
    """
    return {
        "total_orders": get_total_orders(db),
        "delivery_rate": get_delivery_rate(db),
        "payment_failure_rate": get_payment_failure_rate(db),
        "payment_success_rate": get_payment_success_rate(db),
        "avg_processing_time_hours": get_avg_processing_time(db),
        "revenue_total": get_revenue_total(db),
        "average_order_value": get_average_order_value(db),
        "sla_compliance": get_sla_compliance(db),
        "stock_reservation_rate": get_stock_reservation_rate(db),
        "fulfillment_rate": get_fulfillment_rate(db)
    }
