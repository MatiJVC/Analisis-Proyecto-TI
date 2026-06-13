"""
KPIs para cálculos analíticos del dominio Notificaciones.

Contiene funciones para calcular KPIs desde fact_notifications y raw_events.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Integer, case
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from app.models.warehouse.fact_notifications import FactNotifications
from app.models import RawEvent


# ================================================================
# FUNCIONES DE CÁLCULO DE KPIs BÁSICOS
# ================================================================

def get_total_notifications(db: Session, days: Optional[int] = None) -> int:
    """Obtiene el total de notificaciones registradas."""
    query = db.query(func.count(FactNotifications.id_notificacion))
    if days:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactNotifications.created_at >= cutoff)
    return query.scalar() or 0


def get_delivered_notifications(db: Session, days: Optional[int] = None) -> int:
    """Obtiene el total de notificaciones con estado 'entregado'."""
    query = db.query(func.count(FactNotifications.id_notificacion)).filter(
        FactNotifications.estado == "entregado"
    )
    if days:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactNotifications.created_at >= cutoff)
    return query.scalar() or 0


def get_failed_notifications(db: Session, days: Optional[int] = None) -> int:
    """Obtiene el total de notificaciones con estado 'fallido'."""
    query = db.query(func.count(FactNotifications.id_notificacion)).filter(
        FactNotifications.estado == "fallido"
    )
    if days:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactNotifications.created_at >= cutoff)
    return query.scalar() or 0


def get_fallback_notifications(db: Session, days: Optional[int] = None) -> int:
    """Obtiene el total de notificaciones donde se activó fallback."""
    query = db.query(func.count(FactNotifications.id_notificacion)).filter(
        FactNotifications.fallback_activado == True
    )
    if days:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactNotifications.created_at >= cutoff)
    return query.scalar() or 0


def get_failure_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Tasa de fallos: % de notificaciones que no se pudieron entregar.
    Fórmula: COUNT(estado='fallido') / COUNT(*) * 100

    Rango: 0.0 a 100.0
    """
    total  = get_total_notifications(db, days)
    failed = get_failed_notifications(db, days)
    if total == 0:
        return 0.0
    return round(failed / total * 100, 2)


