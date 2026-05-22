from typing import List, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, case, literal_column

from app.pagos.models.fact_pagos import FactPagos
from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion
from app.pagos.models.dim_error_codes import DimErrorCode


def _module_case():
    """Return a SQLAlchemy CASE expression to derive module origin (orders/subscriptions)."""
    return case(
        (
            (FactPagos.order_id != None, literal_column("'orders'")),
            (FactPagos.subscription_id != None, literal_column("'subscriptions'")),
        ),
        else_=literal_column("'unknown'"),
    )


def get_conversion_rate(db: Session, start: datetime, end: datetime) -> float:
    """Return percentage of approved transactions over total attempts in the period.

    Args:
        db: SQLAlchemy session
        start: inclusive start datetime (UTC)
        end: inclusive end datetime (UTC)

    Returns:
        conversion rate as percentage (0.0 - 100.0). Returns 0.0 if no attempts.
    """
    total_q = db.query(func.count(FactPagos.transaction_id)).filter(
        FactPagos.timestamp_evento >= start, FactPagos.timestamp_evento <= end
    )
    total = total_q.scalar() or 0

    approved_q = (
        db.query(func.count(FactPagos.transaction_id))
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(
            DimEstadosConciliacion.nombre == "Aprobado",
            FactPagos.timestamp_evento >= start,
            FactPagos.timestamp_evento <= end,
        )
    )
    approved = approved_q.scalar() or 0

    if total == 0:
        return 0.0
    return float(approved) / float(total) * 100.0


def get_aov_by_module(db: Session, start: datetime, end: datetime) -> List[Dict[str, Any]]:
    """Return Average Order Value (AOV) grouped by module (`orders` or `subscriptions`).

    Only approved transactions are considered.
    Returns list of dicts: [{'module': 'orders', 'aov': Decimal, 'approved_count': int}, ...]
    """
    module_expr = _module_case().label("module")

    q = (
        db.query(
            module_expr,
            func.count(FactPagos.transaction_id).label("approved_count"),
            func.coalesce(func.sum(FactPagos.monto), 0).label("total_amount"),
        )
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(
            DimEstadosConciliacion.nombre == "Aprobado",
            FactPagos.timestamp_evento >= start,
            FactPagos.timestamp_evento <= end,
        )
        .group_by(module_expr)
    )

    results = []
    for module, approved_count, total_amount in q:
        aov = float(total_amount) / float(approved_count) if approved_count else 0.0
        results.append({"module": module, "aov": aov, "approved_count": int(approved_count)})
    return results


def get_volume_by_period(db: Session, period: str, start: datetime, end: datetime) -> List[Tuple[datetime, float]]:
    """Return total approved transaction volume aggregated by `period`.

    period: one of 'day', 'week', 'month' (maps to date_trunc values)
    Returns list of tuples: (period_start, total_amount)
    """
    if period not in ("day", "week", "month"):
        raise ValueError("period must be one of 'day', 'week', 'month'")

    period_trunc = func.date_trunc(period, FactPagos.timestamp_evento).label("period_start")

    q = (
        db.query(period_trunc, func.coalesce(func.sum(FactPagos.monto), 0).label("total_amount"))
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(
            DimEstadosConciliacion.nombre == "Aprobado",
            FactPagos.timestamp_evento >= start,
            FactPagos.timestamp_evento <= end,
        )
        .group_by(period_trunc)
        .order_by(period_trunc)
    )

    return [(row.period_start, float(row.total_amount)) for row in q]


def get_rejection_rate_and_top_reasons(db: Session, start: datetime, end: datetime, top_n: int = 10) -> Dict[str, Any]:
    """Return rejection rate and top N error codes for failed transactions.

    Rejection defined as transactions whose estado_conciliacion != 'Aprobado'.
    Returns: { 'rejection_rate': float_percentage, 'total': int, 'failed': int, 'top_reasons': [(codigo_error, count), ...] }
    """
    total_q = db.query(func.count(FactPagos.transaction_id)).filter(
        FactPagos.timestamp_evento >= start, FactPagos.timestamp_evento <= end
    )
    total = total_q.scalar() or 0

    failed_q = (
        db.query(func.count(FactPagos.transaction_id))
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(
            DimEstadosConciliacion.nombre != "Aprobado",
            FactPagos.timestamp_evento >= start,
            FactPagos.timestamp_evento <= end,
        )
    )
    failed = failed_q.scalar() or 0

    rejection_rate = float(failed) / float(total) * 100.0 if total else 0.0

    # Top reasons by error code — join dim_error_codes to get the code string
    reasons_q = (
        db.query(DimErrorCode.code, func.count(FactPagos.transaction_id).label("cnt"))
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .join(DimErrorCode, FactPagos.error_code_id == DimErrorCode.id)
        .filter(
            DimEstadosConciliacion.nombre != "Aprobado",
            FactPagos.timestamp_evento >= start,
            FactPagos.timestamp_evento <= end,
            FactPagos.error_code_id != None,
        )
        .group_by(DimErrorCode.code)
        .order_by(func.count(FactPagos.transaction_id).desc())
        .limit(top_n)
    )

    top_reasons = [(row.code, int(row.cnt)) for row in reasons_q]

    return {
        "rejection_rate": rejection_rate,
        "total": int(total),
        "failed": int(failed),
        "top_reasons": top_reasons,
    }
