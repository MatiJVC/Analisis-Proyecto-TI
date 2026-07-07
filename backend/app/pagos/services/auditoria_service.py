from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.pagos.analytics.payment_metrics import get_payment_methods
from app.pagos.models.cierre_diario import CierreDiario
from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion
from app.pagos.models.fact_pagos import FactPagos
from app.pagos.models.fact_payments_events import FactPaymentsEvent
from app.pagos.models.fact_sla_events import FactSlaEvent
from app.pagos.services.closure_service import process_cierre_diario
from app.pagos.services.payment_analytics_service import get_payment_kpis, get_payment_timeline

_ESTADO_MAP: Dict[str, str] = {
    "Aprobado": "completo",
    "esperando_revisión": "en_proceso",
    "discrepancia_de_monto": "fallido",
    "discrepancia_de_transacciones": "fallido",
}

_METHOD_LABELS: Dict[str, str] = {
    "tarjeta_credito": "Tarjeta de Crédito",
    "tarjeta_debito": "Tarjeta de Débito",
    "transferencia": "Transferencia",
    "billetera_digital": "Billetera Digital",
}


def _compute_uptime_window(db: Session, window_start: datetime, window_end: datetime) -> float:
    """Calcula uptime para una ventana de tiempo arbitraria (histórico por fecha)."""
    window_seconds = (window_end - window_start).total_seconds()
    if window_seconds <= 0:
        return 100.0

    downtime_seconds = (
        db.query(
            func.coalesce(
                func.sum(
                    func.extract(
                        "epoch",
                        func.least(
                            func.coalesce(FactSlaEvent.timestamp_fin, text(":window_end")),
                            text(":window_end"),
                        )
                        - func.greatest(FactSlaEvent.timestamp_inicio, text(":window_start")),
                    )
                ),
                0,
            )
        )
        .filter(
            FactSlaEvent.tipo == "downtime",
            FactSlaEvent.timestamp_inicio < window_end,
            (FactSlaEvent.timestamp_fin.is_(None))
            | (FactSlaEvent.timestamp_fin > window_start),
        )
        .params(window_start=window_start, window_end=window_end)
        .scalar()
        or 0.0
    )

    downtime_capped = min(float(downtime_seconds), window_seconds)
    return round((window_seconds - downtime_capped) / window_seconds * 100.0, 4)


def get_dashboard(db: Session) -> Dict[str, Any]:
    """Agrega KPIs, crecimiento diario, timeline y métodos para el dashboard."""
    kpis = get_payment_kpis(db, hours=24)

    now = datetime.now(tz=timezone.utc)
    today_start = now - timedelta(hours=24)
    # Misma ventana de 24h hace exactamente 7 días
    week_ago_end   = today_start - timedelta(days=7)
    week_ago_start = week_ago_end - timedelta(hours=24)

    today_count = (
        db.query(func.count(FactPaymentsEvent.id))
        .filter(FactPaymentsEvent.timestamp_evento >= today_start)
        .scalar()
        or 0
    )
    week_ago_count = (
        db.query(func.count(FactPaymentsEvent.id))
        .filter(
            FactPaymentsEvent.timestamp_evento >= week_ago_start,
            FactPaymentsEvent.timestamp_evento < week_ago_end,
        )
        .scalar()
        or 0
    )

    crecimiento = (
        round((today_count - week_ago_count) / week_ago_count * 100.0, 2)
        if week_ago_count > 0
        else 0.0
    )

    timeline_raw = get_payment_timeline(db, hours=24)
    transacciones_diarias = [
        {"hora": p["date"], "exitosas": p["successful"], "rechazadas": p["failed"]}
        for p in timeline_raw
    ]

    methods_raw = get_payment_methods(db, hours=24)
    volumen_por_metodo = [
        {"metodo": m["name"], "volumenTrans": m["count"]}
        for m in methods_raw["methods"]
    ]

    return {
        "kpiResumen": {
            "volumenTransDiario": kpis["totalTransactions"],
            "crecimientoVolumen": crecimiento,
            "tasaRechazo": kpis["failureRate"],
            "uptimeSLA": kpis["uptime"],
        },
        "transaccionesDiarias": transacciones_diarias,
        "volumenPorMetodo": volumen_por_metodo,
    }


def get_reportes_historicos(db: Session) -> List[Dict[str, Any]]:
    """Devuelve el histórico de cierres diarios ordenado por fecha descendente."""
    rows = (
        db.query(CierreDiario, DimEstadosConciliacion.nombre.label("estado_nombre"))
        .join(DimEstadosConciliacion, CierreDiario.estado_id == DimEstadosConciliacion.id)
        .order_by(CierreDiario.fecha.desc())
        .all()
    )

    return [
        {
            "id": str(cierre.id),
            "fecha": cierre.fecha.isoformat(),
            "tipo": "Cierre Diario",
            "estado": _ESTADO_MAP.get(estado_nombre, "fallido"),
        }
        for cierre, estado_nombre in rows
    ]


