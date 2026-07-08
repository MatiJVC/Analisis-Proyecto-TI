import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.warehouse.fact_tickets import FactTicket
from app.models.warehouse.dim_clientes_crm import DimClienteCRM
from app.models.warehouse.fact_sla_violaciones import FactSlaViolacion

# La BD tiene casing mezclado en tickets históricos (minúscula sin tilde del CRM
# externo) vs. los nuevos ya normalizados en la ingesta. Para que las
# distribuciones no dupliquen categorías ("alta" vs "Alta"), se normaliza al
# canónico en la capa de agregación. Passthrough para valores no reconocidos
# (no lanza, a diferencia de crm_processor._normalize_*: un dato inesperado no
# debe romper un gráfico). Constantes locales al módulo de analítica, sin
# acoplar con las del processor.
_PRIORIDAD_CANON = {
    "baja": "Baja", "media": "Media", "alta": "Alta",
    "critica": "Crítica", "crítica": "Crítica",
}
_CANAL_CANON = {
    "chat": "Chat", "email": "Email",
    "telefono": "Teléfono", "teléfono": "Teléfono", "app": "App",
}
# Formas en minúscula para filtros SQL case-insensitive (vía func.lower),
# de modo que los conteos incluyan también los tickets históricos en minúscula.
_CRITICAL_PRIORITIES_LOWER = ("alta", "crítica", "critica")
_OPEN_STATES_LOWER = ("abierto", "progreso")
_CLOSED_STATE_LOWER = "cerrado"


def _canon(value: Optional[str], mapping: Dict[str, str]) -> Optional[str]:
    if value is None:
        return None
    return mapping.get(str(value).strip().lower(), value)


