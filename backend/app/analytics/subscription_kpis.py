from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from app.models import FactSubscription


def _get_total_subscriptions(db: Session) -> int:
    return db.query(func.count(FactSubscription.id)).scalar() or 0


def _round_percentage(value: float) -> float:
    return round(value, 2)


def get_renewal_rate(db: Session) -> float:
    total = _get_total_subscriptions(db)
    
    if total == 0:
        return 0.0
    
    renewed_count = (
        db.query(func.count(FactSubscription.id))
        .filter(FactSubscription.renewed == True)
        .scalar() or 0
    )
    
    rate = renewed_count / total
    return _round_percentage(rate)


def get_error_rate(db: Session) -> float:
    total = _get_total_subscriptions(db)
    
    if total == 0:
        return 0.0
    
    error_count = (
        db.query(func.count(FactSubscription.id))
        .filter(FactSubscription.billing_success == False)
        .scalar() or 0
    )
    
    rate = error_count / total
    return _round_percentage(rate)


def get_auto_service_rate(db: Session) -> float:
    total = _get_total_subscriptions(db)
    
    if total == 0:
        return 0.0
    
    auto_service_count = (
        db.query(func.count(FactSubscription.id))
        .filter(FactSubscription.auto_service == True)
        .scalar() or 0
    )
    
    rate = auto_service_count / total
    return _round_percentage(rate)


def get_subscription_stats(db: Session) -> dict:
    total = _get_total_subscriptions(db)
    
    active = (
        db.query(func.count(FactSubscription.id))
        .filter(FactSubscription.status == "active")
        .scalar() or 0
    )
    
    renewed = (
        db.query(func.count(FactSubscription.id))
        .filter(FactSubscription.renewed == True)
        .scalar() or 0
    )
    
    billing_success = (
        db.query(func.count(FactSubscription.id))
        .filter(FactSubscription.billing_success == True)
        .scalar() or 0
    )
    
    auto_service = (
        db.query(func.count(FactSubscription.id))
        .filter(FactSubscription.auto_service == True)
        .scalar() or 0
    )
    
    return {
        "total": total,
        "active": active,
        "renewed": renewed,
        "with_billing_success": billing_success,
        "with_auto_service": auto_service
    }


def get_subscription_summary(db: Session) -> dict:
    return {
        "renewal_rate": get_renewal_rate(db),
        "error_rate": get_error_rate(db),
        "auto_service_rate": get_auto_service_rate(db),
        "stats": get_subscription_stats(db)
    }
