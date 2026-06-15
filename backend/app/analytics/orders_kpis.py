"""
KPIs para cálculos analíticos del dominio Orders.

Contiene funciones para calcular KPIs desde fact_orders.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, case, Date, Integer
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional

from app.models import FactOrder

# Orders delivered within this window are considered SLA-compliant.
SLA_DELIVERY_HOURS = 48
_SLA_THRESHOLD_SECONDS = SLA_DELIVERY_HOURS * 3600


# ================================================================
# FUNCIONES DE AGREGACIÓN POR DIMENSIÓN
# ================================================================

def get_orders_by_channel(db: Session, days: Optional[int] = None) -> List[Tuple[str, int, float]]:
    """
    Obtiene distribución de órdenes por canal de venta.

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
        func.count(FactOrder.id).filter(
            FactOrder.delivery_completed == True,
            FactOrder.processing_time_seconds.isnot(None),
            FactOrder.processing_time_seconds > 0,
        ).label("sla_delivered"),
        func.count(FactOrder.id).filter(
            FactOrder.delivery_completed == True,
            FactOrder.processing_time_seconds.isnot(None),
            FactOrder.processing_time_seconds > 0,
            FactOrder.processing_time_seconds <= _SLA_THRESHOLD_SECONDS,
        ).label("sla_compliant"),
    )

    if cutoff_date:
        q = q.filter(FactOrder.created_at >= cutoff_date)

    row = q.one()

    total = row.total or 0
    attempted = row.attempted or 0
    revenue = float(row.revenue or 0)
    avg_secs = float(row.avg_processing_secs or 0)
    sla_delivered = row.sla_delivered or 0

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
        "sla_compliance": round(row.sla_compliant / sla_delivered, 2) if sla_delivered else 0.0,
        "stock_reservation_rate": round(row.reserved / total, 2) if total else 0.0,
        "fulfillment_rate": round(row.fulfilled / total, 2) if total else 0.0,
    }
