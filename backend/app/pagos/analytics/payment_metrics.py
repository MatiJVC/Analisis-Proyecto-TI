from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone

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


def get_failure_reasons(db: Session, hours: int = 24, top_n: int = 10) -> Dict[str, Any]:
    """Razones de fallo con descripción legible para el dashboard de pagos.

    Usa una ventana rodante de `hours` horas hacia atrás desde ahora.
    Devuelve: { rejection_rate, total, failed, reasons: [{reason, count, percentage}] }
    """
    _RESOLVED = ("Aprobado", "discrepancia_de_monto", "discrepancia_de_transacciones", "Rechazado")
    _FAILURES  = ("discrepancia_de_monto", "discrepancia_de_transacciones", "Rechazado")

    start = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    # Token único con estado más reciente — excluye esperando_revisión del conteo
    latest = (
        db.query(FactPagos.token_transaccion, DimEstadosConciliacion.nombre.label("estado"), FactPagos.error_code_id)
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(FactPagos.timestamp_evento >= start)
        .distinct(FactPagos.token_transaccion)
        .order_by(FactPagos.token_transaccion, FactPagos.timestamp_evento.desc())
        .subquery()
    )

    total  = db.query(func.count()).select_from(latest).filter(latest.c.estado.in_(_RESOLVED)).scalar() or 0
    failed = db.query(func.count()).select_from(latest).filter(latest.c.estado.in_(_FAILURES)).scalar() or 0

    rejection_rate = round(float(failed) / float(total) * 100.0, 2) if total else 0.0

    reasons_q = (
        db.query(
            DimErrorCode.descripcion.label("reason"),
            DimErrorCode.categoria.label("categoria"),
            func.count().label("cnt"),
        )
        .select_from(latest)
        .join(DimErrorCode, DimErrorCode.id == latest.c.error_code_id)
        .filter(
            latest.c.estado.in_(_FAILURES),
            latest.c.error_code_id.isnot(None),
        )
        .group_by(DimErrorCode.descripcion, DimErrorCode.categoria)
        .order_by(func.count().desc())
        .limit(top_n)
    )

    reasons = [
        {
            "reason":     row.reason,
            "categoria":  row.categoria,
            "count":      int(row.cnt),
            "percentage": round(float(row.cnt) / float(failed) * 100.0, 1) if failed else 0.0,
        }
        for row in reasons_q
    ]

    return {
        "rejection_rate": rejection_rate,
        "total":          int(total),
        "failed":         int(failed),
        "reasons":        reasons,
    }


_METHOD_LABELS: Dict[str, str] = {
    "tarjeta_credito":   "Tarjeta de Crédito",
    "tarjeta_debito":    "Tarjeta de Débito",
    "transferencia":     "Transferencia",
    "billetera_digital": "Billetera Digital",
}


def get_payment_methods(db: Session, hours: int = 24) -> Dict[str, Any]:
    """Distribución de transacciones aprobadas por método de pago.

    Ventana rodante de `hours` horas. Solo cuenta transacciones Aprobado con
    payment_method no nulo. Devuelve methods (con name, value%, count) y total.
    """
    start = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    rows = (
        db.query(
            FactPagos.payment_method.label("method"),
            func.count(FactPagos.transaction_id).label("cnt"),
        )
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(
            DimEstadosConciliacion.nombre == "Aprobado",
            FactPagos.timestamp_evento >= start,
            FactPagos.payment_method.isnot(None),
        )
        .group_by(FactPagos.payment_method)
        .order_by(func.count(FactPagos.transaction_id).desc())
        .all()
    )

    total = sum(int(r.cnt) for r in rows)

    methods = [
        {
            "name":  _METHOD_LABELS.get(r.method, r.method),
            "count": int(r.cnt),
            "value": round(float(r.cnt) / float(total) * 100.0, 1) if total else 0.0,
        }
        for r in rows
    ]

    return {"methods": methods, "total": total}


def get_conciliation_summary(db: Session, hours: int = 24) -> Dict[str, Any]:
    """Distribución de transacciones por estado de conciliación.

    Ventana rodante de `hours` horas. Devuelve statuses, total y approval_rate.
    """
    start = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    rows = (
        db.query(
            DimEstadosConciliacion.nombre.label("status"),
            func.count(FactPagos.transaction_id).label("cnt"),
        )
        .join(FactPagos, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(FactPagos.timestamp_evento >= start)
        .group_by(DimEstadosConciliacion.nombre)
        .order_by(func.count(FactPagos.transaction_id).desc())
        .all()
    )

    total = sum(int(r.cnt) for r in rows)
    approved_count = next((int(r.cnt) for r in rows if r.status == "Aprobado"), 0)
    approval_rate  = round(float(approved_count) / float(total) * 100.0, 2) if total else 0.0

    statuses = [
        {
            "status":     r.status,
            "count":      int(r.cnt),
            "percentage": round(float(r.cnt) / float(total) * 100.0, 1) if total else 0.0,
        }
        for r in rows
    ]

    return {
        "statuses":     statuses,
        "total":        total,
        "approval_rate": approval_rate,
    }
