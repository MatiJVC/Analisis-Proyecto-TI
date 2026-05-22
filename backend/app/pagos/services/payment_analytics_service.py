from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.pagos.models.fact_payments_events import FactPaymentsEvent
from app.pagos.services.sla_service import compute_uptime, check_sla_and_alert

# States that represent a completed failure (not pending, not approved)
_FAILURE_STATES = ("discrepancia_de_monto", "discrepancia_de_transacciones")
_APPROVED = "Aprobado"
_ATTEMPT = "esperando_revisión"


def get_payment_kpis(db: Session, hours: int = 24) -> Dict[str, Any]:
    """Calculate aggregated payment KPIs from fact_payments_events.

    Uses a single-pass aggregate query to minimise DB round-trips.
    The timestamp_evento index ensures the date filter is applied efficiently.

    Args:
        db:    SQLAlchemy session.
        hours: Rolling window in hours (default 24 = last 24 h).

    Returns dict with keys matching PaymentKPIsResponse fields.
    """
    since: datetime = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    # ------------------------------------------------------------------ #
    # Single-pass aggregation over the time window                         #
    # Uses conditional aggregation (FILTER / CASE) to avoid multiple scans #
    # ------------------------------------------------------------------ #
    row = db.query(
        # Total payment attempts (each intento_pago inserts one esperando_revisión row)
        func.count(case((FactPaymentsEvent.status == _ATTEMPT, 1))).label("total_transactions"),

        # Final failure events (discrepancia_* rows)
        func.count(case(
            (FactPaymentsEvent.status.in_(_FAILURE_STATES), 1)
        )).label("failed_payments"),

        # Revenue = sum of amount for Aprobado rows
        func.coalesce(
            func.sum(case((FactPaymentsEvent.status == _APPROVED, FactPaymentsEvent.amount))),
            0,
        ).label("revenue"),

        # Approved count for AOV denominator
        func.count(case((FactPaymentsEvent.status == _APPROVED, 1))).label("approved_count"),
    ).filter(
        FactPaymentsEvent.timestamp_evento >= since
    ).one()

    total_transactions: int = int(row.total_transactions or 0)
    failed_payments: int = int(row.failed_payments or 0)
    revenue: float = float(row.revenue or 0)
    approved_count: int = int(row.approved_count or 0)

    # Derived metrics
    failure_rate: float = round((failed_payments / total_transactions * 100.0) if total_transactions else 0.0, 4)
    avg_transaction_value: float = round(revenue / approved_count if approved_count else 0.0, 2)

    # Uptime real calculado desde fact_sla_events.
    # Si cae bajo el umbral SLA (99.5%) se escribe una PriorityAlert.
    uptime: float = compute_uptime(db, hours)
    check_sla_and_alert(db, uptime, hours)

    return {
        "totalTransactions": total_transactions,
        "failedPayments": failed_payments,
        "failureRate": failure_rate,
        "revenue": round(revenue, 2),
        "avgTransactionValue": avg_transaction_value,
        "uptime": uptime,
    }


def get_payment_timeline(db: Session, hours: int = 24) -> List[Dict[str, Any]]:
    """Return per-hour transaction counts for the last `hours` hours.

    Design decisions
    ----------------
    * Only FINAL-state rows are counted (Aprobado / discrepancia_*).
      The esperando_revisión rows are excluded to avoid double-counting
      attempts that haven't been confirmed yet.
    * The 24-hour grid is generated in Python so every slot is always
      present — hours with no activity return successful=0, failed=0,
      amount=0.0 instead of being absent or null.
    * A single GROUP-BY query hits the timestamp_evento index once;
      Python handles the gap-filling.

    Returns list of dicts ordered chronologically, newest last.
    """
    # Truncate current time to the start of the current hour (UTC)
    now_hour: datetime = datetime.now(tz=timezone.utc).replace(
        minute=0, second=0, microsecond=0
    )
    # Window starts at the beginning of (hours-1) hours ago so we include
    # the current incomplete hour as well as the previous (hours-1) full hours
    since: datetime = now_hour - timedelta(hours=hours - 1)

    # ------------------------------------------------------------------ #
    # Single GROUP-BY query — uses the timestamp_evento index             #
    # ------------------------------------------------------------------ #
    rows = (
        db.query(
            func.date_trunc("hour", FactPaymentsEvent.timestamp_evento).label("hour"),
            func.count(
                case((FactPaymentsEvent.status == _APPROVED, 1))
            ).label("successful"),
            func.count(
                case((FactPaymentsEvent.status.in_(_FAILURE_STATES), 1))
            ).label("failed"),
            func.coalesce(
                func.sum(
                    case((FactPaymentsEvent.status == _APPROVED, FactPaymentsEvent.amount))
                ),
                0,
            ).label("amount"),
        )
        .filter(
            FactPaymentsEvent.timestamp_evento >= since,
            # Exclude pending rows — only final states count
            FactPaymentsEvent.status != _ATTEMPT,
        )
        .group_by(func.date_trunc("hour", FactPaymentsEvent.timestamp_evento))
        .order_by(func.date_trunc("hour", FactPaymentsEvent.timestamp_evento))
        .all()
    )

    # ------------------------------------------------------------------ #
    # Build a lookup: truncated-hour → aggregated values                  #
    # ------------------------------------------------------------------ #
    db_by_hour: Dict[datetime, Dict] = {}
    for row in rows:
        # date_trunc returns timezone-aware datetime for timestamptz columns
        hour_key: datetime = row.hour
        # Normalise to UTC-aware in case the driver strips tz info
        if hour_key.tzinfo is None:
            hour_key = hour_key.replace(tzinfo=timezone.utc)
        db_by_hour[hour_key] = {
            "successful": int(row.successful),
            "failed": int(row.failed),
            "amount": float(row.amount),
        }

    # ------------------------------------------------------------------ #
    # Generate full 24-slot grid and merge — gaps → zeros, never null    #
    # ------------------------------------------------------------------ #
    timeline: List[Dict[str, Any]] = []
    for i in range(hours):
        slot: datetime = since + timedelta(hours=i)
        values = db_by_hour.get(slot, {"successful": 0, "failed": 0, "amount": 0.0})
        timeline.append({
            "date": slot.strftime("%H:%M"),
            "successful": values["successful"],
            "failed": values["failed"],
            "amount": round(values["amount"], 2),
        })

    return timeline
