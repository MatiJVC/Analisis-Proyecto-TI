from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.pagos.models.fact_sla_events import FactSlaEvent
from app.models.warehouse.alerts import PriorityAlert

SLA_THRESHOLD = 99.5  # porcentaje mínimo de uptime requerido


def compute_uptime(db: Session, hours: int = 24) -> float:
    """Calcula el uptime real del servicio de pagos en la ventana indicada.

    Suma los segundos de downtime registrados en fact_sla_events para el período
    [now - hours, now] y devuelve el porcentaje de disponibilidad.

    Eventos activos (timestamp_fin IS NULL) se tratan como si aún estuvieran
    en curso hasta el momento actual.

    Returns:
        Uptime como porcentaje entre 0.0 y 100.0.
    """
    now = datetime.now(tz=timezone.utc)
    window_start = now - timedelta(hours=hours)
    window_seconds = hours * 3600.0

    # Suma los segundos de downtime que se solapan con la ventana.
    # LEAST/GREATEST recortan el evento al rango de la ventana.
    # Eventos activos (fin NULL) usan :now como fin provisional.
    downtime_seconds = db.query(
        func.coalesce(
            func.sum(
                func.extract(
                    "epoch",
                    func.least(
                        func.coalesce(FactSlaEvent.timestamp_fin, text(":now")),
                        text(":window_end"),
                    ) - func.greatest(FactSlaEvent.timestamp_inicio, text(":window_start")),
                )
            ),
            0,
        )
    ).filter(
        FactSlaEvent.tipo == "downtime",
        FactSlaEvent.timestamp_inicio < now,
        (FactSlaEvent.timestamp_fin.is_(None)) | (FactSlaEvent.timestamp_fin > window_start),
    ).params(
        now=now,
        window_end=now,
        window_start=window_start,
    ).scalar() or 0.0

    downtime_capped = min(float(downtime_seconds), window_seconds)
    uptime_pct = round((window_seconds - downtime_capped) / window_seconds * 100.0, 4)
    return uptime_pct


def check_sla_and_alert(db: Session, uptime_pct: float, hours: int) -> bool:
    """Escribe una PriorityAlert si el uptime cae bajo SLA_THRESHOLD.

    Evita duplicar alertas: solo inserta una nueva si no existe ya una
    alerta de tipo 'sla_breach' no reconocida en las últimas 2 horas.

    Returns:
        True si se creó una nueva alerta, False en caso contrario.
    """
    if uptime_pct >= SLA_THRESHOLD:
        return False

    two_hours_ago = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    existing = db.query(PriorityAlert).filter(
        PriorityAlert.alert_type == "sla_breach",
        PriorityAlert.acknowledged == False,
        PriorityAlert.created_at >= two_hours_ago,
    ).first()

    if existing:
        return False

    alert = PriorityAlert(
        alert_type="sla_breach",
        severity="critical",
        message=(
            f"SLA de pagos por debajo del umbral: uptime={uptime_pct:.2f}% "
            f"(mínimo requerido: {SLA_THRESHOLD}%) en las últimas {hours}h."
        ),
        alert_metadata={
            "uptime_pct": uptime_pct,
            "sla_threshold": SLA_THRESHOLD,
            "window_hours": hours,
        },
        acknowledged=False,
    )
    db.add(alert)
    db.flush()
    return True


def get_sla_status(db: Session, hours: int = 24) -> Dict[str, Any]:
    """Devuelve el estado SLA completo: uptime, eventos activos y alertas recientes.

    Returns dict con:
      - uptime_pct: float — disponibilidad real en la ventana
      - sla_ok: bool — True si uptime >= 99.5%
      - sla_threshold: float — umbral configurado (99.5)
      - active_events: list — eventos downtime/degraded aún abiertos
      - recent_alerts: list — alertas de SLA no reconocidas de las últimas 24h
      - alert_created: bool — si esta llamada generó una nueva alerta
    """
    uptime_pct = compute_uptime(db, hours)
    alert_created = check_sla_and_alert(db, uptime_pct, hours)

    # Eventos activos (timestamp_fin IS NULL)
    active_rows = db.query(FactSlaEvent).filter(
        FactSlaEvent.timestamp_fin.is_(None)
    ).order_by(FactSlaEvent.timestamp_inicio.desc()).all()

    active_events = [
        {
            "id": e.id,
            "tipo": e.tipo,
            "timestamp_inicio": e.timestamp_inicio.isoformat(),
            "descripcion": e.descripcion,
        }
        for e in active_rows
    ]

    # Alertas de SLA no reconocidas en las últimas 24h
    since_24h = datetime.now(tz=timezone.utc) - timedelta(hours=24)
    alert_rows = db.query(PriorityAlert).filter(
        PriorityAlert.alert_type == "sla_breach",
        PriorityAlert.acknowledged == False,
        PriorityAlert.created_at >= since_24h,
    ).order_by(PriorityAlert.created_at.desc()).all()

    recent_alerts = [
        {
            "id": a.id,
            "severity": a.severity,
            "message": a.message,
            "created_at": a.created_at.isoformat(),
        }
        for a in alert_rows
    ]

    return {
        "uptime_pct": uptime_pct,
        "sla_ok": uptime_pct >= SLA_THRESHOLD,
        "sla_threshold": SLA_THRESHOLD,
        "active_events": active_events,
        "recent_alerts": recent_alerts,
        "alert_created": alert_created,
    }
