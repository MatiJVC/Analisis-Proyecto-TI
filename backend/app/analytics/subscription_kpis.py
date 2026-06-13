from sqlalchemy import func, and_, or_, cast, Date, Integer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from app.models import FactSubscription


def _get_total_subscriptions(db: Session, days: Optional[int] = None) -> int:
    query = db.query(func.count(FactSubscription.id))
    
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactSubscription.created_at >= cutoff_date)
    
    return query.scalar() or 0


def _round_percentage(value: float) -> float:
    return round(value, 2)


def get_renewal_rate(db: Session, days: Optional[int] = None) -> float:
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None
    
    total_query = db.query(func.count(FactSubscription.id))
    renewed_query = db.query(func.count(FactSubscription.id)).filter(
        FactSubscription.renewed == True
    )
    
    if cutoff_date:
        # Ambas queries deben filtrar por el mismo criterio de fecha
        total_query = total_query.filter(FactSubscription.created_at >= cutoff_date)
        renewed_query = renewed_query.filter(FactSubscription.created_at >= cutoff_date)
    
    total = total_query.scalar() or 0
    renewed_count = renewed_query.scalar() or 0
    
    if total == 0:
        return 0.0
    
    rate = renewed_count / total
    # Retorna 0-1 (porcentaje decimal), no 0-100
    return _round_percentage(rate)


def get_error_rate(db: Session, days: Optional[int] = None) -> float:
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None
    
    total_query = db.query(func.count(FactSubscription.id))
    error_query = db.query(func.count(FactSubscription.id)).filter(
        FactSubscription.billing_success == False
    )
    
    if cutoff_date:
        total_query = total_query.filter(FactSubscription.created_at >= cutoff_date)
        error_query = error_query.filter(FactSubscription.created_at >= cutoff_date)
    
    total = total_query.scalar() or 0
    error_count = error_query.scalar() or 0
    
    if total == 0:
        return 0.0
    
    rate = error_count / total
    return _round_percentage(rate)


def get_auto_service_rate(db: Session, days: Optional[int] = None) -> float:
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None
    
    total_query = db.query(func.count(FactSubscription.id))
    auto_service_query = db.query(func.count(FactSubscription.id)).filter(
        FactSubscription.auto_service == True
    )
    
    if cutoff_date:
        total_query = total_query.filter(FactSubscription.created_at >= cutoff_date)
        auto_service_query = auto_service_query.filter(FactSubscription.created_at >= cutoff_date)
    
    total = total_query.scalar() or 0
    auto_service_count = auto_service_query.scalar() or 0
    
    if total == 0:
        return 0.0
    
    rate = auto_service_count / total
    return _round_percentage(rate)


def get_subscription_stats(db: Session, days: Optional[int] = None) -> dict:
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days) if days else None
    
    base_query = db.query(FactSubscription.id)
    if cutoff_date:
        base_query = base_query.filter(FactSubscription.created_at >= cutoff_date)
    
    total = base_query.count()
    
    active = (
        base_query.filter(FactSubscription.status == "active")
        .count()
    )
    
    renewed = db.query(func.count(FactSubscription.id)).filter(
        FactSubscription.renewed == True
    )
    if cutoff_date:
        renewed = renewed.filter(FactSubscription.created_at >= cutoff_date)
    renewed = renewed.scalar() or 0
    
    billing_success = db.query(func.count(FactSubscription.id)).filter(
        FactSubscription.billing_success == True
    )
    if cutoff_date:
        billing_success = billing_success.filter(FactSubscription.created_at >= cutoff_date)
    billing_success = billing_success.scalar() or 0
    
    auto_service = base_query.filter(FactSubscription.auto_service == True).count()
    
    # Nuevas suscripciones en el período
    new_subs_query = db.query(func.count(FactSubscription.id))
    if cutoff_date:
        new_subs_query = new_subs_query.filter(FactSubscription.created_at >= cutoff_date)
    new_subscriptions = new_subs_query.scalar() or 0
    
    # Cancelaciones en el período
    cancel_query = db.query(func.count(FactSubscription.id)).filter(
        FactSubscription.end_date.isnot(None)
    )
    if cutoff_date:
        cancel_query = cancel_query.filter(FactSubscription.end_date >= cutoff_date.date())
    cancellations = cancel_query.scalar() or 0
    
    # Churn Rate: Cancelaciones / (Total activo + Nuevas) × 100%
    churn_denominator = active + new_subscriptions if active + new_subscriptions > 0 else 1
    churn_rate = round((cancellations / churn_denominator) * 100, 2)
    
    # Lifetime Value: Tiempo promedio de suscripción en meses (cálculo en Python)
    subs = db.query(FactSubscription.start_date, FactSubscription.end_date).filter(
        (FactSubscription.end_date.isnot(None)) | (FactSubscription.status == "active")
    ).all()
    
    if subs:
        lifetimes = []
        for start, end in subs:
            if start:
                end_date = end if end else datetime.now(tz=timezone.utc).date()
                delta = (end_date - start).days
                lifetimes.append(delta)
        avg_lifetime_days = sum(lifetimes) / len(lifetimes) if lifetimes else 0
        avg_lifetime_months = round(avg_lifetime_days / 30, 2)
    else:
        avg_lifetime_months = 0
    
    return {
        "total": total,
        "active": active,
        "renewed": renewed,
        "with_billing_success": billing_success,
        "with_auto_service": auto_service,
        "new_subscriptions": new_subscriptions,
        "cancellations": cancellations,
        "net_growth": new_subscriptions - cancellations,
        "churn_rate": churn_rate,
        "avg_lifetime_months": avg_lifetime_months
    }