def _merge_distribution(rows: List[Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    """Agrupa `rows` [(name, count)] fusionando por forma canónica (casing)."""
    merged: Dict[str, int] = {}
    for name, count in rows:
        key = _canon(name, mapping)
        merged[key] = merged.get(key, 0) + count
    total = sum(merged.values())
    return _distribution(list(merged.items()), total)


def get_crm_kpis(db: Session) -> Dict[str, Any]:
    today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_customers = db.query(func.count(DimClienteCRM.id)).scalar() or 0

    open_tickets = (
        db.query(func.count(FactTicket.id))
        .filter(func.lower(FactTicket.estado).in_(_OPEN_STATES_LOWER))
        .scalar() or 0
    )

    avg_response_time = (
        db.query(func.avg(FactTicket.resolution_time_hours))
        .filter(FactTicket.resolution_time_hours.isnot(None))
        .scalar()
    )
    avg_response_time = round(float(avg_response_time) * 60, 1) if avg_response_time else 0.0

    critical_tickets = (
        db.query(func.count(FactTicket.id))
        .filter(
            func.lower(FactTicket.estado).in_(_OPEN_STATES_LOWER),
            func.lower(FactTicket.prioridad).in_(_CRITICAL_PRIORITIES_LOWER),
        )
        .scalar() or 0
    )

    tickets_created_today = (
        db.query(func.count(FactTicket.id))
        .filter(FactTicket.opened_at >= today_start)
        .scalar() or 0
    )

    resolved = db.query(func.count(FactTicket.id)).filter(
        func.lower(FactTicket.estado) == _CLOSED_STATE_LOWER
    ).scalar() or 0
    total = db.query(func.count(FactTicket.id)).scalar() or 1
    resolution_rate = round((resolved / total) * 100, 1)

    return {
        "totalCustomers": total_customers,
        "openTickets": open_tickets,
        "avgResponseTimeMinutes": avg_response_time,
        "criticalTickets": critical_tickets,
        "ticketsCreatedToday": tickets_created_today,
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
    # Ordena por última actividad (updated_at) con fallback a opened_at, así los
    # tickets que cambian de estado suben y se refleja el movimiento — no solo
    # los recién creados.
    tickets = (
        db.query(FactTicket)
        .order_by(func.coalesce(FactTicket.updated_at, FactTicket.opened_at).desc())
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


def _distribution(rows: List[Any], total: int) -> Dict[str, Any]:
    items = [
        {
            "name": name,
            "count": count,
            "percentage": round((count / total) * 100, 1) if total else 0.0,
        }
        for name, count in rows
    ]
    return {"total": total, "items": items}


def get_tickets_by_channel(db: Session) -> Dict[str, Any]:
    rows = (
        db.query(FactTicket.canal, func.count(FactTicket.id))
        .filter(FactTicket.canal.isnot(None))
        .group_by(FactTicket.canal)
        .all()
    )
    # Fusiona casing mezclado ("email" vs "Email") en una sola categoría.
    return _merge_distribution(rows, _CANAL_CANON)


def get_tickets_by_priority(db: Session) -> Dict[str, Any]:
    rows = (
        db.query(FactTicket.prioridad, func.count(FactTicket.id))
        .group_by(FactTicket.prioridad)
        .all()
    )
    # Fusiona casing mezclado ("alta" vs "Alta", "critica" vs "Crítica").
    return _merge_distribution(rows, _PRIORIDAD_CANON)


def get_tickets_by_source_project(db: Session) -> Dict[str, Any]:
    rows = (
        db.query(FactTicket.source_project, func.count(FactTicket.id))
        .filter(FactTicket.source_project.isnot(None))
        .group_by(FactTicket.source_project)
        .all()
    )
    total = sum(count for _, count in rows)
    return _distribution(rows, total)


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
        .scalar() or 0
    )
    # Sin tickets evaluables no hay una tasa real de cumplimiento — se devuelve
    # 0.0 pero el frontend usa ticketsEvaluated para mostrar "Sin datos" en vez
    # de un 0.0% engañoso (que parece incumplimiento total cuando en realidad
    # todavía no se ha resuelto ningún ticket con dato de SLA).
    sla_compliance = (
        round((tickets_within_sla / tickets_evaluated) * 100, 1) if tickets_evaluated else 0.0
    )

    return {
        "totalViolations": total_violations,
        "criticalViolations": critical_violations,
        "slaComplianceRate": sla_compliance,
        "ticketsEvaluated": tickets_evaluated,
    }


_AGENTE_ID_MODULO_RE = re.compile(r"^p(\d{1,2})\.", re.IGNORECASE)

# Convención de numeración de grupos del proyecto (confirmada por el usuario,
# jul-2026): agente_id de tickets externos viene como "p{N}.algo@..." donde N
# identifica el grupo de origen. Los tickets internos del propio CRM (grupo 07)
# no siguen necesariamente este patrón, así que ese es también el default.
_MODULO_POR_NUMERO = {
    1: "Salud",
    2: "Logística",
    3: "Pedidos",
    4: "Pagos",
    5: "Inventario",
    6: "Notificaciones",
    7: "CRM",
    8: "IoT",
    9: "Analítica",
    10: "Suscripciones",
    11: "Incidentes",
    12: "Identidad",
}


def _clasificar_modulo(
    agente_id: Optional[str],
    pedido_id_ref: Optional[str],
    pago_id_ref: Optional[str],
    salud_ref: Optional[str],
    suscripcion_id_ref: Optional[str],
) -> str:
    """Clasifica a qué grupo/módulo pertenece un ticket.

    Fuente primaria: el prefijo numérico de `agente_id` (`p{N}.` → grupo N).
    Fallback: los 4 campos de referencia cruzada que sí tenemos en el modelo
    (cubren solo Pedidos/Pagos/Salud/Suscripciones). Si nada matchea, se asume
    ticket interno del propio CRM.
    """
    if agente_id:
        match = _AGENTE_ID_MODULO_RE.match(agente_id.strip())
        if match:
            numero = int(match.group(1))
            if numero in _MODULO_POR_NUMERO:
                return _MODULO_POR_NUMERO[numero]

    if pedido_id_ref:
        return "Pedidos"
    if pago_id_ref:
        return "Pagos"
    if salud_ref:
        return "Salud"
    if suscripcion_id_ref:
        return "Suscripciones"

    return "CRM"


def get_critical_tickets_by_module(db: Session) -> Dict[str, Any]:
    """Distribución de tickets críticos abiertos (Alta/Crítica, sin cerrar)
    por módulo de origen — mismo universo que el KPI `criticalTickets`."""
    rows = (
        db.query(
            FactTicket.agente_id,
            FactTicket.pedido_id_ref,
            FactTicket.pago_id_ref,
            FactTicket.salud_ref,
            FactTicket.suscripcion_id_red,
        )
        .filter(
            func.lower(FactTicket.estado).in_(_OPEN_STATES_LOWER),
            func.lower(FactTicket.prioridad).in_(_CRITICAL_PRIORITIES_LOWER),
        )
        .all()
    )
    conteo: Dict[str, int] = {}
    for agente_id, pedido_id_ref, pago_id_ref, salud_ref, suscripcion_id_ref in rows:
        modulo = _clasificar_modulo(agente_id, pedido_id_ref, pago_id_ref, salud_ref, suscripcion_id_ref)
        conteo[modulo] = conteo.get(modulo, 0) + 1

    total = sum(conteo.values())
    return _distribution(list(conteo.items()), total)