def get_detalle_reporte(db: Session, reporte_id: int) -> Dict[str, Any] | None:
    """Devuelve el detalle de un cierre diario por id con KPIs y volumen históricos."""
    cierre = db.query(CierreDiario).filter(CierreDiario.id == reporte_id).one_or_none()
    if cierre is None:
        return None

    fecha: date = cierre.fecha
    start = datetime.combine(fecha, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = datetime.combine(fecha, datetime.max.time()).replace(tzinfo=timezone.utc)

    _RESOLVED = ("Aprobado", "discrepancia_de_monto", "discrepancia_de_transacciones", "Rechazado")
    _FAILURES  = ("discrepancia_de_monto", "discrepancia_de_transacciones", "Rechazado")

    # Pago único por token_transaccion: tomar el estado más reciente del día
    latest = (
        db.query(FactPagos.token_transaccion, DimEstadosConciliacion.nombre.label("estado"))
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(FactPagos.timestamp_evento >= start, FactPagos.timestamp_evento <= end)
        .distinct(FactPagos.token_transaccion)
        .order_by(FactPagos.token_transaccion, FactPagos.timestamp_evento.desc())
        .subquery()
    )

    total = (
        db.query(func.count()).select_from(latest)
        .filter(latest.c.estado.in_(_RESOLVED))
        .scalar() or 0
    )
    failed = (
        db.query(func.count()).select_from(latest)
        .filter(latest.c.estado.in_(_FAILURES))
        .scalar() or 0
    )
    tasa_rechazo = round(float(failed) / float(total) * 100.0, 4) if total else 0.0

    uptime_sla = _compute_uptime_window(db, start, end)

    # Misma fecha hace 7 días para comparación semana a semana
    prev_start = start - timedelta(days=7)
    prev_end   = end   - timedelta(days=7)
    latest_prev = (
        db.query(FactPagos.token_transaccion, DimEstadosConciliacion.nombre.label("estado"))
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(FactPagos.timestamp_evento >= prev_start, FactPagos.timestamp_evento <= prev_end)
        .distinct(FactPagos.token_transaccion)
        .order_by(FactPagos.token_transaccion, FactPagos.timestamp_evento.desc())
        .subquery()
    )
    prev_total = (
        db.query(func.count()).select_from(latest_prev)
        .filter(latest_prev.c.estado.in_(_RESOLVED))
        .scalar() or 0
    )
    crecimiento = (
        round((total - prev_total) / prev_total * 100.0, 2) if prev_total > 0 else 0.0
    )

    method_rows = (
        db.query(
            FactPagos.payment_method.label("method"),
            func.count(FactPagos.transaction_id).label("cnt"),
        )
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(
            DimEstadosConciliacion.nombre == "Aprobado",
            FactPagos.timestamp_evento >= start,
            FactPagos.timestamp_evento <= end,
            FactPagos.payment_method.isnot(None),
        )
        .group_by(FactPagos.payment_method)
        .all()
    )

    volumen_por_metodo = [
        {"metodo": _METHOD_LABELS.get(r.method, r.method), "volumenTrans": int(r.cnt)}
        for r in method_rows
    ]

    return {
        "id_reporte": str(cierre.id),
        "fecha": fecha.isoformat(),
        "kpiResumen": {
            "volumenTransDiario": total,
            "crecimientoVolumen": crecimiento,
            "tasaRechazo": tasa_rechazo,
            "uptimeSLA": uptime_sla,
        },
        "volumenPorMetodo": volumen_por_metodo,
    }


def generar_reporte_hoy(db: Session) -> None:
    """Genera el cierre diario del día actual usando los totales internos aprobados."""
    # date.today() usa la hora LOCAL del servidor; el resto del módulo (FactPagos.timestamp_evento,
    # get_payment_kpis, sla_service, etc.) trabaja siempre en UTC. En husos horarios detrás de UTC
    # (ej. UTC-4), "hoy" local puede ser un día calendario distinto al "hoy" UTC, generando el cierre
    # con una ventana que no incluye los eventos recién ingeridos (bug real: reporte con 0 transacciones
    # pese a haber datos, detectado probando /pagos con eventos inyectados en jul-2026).
    today = datetime.now(tz=timezone.utc).date()
    start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

    row = (
        db.query(
            func.coalesce(func.count(FactPagos.transaction_id), 0).label("cnt"),
            func.coalesce(func.sum(FactPagos.monto), 0).label("total"),
        )
        .join(DimEstadosConciliacion, FactPagos.estado_conciliacion_id == DimEstadosConciliacion.id)
        .filter(
            DimEstadosConciliacion.nombre == "Aprobado",
            FactPagos.timestamp_evento >= start,
            FactPagos.timestamp_evento <= end,
        )
        .one()
    )

    process_cierre_diario(
        db,
        {
            "fecha": today,
            "reported_total": float(row.total or 0),
            "reported_count": int(row.cnt or 0),
        },
    )
    db.commit()