def get_subscription_summary(db: Session, days: Optional[int] = None) -> dict:
    return {
        "renewal_rate": get_renewal_rate(db, days),
        "error_rate": get_error_rate(db, days),
        "auto_service_rate": get_auto_service_rate(db, days),
        "stats": get_subscription_stats(db, days)
    }


def get_subscriptions_by_date(db: Session, days: int = 30) -> List[Dict]:
    """
    Obtiene distribución de suscripciones por fecha (últimos N días).
    Agrupa por:
    - Nuevas suscripciones (created_at)
    - Renovaciones (renewed=True)
    - Cancelaciones (end_date)
    
    Args:
        db: Sesión SQLAlchemy
        days: Cantidad de días atrás a considerar
        
    Returns:
        List de dicts: [{'date': '2026-05-13', 'new_subscriptions': 10, 'renewals': 5, 'cancellations': 2}, ...]
    """
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
    
    # Query para nuevas suscripciones (por created_at)
    new_subs = db.query(
        cast(FactSubscription.created_at, Date).label("date"),
        func.count(FactSubscription.id).label("count")
    ).filter(
        FactSubscription.created_at >= cutoff_date
    ).group_by(
        cast(FactSubscription.created_at, Date)
    ).all()
    
    # Query para renovaciones (renewed=True, por updated_at)
    renewals_query = db.query(
        cast(FactSubscription.updated_at, Date).label("date"),
        func.count(FactSubscription.id).label("count")
    ).filter(
        FactSubscription.renewed == True,
        FactSubscription.updated_at >= cutoff_date
    ).group_by(
        cast(FactSubscription.updated_at, Date)
    ).all()
    
    # Query para cancelaciones (end_date not null)
    cancellations_query = db.query(
        cast(FactSubscription.end_date, Date).label("date"),
        func.count(FactSubscription.id).label("count")
    ).filter(
        FactSubscription.end_date.isnot(None),
        FactSubscription.end_date >= cutoff_date.date()
    ).group_by(
        cast(FactSubscription.end_date, Date)
    ).all()
    
    # Consolidar en un diccionario por fecha
    timeline_dict = {}
    
    for date, count in new_subs:
        if date.isoformat() not in timeline_dict:
            timeline_dict[date.isoformat()] = {
                "date": date.isoformat(),
                "new_subscriptions": 0,
                "renewals": 0,
                "cancellations": 0
            }
        timeline_dict[date.isoformat()]["new_subscriptions"] = count or 0
    
    for date, count in renewals_query:
        if date.isoformat() not in timeline_dict:
            timeline_dict[date.isoformat()] = {
                "date": date.isoformat(),
                "new_subscriptions": 0,
                "renewals": 0,
                "cancellations": 0
            }
        timeline_dict[date.isoformat()]["renewals"] = count or 0
    
    for date, count in cancellations_query:
        if date.isoformat() not in timeline_dict:
            timeline_dict[date.isoformat()] = {
                "date": date.isoformat(),
                "new_subscriptions": 0,
                "renewals": 0,
                "cancellations": 0
            }
        timeline_dict[date.isoformat()]["cancellations"] = count or 0
    
    # Ordenar por fecha descendente
    timeline = sorted(
        timeline_dict.values(),
        key=lambda x: x["date"],
        reverse=True
    )
    
    return timeline


def get_retention_rate(db: Session, period_days: int) -> float:
    """
    Calcula el retention rate para un período específico.
    
    Definición: % de suscripciones que estaban activas hace X días Y siguen activas hoy.
    
    Fórmula: (suscripciones que siguen activas hoy de las que estaban activas hace X días) / (suscripciones activas hace X días) * 100
    
    Args:
        db: Sesión SQLAlchemy
        period_days: Cantidad de días atrás a medir (30, 90, 365)
        
    Returns:
        float: Retention rate como porcentaje (0-100)
    """
    
    now = datetime.now(tz=timezone.utc)
    start_of_period = now - timedelta(days=period_days)
    
    # Una suscripción estaba activa en start_of_period si:
    # - fue creada antes o en esa fecha: created_at <= start_of_period
    # - no fue cancelada antes: end_date IS NULL o end_date > start_of_period
    
    # Suscripciones que ESTABAN activas hace X días
    active_at_period = db.query(func.count(FactSubscription.id)).filter(
        FactSubscription.created_at <= start_of_period,
        or_(
            FactSubscription.end_date.is_(None),
            FactSubscription.end_date > start_of_period
        )
    ).scalar() or 0
    
    if active_at_period == 0:
        return 0.0
    
    # Suscripciones que SIGUEN ACTIVAS hoy de las que estaban activas hace X días
    # Deben cumplir:
    # - estaban activas en start_of_period (mismo filtro anterior)
    # - siguen activas hoy: status == "active" O (end_date IS NULL O end_date > now)
    retained = db.query(func.count(FactSubscription.id)).filter(
        FactSubscription.created_at <= start_of_period,
        or_(
            FactSubscription.end_date.is_(None),
            FactSubscription.end_date > start_of_period
        ),
        FactSubscription.status == "active"
    ).scalar() or 0
    
    retention_rate = (retained / active_at_period) * 100
    return round(retention_rate, 2)


def get_all_retention_rates(db: Session) -> Dict[str, float]:
    """
    Calcula retention rates para los períodos estándar: 30, 90 y 365 días.
    
    Returns:
        dict: {
            "retention_30_days": 92.5,
            "retention_90_days": 87.3,
            "retention_annual": 78.9
        }
    """
    
    return {
        "retention_30_days": get_retention_rate(db, 30),
        "retention_90_days": get_retention_rate(db, 90),
        "retention_annual": get_retention_rate(db, 365)
    }
