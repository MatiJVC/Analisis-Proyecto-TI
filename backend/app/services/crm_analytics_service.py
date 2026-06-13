from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.warehouse.fact_tickets import FactTicket
from app.models.warehouse.dim_clientes_crm import DimClienteCRM
from app.models.warehouse.fact_interacciones import FactInteraccion
from app.models.warehouse.fact_sla_violaciones import FactSlaViolacion


def get_crm_kpis(db: Session) -> Dict[str, Any]:
    today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_customers = db.query(func.count(DimClienteCRM.id)).scalar() or 0

    open_tickets = (
        db.query(func.count(FactTicket.id))
        .filter(FactTicket.estado.in_(["Abierto", "Progreso"]))
        .scalar() or 0
    )

    avg_response_time = (
        db.query(func.avg(FactTicket.resolution_time_hours))
        .filter(FactTicket.resolution_time_hours.isnot(None))
        .scalar()
    )
    avg_response_time = round(float(avg_response_time) * 60, 1) if avg_response_time else 0.0

    avg_csat = (
        db.query(func.avg(FactTicket.csat_score))
        .filter(FactTicket.csat_score.isnot(None))
        .scalar()
    )
    csat_score = round(float(avg_csat), 1) if avg_csat else 0.0

    messages_today = (
        db.query(func.count(FactInteraccion.id))
        .filter(FactInteraccion.ingested_at >= today_start)
        .scalar() or 0
    )

    resolved = db.query(func.count(FactTicket.id)).filter(
        FactTicket.estado == "Cerrado"
    ).scalar() or 0
    total = db.query(func.count(FactTicket.id)).scalar() or 1
    resolution_rate = round((resolved / total) * 100, 1)

    return {
        "totalCustomers": total_customers,
        "openTickets": open_tickets,
        "avgResponseTimeMinutes": avg_response_time,
        "csatScore": csat_score,
        "messagesToday": messages_today,
        "resolutionRate": resolution_rate,
    }


def get_crm_timeline(db: Session, days: int = 14) -> List[Dict[str, Any]]:
    result = []
    now = datetime.now(tz=timezone.utc)
    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        opened = (
            db.query(func.count(FactTicket.id))
            .filter(FactTicket.opened_at >= day_start, FactTicket.opened_at < day_end)
            .scalar() or 0
        )
        resolved = (
            db.query(func.count(FactTicket.id))
            .filter(FactTicket.resolved_at >= day_start, FactTicket.resolved_at < day_end)
            .scalar() or 0
        )
        result.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "opened": opened,
            "resolved": resolved,
        })
    return result


def get_recent_tickets(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    tickets = (
        db.query(FactTicket)
        .order_by(FactTicket.opened_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "ticketId": t.ticket_id,
            "asunto": t.asunto or "",
            "estado": t.estado,
            "prioridad": t.prioridad,
            "canal": t.canal or "",
            "sourceProject": t.source_project or "",
            "openedAt": t.opened_at.isoformat() if t.opened_at else "",
            "updatedAt": t.updated_at.isoformat() if t.updated_at else "",
        }
        for t in tickets
    ]


def get_sla_summary(db: Session) -> Dict[str, Any]:
    total_violations = db.query(func.count(FactSlaViolacion.id)).scalar() or 0
    critical_violations = (
        db.query(func.count(FactSlaViolacion.id))
        .filter(FactSlaViolacion.threshold_crossed >= 100)
        .scalar() or 0
    )
    tickets_within_sla = (
        db.query(func.count(FactTicket.id))
        .filter(FactTicket.within_sla == True)
        .scalar() or 0
    )
    tickets_evaluated = (
        db.query(func.count(FactTicket.id))
        .filter(FactTicket.within_sla.isnot(None))
        .scalar() or 1
    )
    sla_compliance = round((tickets_within_sla / tickets_evaluated) * 100, 1)

    return {
        "totalViolations": total_violations,
        "criticalViolations": critical_violations,
        "slaComplianceRate": sla_compliance,
    }
