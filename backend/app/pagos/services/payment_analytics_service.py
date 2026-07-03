from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.pagos.models.fact_payments_events import FactPaymentsEvent
from app.pagos.services.sla_service import compute_uptime, check_sla_and_alert

_FAILURE_STATES = ("discrepancia_de_monto", "discrepancia_de_transacciones")
_APPROVED = "Aprobado"
_ATTEMPT = "esperando_revisión"


def get_payment_kpis(db: Session, hours: int = 24) -> Dict[str, Any]:
    since: datetime = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    _RESOLVED = (_APPROVED, *_FAILURE_STATES)

    # DISTINCT ON token_transaccion: agrupa por token de pago (consistente entre
    # intento_pago y pago_exitoso del mismo cobro), toma el estado más reciente.
    latest = (
        db.query(
            FactPaymentsEvent.token_transaccion,
            FactPaymentsEvent.status,
            FactPaymentsEvent.amount,
        )
        .filter(FactPaymentsEvent.timestamp_evento >= since)
        .distinct(FactPaymentsEvent.token_transaccion)
        .order_by(
            FactPaymentsEvent.token_transaccion,
            FactPaymentsEvent.timestamp_evento.desc(),
        )
        .subquery()
    )

    row = db.query(
        func.count(case((latest.c.status.in_(_RESOLVED), 1))).label("total_transactions"),
        func.count(case((latest.c.status.in_(_FAILURE_STATES), 1))).label("failed_payments"),
        func.coalesce(func.sum(case((latest.c.status == _APPROVED, latest.c.amount))), 0).label("revenue"),
        func.count(case((latest.c.status == _APPROVED, 1))).label("approved_count"),
    ).select_from(latest).one()

    total_transactions: int = int(row.total_transactions or 0)
    failed_payments: int    = int(row.failed_payments or 0)
    revenue: float          = float(row.revenue or 0)
    approved_count: int     = int(row.approved_count or 0)

    failure_rate: float         = round((failed_payments / total_transactions * 100.0) if total_transactions else 0.0, 4)
    avg_transaction_value: float = round(revenue / approved_count if approved_count else 0.0, 2)

    uptime: float = compute_uptime(db, hours)
    check_sla_and_alert(db, uptime, hours)

    return {
        "totalTransactions":    total_transactions,
        "failedPayments":       failed_payments,
        "failureRate":          failure_rate,
        "revenue":              round(revenue, 2),
        "avgTransactionValue":  avg_transaction_value,
        "uptime":               uptime,
    }


def get_payment_timeline(db: Session, hours: int = 24) -> List[Dict[str, Any]]:
    # Redondear al bloque de 30 min actual
    now = datetime.now(tz=timezone.utc)
    half = 0 if now.minute < 30 else 30
    now_slot: datetime = now.replace(minute=half, second=0, microsecond=0)

    slots = hours * 2  # 48 bloques de 30 min para 24h
    since: datetime = now_slot - timedelta(minutes=30 * (slots - 1))

    # Truncar al bloque de 30 min: floor(epoch / 1800) * 1800
    half_trunc = func.to_timestamp(
        func.floor(func.extract("epoch", FactPaymentsEvent.timestamp_evento) / 1800) * 1800
    ).label("slot")

    rows = (
        db.query(
            half_trunc,
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
            FactPaymentsEvent.status != _ATTEMPT,
        )
        .group_by(half_trunc)
        .order_by(half_trunc)
        .all()
    )

    db_by_slot: Dict[datetime, Dict] = {}
    for row in rows:
        slot_key: datetime = row.slot
        if slot_key.tzinfo is None:
            slot_key = slot_key.replace(tzinfo=timezone.utc)
        db_by_slot[slot_key] = {
            "successful": int(row.successful),
            "failed":     int(row.failed),
            "amount":     float(row.amount),
        }

    timeline: List[Dict[str, Any]] = []
    for i in range(slots):
        slot: datetime = since + timedelta(minutes=30 * i)
        values = db_by_slot.get(slot, {"successful": 0, "failed": 0, "amount": 0.0})
        timeline.append({
            "date":       slot.strftime("%H:%M"),
            "successful": values["successful"],
            "failed":     values["failed"],
            "amount":     round(values["amount"], 2),
        })

    return timeline