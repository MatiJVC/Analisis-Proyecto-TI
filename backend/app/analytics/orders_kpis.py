"""
KPIs para cálculos analíticos del dominio Orders.

Contiene funciones para calcular KPIs desde fact_orders.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Integer
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional

from app.models import FactOrder


# ================================================================
# FUNCIONES DE CÁLCULO DE KPIs
# ================================================================

def get_total_orders(db: Session, days: Optional[int] = None) -> int:
    """Obtiene total de órdenes.
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    query = db.query(func.count(FactOrder.id))
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactOrder.created_at >= cutoff_date)
    return query.scalar() or 0


def get_delivery_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula tasa de entregas completadas.
    Fórmula: COUNT(delivery_completed=TRUE) / COUNT(*)
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None
    
    total_query = db.query(func.count(FactOrder.id))
    delivered_query = db.query(func.count(FactOrder.id)).filter(
        FactOrder.delivery_completed == True
    )
    
    if cutoff_date:
        total_query = total_query.filter(FactOrder.created_at >= cutoff_date)
        delivered_query = delivered_query.filter(FactOrder.created_at >= cutoff_date)
    
    total = total_query.scalar() or 0
    delivered = delivered_query.scalar() or 0
    
    if total == 0:
        return 0.0
    
    return round(delivered / total, 2)


def get_payment_failure_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula tasa de pagos fallidos.
    Fórmula: COUNT(status='payment_failed') / COUNT(status IN ('paid', 'payment_failed'))
    Solo cuenta órdenes que tuvieron intento de pago (basado en status).
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None
    
    payment_attempted_query = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status.in_(["paid", "payment_failed"])
    )
    failed_query = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status == "payment_failed"
    )
    
    if cutoff_date:
        payment_attempted_query = payment_attempted_query.filter(FactOrder.created_at >= cutoff_date)
        failed_query = failed_query.filter(FactOrder.created_at >= cutoff_date)
    
    payment_attempted = payment_attempted_query.scalar() or 0
    failed = failed_query.scalar() or 0
    
    if payment_attempted == 0:
        return 0.0
    
    return round(failed / payment_attempted, 2)


def get_payment_success_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula tasa de pagos exitosos.
    Fórmula: COUNT(status='paid') / COUNT(status IN ('paid', 'payment_failed'))
    Solo cuenta órdenes que tuvieron intento de pago (basado en status).
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None
    
    payment_attempted_query = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status.in_(["paid", "payment_failed"])
    )
    successful_query = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status == "paid"
    )
    
    if cutoff_date:
        payment_attempted_query = payment_attempted_query.filter(FactOrder.created_at >= cutoff_date)
        successful_query = successful_query.filter(FactOrder.created_at >= cutoff_date)
    
    payment_attempted = payment_attempted_query.scalar() or 0
    successful = successful_query.scalar() or 0
    
    if payment_attempted == 0:
        return 0.0
    
    return round(successful / payment_attempted, 2)


def get_avg_processing_time(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula tiempo promedio de procesamiento en horas.
    Solo considera órdenes entregadas (delivery_completed=TRUE).
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    query = db.query(
        func.avg(FactOrder.processing_time_seconds)
    ).filter(
        FactOrder.delivery_completed == True,
        FactOrder.processing_time_seconds.isnot(None),
        FactOrder.processing_time_seconds > 0
    )
    
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactOrder.created_at >= cutoff_date)
    
    avg_seconds = query.scalar()
    
    if avg_seconds is None or avg_seconds == 0:
        return 0.0
    
    hours = float(avg_seconds) / 3600
    return round(hours, 2)


def get_revenue_total(db: Session, days: Optional[int] = None) -> float:
    """Calcula ingresos totales.
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    query = db.query(func.sum(FactOrder.total_amount)).filter(
        FactOrder.payment_success == True
    )
    
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactOrder.created_at >= cutoff_date)
    
    total = query.scalar() or 0.0
    return round(float(total), 2)


def get_average_order_value(db: Session, days: Optional[int] = None) -> float:
    """Calcula valor promedio por orden.
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    total_orders = get_total_orders(db, days)
    if total_orders == 0:
        return 0.0
    
    total_revenue = get_revenue_total(db, days)
    return round(total_revenue / total_orders, 2)


def get_stock_reservation_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula tasa de órdenes con stock reservado.
    Fórmula: COUNT(stock_reserved=TRUE) / COUNT(*)
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None
    
    total_query = db.query(func.count(FactOrder.id))
    reserved_query = db.query(func.count(FactOrder.id)).filter(
        FactOrder.stock_reserved == True
    )
    
    if cutoff_date:
        total_query = total_query.filter(FactOrder.created_at >= cutoff_date)
        reserved_query = reserved_query.filter(FactOrder.created_at >= cutoff_date)
    
    total = total_query.scalar() or 0
    reserved = reserved_query.scalar() or 0
    
    if total == 0:
        return 0.0
    
    return round(reserved / total, 2)


def get_fulfillment_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula tasa de fulfillment completo.
    Fórmula: COUNT(status='paid' AND delivery_completed=TRUE) / COUNT(*)
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None
    
    total_query = db.query(func.count(FactOrder.id))
    fulfilled_query = db.query(func.count(FactOrder.id)).filter(
        FactOrder.status == "paid",
        FactOrder.delivery_completed == True
    )
    
    if cutoff_date:
        total_query = total_query.filter(FactOrder.created_at >= cutoff_date)
        fulfilled_query = fulfilled_query.filter(FactOrder.created_at >= cutoff_date)
    
    total = total_query.scalar() or 0
    fulfilled = fulfilled_query.scalar() or 0
    
    if total == 0:
        return 0.0
    
    return round(fulfilled / total, 2)


