from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.pagos.models.fact_pagos import FactPagos
from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion
from app.models.warehouse.alerts import PriorityAlert


SLA_THRESHOLD = 0.5  # percent
CRITICAL_NO_CONF_INTERVAL = timedelta(minutes=5)  # critical window without confirmations


def check_payments_uptime(db: Session, window_minutes: int = 15) -> Dict[str, Any]:
    """Check payment processing uptime over a sliding window and create alerts if thresholds exceeded.

    - window_minutes: size of the moving window in minutes.
    - Inserts a PriorityAlert row when anomaly detected.
    Returns a dict with metrics and alert info.
    """
    now = datetime.now(tz=timezone.utc)
    start = now - timedelta(minutes=window_minutes)

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
    if failure_rate > SLA_THRESHOLD:
        message = f"High failure rate in last {window_minutes}m: {failure_rate:.3f}% (threshold {SLA_THRESHOLD}%)"
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
