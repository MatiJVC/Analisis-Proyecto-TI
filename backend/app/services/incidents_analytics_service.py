"""
Consultas analíticas sobre fact_incidents (warehouse de incidentes).
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.warehouse.fact_incidents import FactIncident


def _format_relative_time(dt: datetime) -> str:
    now = datetime.utcnow()
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} hours ago"
    return f"{seconds // 86400} days ago"


def get_incidents_kpis(db: Session) -> Dict[str, Any]:
    total = db.query(func.count(FactIncident.id)).scalar() or 0

    active_incidents = (
        db.query(func.count(FactIncident.id))
        .filter(FactIncident.status != "resolved")
        .scalar()
        or 0
    )

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = (
        db.query(func.count(FactIncident.id))
        .filter(
            and_(
                FactIncident.status == "resolved",
                FactIncident.resolved_at >= today_start,
            )
        )
        .scalar()
        or 0
    )

    avg_resolution: Optional[float] = (
        db.query(func.avg(FactIncident.resolution_time_hours))
        .filter(
            and_(
                FactIncident.resolution_time_hours.isnot(None),
                FactIncident.status == "resolved",
            )
        )
        .scalar()
    )
    avg_resolution_time = round(float(avg_resolution), 1) if avg_resolution is not None else 0.0

    resolved_total = (
        db.query(func.count(FactIncident.id))
        .filter(FactIncident.status == "resolved")
        .scalar()
        or 0
    )
    sla_met_count = (
        db.query(func.count(FactIncident.id))
        .filter(
            and_(
                FactIncident.status == "resolved",
                FactIncident.sla_met == True,
            )
        )
        .scalar()
        or 0
    )
    sla_compliance = (
        round(sla_met_count / resolved_total * 100, 1) if resolved_total > 0 else 0.0
    )

    critical_count = (
        db.query(func.count(FactIncident.id))
        .filter(
            and_(
                FactIncident.severity == "critical",
                FactIncident.status != "resolved",
            )
        )
        .scalar()
        or 0
    )

    _ = total
    return {
        "activeIncidents": int(active_incidents),
        "resolvedToday": int(resolved_today),
        "avgResolutionTime": avg_resolution_time,
        "slaCompliance": sla_compliance,
        "criticalCount": int(critical_count),
    }


def get_incidents_timeline(db: Session, days: int = 14) -> List[Dict[str, Any]]:
    if days < 1:
        days = 14
    if days > 90:
        days = 90

    end = date.today()
    start = end - timedelta(days=days - 1)
    points: List[Dict[str, Any]] = []

    d = start
    while d <= end:
        day_start = datetime.combine(d, datetime.min.time())
        day_end = datetime.combine(d, datetime.max.time())

        opened = (
            db.query(func.count(FactIncident.id))
            .filter(
                and_(
                    FactIncident.opened_at >= day_start,
                    FactIncident.opened_at <= day_end,
                )
            )
            .scalar()
            or 0
        )
        resolved = (
            db.query(func.count(FactIncident.id))
            .filter(
                and_(
                    FactIncident.resolved_at.isnot(None),
                    FactIncident.resolved_at >= day_start,
                    FactIncident.resolved_at <= day_end,
                )
            )
            .scalar()
            or 0
        )
        critical = (
            db.query(func.count(FactIncident.id))
            .filter(
                and_(
                    FactIncident.severity == "critical",
                    FactIncident.opened_at >= day_start,
                    FactIncident.opened_at <= day_end,
                )
            )
            .scalar()
            or 0
        )
        points.append(
            {
                "date": d.isoformat(),
                "opened": int(opened),
                "resolved": int(resolved),
                "critical": int(critical),
            }
        )
        d += timedelta(days=1)

    return points


def get_incidents_list(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    rows = (
        db.query(FactIncident)
        .order_by(FactIncident.updated_at.desc())
        .limit(limit)
        .all()
    )

    result: List[Dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "id": row.incident_id,
                "title": row.title,
                "severity": row.severity,
                "status": row.status,
                "assignee": row.assignee or "Unassigned",
                "createdAt": _format_relative_time(row.opened_at),
                "updatedAt": _format_relative_time(row.updated_at or row.opened_at),
            }
        )
    return result
