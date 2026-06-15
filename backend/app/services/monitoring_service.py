from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.pagos.models.fact_pagos import FactPagos
from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion
from app.models.warehouse.alerts import PriorityAlert


MAX_FAILURE_RATE_PCT = 0.5  # percent
CRITICAL_NO_CONF_INTERVAL = timedelta(minutes=5)  # critical window without confirmations


def check_payments_uptime(db: Session, window_minutes: int = 15) -> Dict[str, Any]:
    """Check payment processing uptime and insert PriorityAlert rows on anomalies.

    Write-side function — caller must commit the session. Use run_payment_alert_check()
    for standalone periodic background calls (it handles session + commit).

    Each alert type is deduplicated: a new row is only inserted when there is no
    unacknowledged alert of the same type created within the last 2 hours. This
    prevents alert storms during low-traffic periods (e.g. nights / weekends).
    """
    now = datetime.now(tz=timezone.utc)
    start = now - timedelta(minutes=window_minutes)
    two_hours_ago = now - timedelta(hours=2)

    total = db.query(func.count(FactPagos.transaction_id)).filter(
        FactPagos.timestamp_evento >= start, FactPagos.timestamp_evento <= now
    ).scalar() or 0

    approved_id = db.query(DimEstadosConciliacion.id).filter(DimEstadosConciliacion.nombre == "Aprobado").scalar()
    failed = db.query(func.count(FactPagos.transaction_id)).filter(
        FactPagos.timestamp_evento >= start,
        FactPagos.timestamp_evento <= now,
        FactPagos.estado_conciliacion_id != approved_id,
    ).scalar() or 0

    failure_rate = (failed / total * 100.0) if total else 0.0

    alert = None
    if failure_rate > MAX_FAILURE_RATE_PCT:
        existing_fr = db.query(PriorityAlert).filter(
            PriorityAlert.alert_type == "payments.failure_rate",
            PriorityAlert.acknowledged == False,
            PriorityAlert.created_at >= two_hours_ago,
        ).first()
        if not existing_fr:
            message = f"High failure rate in last {window_minutes}m: {failure_rate:.3f}% (threshold {MAX_FAILURE_RATE_PCT}%)"
            alert = PriorityAlert(alert_type="payments.failure_rate", severity="high", message=message, alert_metadata={"failure_rate": failure_rate, "window_minutes": window_minutes})
            db.add(alert)
            db.flush()

    # check for lack of confirmations: look for confirmed (Aprobado) within a critical interval
    recent_confirmed = 0
    if approved_id:
        recent_confirmed = db.query(func.count(FactPagos.transaction_id)).filter(
            FactPagos.timestamp_evento >= (now - CRITICAL_NO_CONF_INTERVAL), FactPagos.estado_conciliacion_id == approved_id
        ).scalar() or 0

    if recent_confirmed == 0:
        existing_nc = db.query(PriorityAlert).filter(
            PriorityAlert.alert_type == "payments.no_confirmations",
            PriorityAlert.acknowledged == False,
            PriorityAlert.created_at >= two_hours_ago,
        ).first()
        if not existing_nc:
            message = f"No confirmations in the last {int(CRITICAL_NO_CONF_INTERVAL.total_seconds()/60)} minutes"
            alert2 = PriorityAlert(alert_type="payments.no_confirmations", severity="critical", message=message, alert_metadata={"since": (now - CRITICAL_NO_CONF_INTERVAL).isoformat()})
            db.add(alert2)
            db.flush()
            alert = alert2 if alert is None else alert

    return {
        "window_start": start.isoformat(),
        "window_end": now.isoformat(),
        "total": int(total),
        "failed": int(failed),
        "failure_rate": float(failure_rate),
        "alert_id": alert.id if alert else None,
    }


def run_payment_alert_check(window_minutes: int = 15) -> None:
    """Opens its own DB session, runs check_payments_uptime, and commits.

    Intended exclusively for periodic background calls (not HTTP request handlers).
    """
    import logging
    from app.db.session import SessionLocal
    _log = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        check_payments_uptime(db, window_minutes)
        db.commit()
    except Exception:
        db.rollback()
        _log.exception("run_payment_alert_check: error al evaluar uptime de pagos")
    finally:
        db.close()