def get_delivery_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Uptime del servicio: % de notificaciones entregadas exitosamente.
    Fórmula: COUNT(estado='entregado') / COUNT(*) * 100

    Rango: 0.0 a 100.0
    """
    total     = get_total_notifications(db, days)
    delivered = get_delivered_notifications(db, days)
    if total == 0:
        return 0.0
    return round(delivered / total * 100, 2)


def get_backpressure_ratio(db: Session, days: Optional[int] = None) -> float:
    """
    Backpressure ratio: % de notificaciones que necesitaron canal alternativo.
    Indica presión/saturación sobre el canal primario.
    Fórmula: COUNT(fallback_activado=TRUE) / COUNT(*) * 100

    Rango: 0.0 a 100.0
    """
    total    = get_total_notifications(db, days)
    fallback = get_fallback_notifications(db, days)
    if total == 0:
        return 0.0
    return round(fallback / total * 100, 2)


def get_avg_attempts(db: Session, days: Optional[int] = None) -> float:
    """Promedio de intentos por notificación."""
    query = db.query(func.avg(FactNotifications.intentos))
    if days:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactNotifications.created_at >= cutoff)
    result = query.scalar()
    return round(float(result), 2) if result else 0.0


# ================================================================
# KPI CONSOLIDADO
# ================================================================

def get_notifications_kpis(db: Session, days: Optional[int] = None) -> Dict:
    """
    Retorna todos los KPIs de notificaciones consolidados.

    KPIs globales (sin filtro de días):
    - total_notifications, delivered_notifications, failed_notifications, fallback_notifications

    KPIs con filtro de días (usan parámetro days):
    - failure_rate, delivery_rate, backpressure_ratio, avg_attempts
    """
    # Totales globales (sin filtro — estado actual del sistema)
    total_notifications    = get_total_notifications(db)
    delivered_notifications = get_delivered_notifications(db)
    failed_notifications   = get_failed_notifications(db)
    fallback_notifications = get_fallback_notifications(db)

    # KPIs con filtro de días
    failure_rate       = get_failure_rate(db, days)
    delivery_rate      = get_delivery_rate(db, days)
    backpressure_ratio = get_backpressure_ratio(db, days)
    avg_attempts       = get_avg_attempts(db, days)

    return {
        "total_notifications":     total_notifications,
        "delivered_notifications": delivered_notifications,
        "failed_notifications":    failed_notifications,
        "fallback_notifications":  fallback_notifications,
        "failure_rate":            failure_rate,
        "delivery_rate":           delivery_rate,
        "backpressure_ratio":      backpressure_ratio,
        "avg_attempts":            avg_attempts,
    }


# ================================================================
# FUNCIONES DE DETALLE Y TIMELINE
# ================================================================

def get_notifications_by_channel(db: Session, days: Optional[int] = None) -> List[Dict]:
    query = db.query(
        FactNotifications.canal_usado.label("canal"),
        func.count(FactNotifications.id_notificacion).label("total"),
        func.sum(
            case(
                (
                    (FactNotifications.estado == "entregado") &
                    (FactNotifications.canal_usado == FactNotifications.canal_original),
                    1
                ),
                else_=0
            )
        ).label("delivered_original"),
        func.sum(
            case(
                (
                    (FactNotifications.estado == "entregado") &
                    (FactNotifications.canal_usado != FactNotifications.canal_original),
                    1
                ),
                else_=0
            )
        ).label("delivered_fallback"),
        func.sum(case((FactNotifications.estado == "fallido", 1), else_=0)).label("failed"),
        func.sum(case((FactNotifications.fallback_activado == True, 1), else_=0)).label("fallbacks"),
        func.avg(FactNotifications.intentos).label("avg_attempts"),
    ).filter(FactNotifications.canal_usado.isnot(None))

    if days:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactNotifications.created_at >= cutoff)

    rows = query.group_by(FactNotifications.canal_usado).all()

    result = [
        {
            "canal": canal,
            "total": total,
            "delivered_original": delivered_original or 0,
            "delivered_fallback": delivered_fallback or 0,
            "failed": failed or 0,
            "fallbacks": fallbacks or 0,
            "avg_attempts": round(float(avg_attempts), 2) if avg_attempts else 0.0,
            "delivery_rate": round(((delivered_original or 0) + (delivered_fallback or 0)) / total * 100, 2) if total else 0.0,
            "failure_rate": round((failed or 0) / total * 100, 2) if total else 0.0,
        }
        for canal, total, delivered_original, delivered_fallback, failed, fallbacks, avg_attempts in rows
    ]

    result.sort(key=lambda x: x["total"], reverse=True)
    return result


def get_notifications_by_status(db: Session, days: Optional[int] = None) -> List[Dict]:
    """Distribución de notificaciones por estado (enviado, entregado, fallido)."""
    query = db.query(
        FactNotifications.estado,
        func.count(FactNotifications.id_notificacion).label("count"),
    )

    if days:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactNotifications.created_at >= cutoff)

    rows  = query.group_by(FactNotifications.estado).all()
    total = sum(count for _, count in rows)

    return [
        {
            "estado":     estado,
            "count":      count,
            "percentage": round(count / total * 100, 2) if total else 0.0,
        }
        for estado, count in rows
    ]


def get_notifications_list(db: Session, limit: int = 50) -> List[Dict]:
    """Notificaciones recientes desde el warehouse, ordenadas por última actualización."""
    rows = (
        db.query(FactNotifications)
        .order_by(FactNotifications.updated_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id_notificacion":      row.id_notificacion,
            "canal_usado":          row.canal_usado,
            "estado":               row.estado,
            "intentos":             row.intentos,
            "fallback_activado":    row.fallback_activado,
            "destinatario_email":   row.destinatario_email,
            "destinatario_telefono": row.destinatario_telefono,
            "fecha_entrega":        row.fecha_entrega,
            "created_at":           row.created_at,
            "updated_at":           row.updated_at,
        }
        for row in rows
    ]


def get_notifications_timeline(db: Session, days: int = 30) -> List[Dict]:
    """Timeline diario: total, entregadas, fallidas y fallbacks por día."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

    rows = (
        db.query(
            cast(FactNotifications.created_at, Date).label("date"),
            func.count(FactNotifications.id_notificacion).label("total"),
            func.sum(case((FactNotifications.estado == "entregado", 1), else_=0)).label("delivered"),
            func.sum(case((FactNotifications.estado == "fallido",   1), else_=0)).label("failed"),
            func.sum(case((FactNotifications.fallback_activado == True, 1), else_=0)).label("fallbacks"),
        )
        .filter(FactNotifications.created_at >= cutoff)
        .group_by(cast(FactNotifications.created_at, Date))
        .order_by(cast(FactNotifications.created_at, Date).asc())
        .all()
    )

    return [
        {
            "date":      str(date),
            "total":     total,
            "delivered": delivered or 0,
            "failed":    failed or 0,
            "fallbacks": fallbacks or 0,
        }
        for date, total, delivered, failed, fallbacks in rows
    ]