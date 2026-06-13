"""
Servicio analítico transversal: agrega KPIs y eventos recientes de todos los
warehouses (orders, incidents, salud, subscriptions) para alimentar la Overview.

No depende de dominios que aún no tengan warehouse (notifications, iot,
payments, logistics); para esos KPIs reporta 0 o derivados.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import FactIncident, FactOrder, FactSubscription, RawEvent

def _format_relative_time(dt: datetime) -> str:
    delta = datetime.now(tz=timezone.utc) - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} hours ago"
    return f"{seconds // 86400} days ago"


# ================================================================
# Global KPIs (agregados desde warehouses existentes)
# ================================================================


def get_global_kpis(db: Session) -> Dict[str, Any]:
    total_orders = db.query(func.count(FactOrder.id)).scalar() or 0
    delivered = (
        db.query(func.count(FactOrder.id))
        .filter(FactOrder.delivery_completed == True)  # noqa: E712
        .scalar()
        or 0
    )
    delivery_rate = round((delivered / total_orders * 100) if total_orders > 0 else 0.0, 2)
    revenue = float(db.query(func.sum(FactOrder.total_amount)).scalar() or 0.0)

    active_subs = (
        db.query(func.count(FactSubscription.id))
        .filter(FactSubscription.status == "active")
        .scalar()
        or 0
    )

    incident_count = (
        db.query(func.count(FactIncident.id))
        .filter(FactIncident.status != "resolved")
        .scalar()
        or 0
    )

    return {
        "totalOrders": total_orders,
        "deliveryRate": delivery_rate,
        "revenue": round(revenue, 2),
        "notificationSuccessRate": 0.0,
        "activeSubscriptions": active_subs,
        "iotAlerts": 0,
        "incidentCount": incident_count,
        "paymentFailureRate": 0.0,
    }


# ================================================================
# Service statuses (derivados de incidentes activos)
# ================================================================


_SERVICE_CATALOG: List[Dict[str, str]] = [
    {"name": "Orders Service", "source": "orders"},
    {"name": "Payments Gateway", "source": "payments"},
    {"name": "Notifications", "source": "notifications"},
    {"name": "IoT Platform", "source": "iot"},
    {"name": "Salud Service", "source": "salud"},
    {"name": "Subscriptions Service", "source": "subscriptions"},
    {"name": "Incidents Engine", "source": "incidents"},
]


def _classify_status(critical_active: int, high_active: int) -> str:
    if critical_active >= 1:
        return "outage"
    if high_active >= 1:
        return "degraded"
    return "operational"


def get_service_statuses(db: Session) -> List[Dict[str, Any]]:
    incidents = (
        db.query(FactIncident)
        .filter(FactIncident.status != "resolved")
        .all()
    )

    by_keyword: Dict[str, List[FactIncident]] = {svc["source"]: [] for svc in _SERVICE_CATALOG}
    for inc in incidents:
        title = (inc.title or "").lower()
        for keyword, bucket in (
            ("payment", "payments"),
            ("email", "notifications"),
            ("sms", "notifications"),
            ("push", "notifications"),
            ("notification", "notifications"),
            ("iot", "iot"),
            ("sensor", "iot"),
            ("order", "orders"),
            ("checkout", "orders"),
            ("stock", "orders"),
            ("subscription", "subscriptions"),
            ("renewal", "subscriptions"),
            ("salud", "salud"),
            ("visita", "salud"),
            ("paciente", "salud"),
        ):
            if keyword in title and bucket in by_keyword:
                by_keyword[bucket].append(inc)
                break
        else:
            by_keyword.setdefault("incidents", []).append(inc)

    result: List[Dict[str, Any]] = []
    for svc in _SERVICE_CATALOG:
        bucket = by_keyword.get(svc["source"], [])
        critical = sum(1 for i in bucket if i.severity == "critical")
        high = sum(1 for i in bucket if i.severity == "high")
        status = _classify_status(critical, high)
        last_incident_dt = max((i.opened_at for i in bucket), default=None)
        uptime = 99.99 if status == "operational" else (99.5 if status == "degraded" else 98.0)
        result.append(
            {
                "name": svc["name"],
                "status": status,
                "uptime": uptime,
                "lastIncident": _format_relative_time(last_incident_dt) if last_incident_dt else None,
            }
        )
    return result


# ================================================================
# Recent activities (desde raw_events, los más recientes)
# ================================================================


def _classify_activity_status(event_type: str) -> str:
    et = event_type.lower()
    if "failed" in et or "fallido" in et or "agotado" in et or "outage" in et:
        return "error"
    if "alert" in et or "delay" in et or "warning" in et or "low" in et:
        return "warning"
    return "success"


def _classify_activity_type(source: str) -> str:
    mapping = {
        "orders": "order",
        "subscriptions": "subscription",
        "incidents": "incident",
        "salud": "salud",
        "notifications": "notification",
        "iot": "iot",
        "payments": "payment",
    }
    return mapping.get(source, source)


def _human_message(event: RawEvent) -> str:
    payload = event.payload or {}
    event_type = event.event_type.replace("_", " ")
    src = event.source

    if src == "orders":
        order_id = payload.get("order_id")
        amount = payload.get("total_amount")
        if order_id and amount:
            return f"Order #{order_id} {event_type} (${amount:,.0f})"
        if order_id:
            return f"Order #{order_id} {event_type}"
        return f"Orders {event_type}"

    if src == "incidents":
        title = payload.get("title")
        if title:
            return f"{title} - {event_type}"
        incident_id = payload.get("incident_id")
        if incident_id:
            return f"{incident_id} {event_type}"
        return f"Incident {event_type}"

    if src == "subscriptions":
        contract = payload.get("contract_id")
        return f"Subscription {contract} {event_type}" if contract else f"Subscriptions {event_type}"

    if src == "salud":
        return f"Salud {event_type}"

    return f"{src.capitalize()} {event_type}"


def get_recent_activities(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    rows = (
        db.query(RawEvent)
        .order_by(RawEvent.ingested_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": f"ACT-{r.id:06d}",
            "type": _classify_activity_type(r.source),
            "message": _human_message(r),
            "timestamp": _format_relative_time(r.ingested_at),
            "status": _classify_activity_status(r.event_type or ""),
        }
        for r in rows
    ]


# ================================================================
# Critical alerts (incidentes activos críticos/altos)
# ================================================================


def get_critical_alerts(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    rows = (
        db.query(FactIncident)
        .filter(
            FactIncident.status != "resolved",
            FactIncident.severity.in_(["critical", "high"]),
        )
        .order_by(FactIncident.opened_at.desc())
        .limit(limit)
        .all()
    )
    alerts: List[Dict[str, Any]] = []
    for inc in rows:
        severity = "critical" if inc.severity == "critical" else "warning"
        alerts.append(
            {
                "id": inc.incident_id,
                "title": inc.title,
                "message": f"Status: {inc.status}. Assigned to {inc.assignee or 'Unassigned'}.",
                "severity": severity,
                "source": "Incidents",
                "timestamp": _format_relative_time(inc.opened_at),
            }
        )
    return alerts