def get_sla_compliance(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula cumplimiento SLA.
    SLA = (órdenes con pago exitoso + órdenes entregadas) / (total * 2)
    O interpretado como: (entregas + pagos exitosos) / 2 / 100%
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    """
    delivery_rate = get_delivery_rate(db, days)
    payment_success_rate = get_payment_success_rate(db, days)
    
    sla = (delivery_rate + payment_success_rate) / 2
    return round(sla, 2)


# ================================================================
# FUNCIONES DE AGREGACIÓN POR DIMENSIÓN
# ================================================================

def get_orders_by_channel(db: Session, days: Optional[int] = None) -> List[Tuple[str, int, float]]:
    """
    Obtiene distribución de órdenes por canal de venta.
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    
    Returns:
        List de tuples: [(channel, count, revenue), ...]
    """
    query = db.query(
        FactOrder.sales_channel,
        func.count(FactOrder.id).label("count"),
        func.sum(FactOrder.total_amount).label("revenue")
    )
    
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactOrder.created_at >= cutoff_date)
    
    results = query.group_by(FactOrder.sales_channel).all()
    
    return [(ch, count or 0, float(rev) if rev else 0.0) for ch, count, rev in results]


def get_orders_by_status(db: Session, days: Optional[int] = None) -> List[Tuple[str, int]]:
    """
    Obtiene distribución de órdenes por estado.
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar (None = sin filtro)
    
    Returns:
        List de tuples: [(status, count), ...]
    """
    query = db.query(
        FactOrder.status,
        func.count(FactOrder.id).label("count")
    )
    
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactOrder.created_at >= cutoff_date)
    
    results = query.group_by(FactOrder.status).all()
    
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
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
    
    delivered_case = func.sum(
        func.cast(FactOrder.delivery_completed == True, Integer)
    ).label("delivered_count")
    failed_case = func.sum(
        func.cast(FactOrder.status == "payment_failed", Integer)
    ).label("failed_count")

    results = db.query(
        cast(FactOrder.created_at, Date).label("date"),
        func.count(FactOrder.id).label("order_count"),
        delivered_case,
        failed_case,
        func.sum(FactOrder.total_amount).label("revenue")
    ).filter(
        FactOrder.created_at >= cutoff_date
    ).group_by(
        cast(FactOrder.created_at, Date)
    ).order_by(
        cast(FactOrder.created_at, Date).asc()
    ).all()

    timeline = []
    for date, count, delivered, failed, revenue in results:
        avg_value = float(revenue) / count if count and revenue else 0.0
        timeline.append({
            "date": date.isoformat(),
            "order_count": count or 0,
            "delivered_count": int(delivered or 0),
            "failed_count": int(failed or 0),
            "revenue": round(float(revenue) if revenue else 0.0, 2),
            "avg_order_value": round(avg_value, 2)
        })

    return timeline


# ================================================================
# FUNCIONES DE RESPUESTA CONSOLIDADA
# ================================================================

def get_all_kpis(db: Session, days: Optional[int] = None) -> Dict:
    """
    Calcula todos los KPIs consolidados en una sola query usando
    PostgreSQL FILTER (WHERE ...) en las funciones de agregación.
    """
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None

    q = db.query(
        func.count(FactOrder.id).label("total"),
        func.count(FactOrder.id).filter(FactOrder.delivery_completed == True).label("delivered"),
        func.count(FactOrder.id).filter(FactOrder.status == "paid").label("paid"),
        func.count(FactOrder.id).filter(FactOrder.status == "payment_failed").label("failed"),
        func.count(FactOrder.id).filter(
            FactOrder.status.in_(["paid", "payment_failed"])
        ).label("attempted"),
        func.count(FactOrder.id).filter(FactOrder.stock_reserved == True).label("reserved"),
        func.count(FactOrder.id).filter(
            FactOrder.status == "paid", FactOrder.delivery_completed == True
        ).label("fulfilled"),
        func.avg(FactOrder.processing_time_seconds).filter(
            FactOrder.delivery_completed == True,
            FactOrder.processing_time_seconds.isnot(None),
            FactOrder.processing_time_seconds > 0,
        ).label("avg_processing_secs"),
        func.coalesce(
            func.sum(FactOrder.total_amount).filter(FactOrder.payment_success == True), 0
        ).label("revenue"),
    )

    if cutoff_date:
        q = q.filter(FactOrder.created_at >= cutoff_date)

    row = q.one()

    total = row.total or 0
    attempted = row.attempted or 0
    revenue = float(row.revenue or 0)
    avg_secs = float(row.avg_processing_secs or 0)

    delivery_rate = round(row.delivered / total, 2) if total else 0.0
    payment_success_rate = round(row.paid / attempted, 2) if attempted else 0.0

    return {
        "total_orders": total,
        "delivery_rate": delivery_rate,
        "payment_failure_rate": round(row.failed / attempted, 2) if attempted else 0.0,
        "payment_success_rate": payment_success_rate,
        "avg_processing_time_hours": round(avg_secs / 3600, 2),
        "revenue_total": round(revenue, 2),
        "average_order_value": round(revenue / total, 2) if total else 0.0,
        "sla_compliance": round((delivery_rate + payment_success_rate) / 2, 2),
        "stock_reservation_rate": round(row.reserved / total, 2) if total else 0.0,
        "fulfillment_rate": round(row.fulfilled / total, 2) if total else 0.0,
    }
