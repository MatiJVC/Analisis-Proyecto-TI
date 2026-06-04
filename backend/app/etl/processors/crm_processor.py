from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.warehouse.fact_tickets import FactTicket
from app.models.warehouse.dim_clientes_crm import DimClienteCRM
from app.models.warehouse.fact_interacciones import FactInteraccion
from app.models.warehouse.fact_ticket_articulos import FactTicketArticulo
from app.models.warehouse.fact_sla_violaciones import FactSlaViolacion


class CRMProcessingError(Exception):
    pass


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _get_or_create_ticket(db: Session, ticket_id: str, payload: Dict[str, Any]) -> FactTicket:
    ticket = db.query(FactTicket).filter(FactTicket.ticket_id == ticket_id).first()
    if ticket:
        return ticket
    return FactTicket(
        ticket_id=ticket_id,
        asunto=payload.get("asunto"),
        estado=payload.get("estado", "Abierto"),
        prioridad=payload.get("prioridad", "Media"),
        canal=payload.get("canal"),
        source_project=payload.get("source_project"),
        cliente_identidad_id=payload.get("cliente_identidad_id"),
        agente_id=payload.get("agente_id"),
        pedido_id_ref=payload.get("pedido_id_ref"),
        suscripcion_id_red=payload.get("suscripcion_id_red"),
        fecha_vencimiento_sla=_parse_dt(payload.get("fecha_vencimiento_sla")),
        opened_at=datetime.utcnow(),
    )


def _upsert_cliente(db: Session, payload: Dict[str, Any]) -> Optional[DimClienteCRM]:
    identidad_id = payload.get("cliente_identidad_id")
    if not identidad_id:
        return None
    cliente = (
        db.query(DimClienteCRM)
        .filter(DimClienteCRM.cliente_identidad_id == identidad_id)
        .first()
    )
    if cliente:
        if payload.get("email"):
            cliente.email = payload["email"]
        if payload.get("telefono"):
            cliente.telefono = payload["telefono"]
        cliente.updated_at = datetime.utcnow()
    else:
        cliente = DimClienteCRM(
            cliente_identidad_id=identidad_id,
            email=payload.get("email"),
            telefono=payload.get("telefono"),
        )
        db.add(cliente)
    return cliente


# ---------------------------------------------------------------------------
# Handlers por event_type
# ---------------------------------------------------------------------------

def _handle_ticket_creado(db: Session, payload: Dict[str, Any]) -> FactTicket:
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise CRMProcessingError("Campo requerido faltante: ticket_id")
    _upsert_cliente(db, payload)
    ticket = _get_or_create_ticket(db, ticket_id, payload)
    db.add(ticket)
    db.flush()
    return ticket


def _handle_ticket_asignado(db: Session, payload: Dict[str, Any]) -> FactTicket:
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise CRMProcessingError("Campo requerido faltante: ticket_id")
    ticket = _get_or_create_ticket(db, ticket_id, payload)
    ticket.estado = payload.get("estado", ticket.estado)
    ticket.agente_id = payload.get("agente_id", ticket.agente_id)
    ticket.updated_at = datetime.utcnow()
    db.add(ticket)
    db.flush()
    return ticket


def _handle_ticket_escalado(db: Session, payload: Dict[str, Any]) -> FactTicket:
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise CRMProcessingError("Campo requerido faltante: ticket_id")
    ticket = _get_or_create_ticket(db, ticket_id, payload)
    if payload.get("prioridad_al_escalar"):
        ticket.prioridad = payload["prioridad_al_escalar"]
    ticket.estado = payload.get("estado", ticket.estado)
    ticket.updated_at = datetime.utcnow()
    db.add(ticket)
    db.flush()
    return ticket


def _handle_ticket_resuelto(db: Session, payload: Dict[str, Any]) -> FactTicket:
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise CRMProcessingError("Campo requerido faltante: ticket_id")
    ticket = _get_or_create_ticket(db, ticket_id, payload)
    ticket.estado = "Resuelto"
    ticket.resolved_at = _parse_dt(payload.get("resolved_at")) or datetime.utcnow()
    if payload.get("resolution_time_hours") is not None:
        ticket.resolution_time_hours = float(payload["resolution_time_hours"])
    if "within_sla" in payload:
        ticket.within_sla = bool(payload["within_sla"])
    if payload.get("prioridad"):
        ticket.prioridad = payload["prioridad"]
    if payload.get("agente_id"):
        ticket.agente_id = payload["agente_id"]
    ticket.updated_at = datetime.utcnow()
    db.add(ticket)
    db.flush()
    return ticket


def _handle_ticket_cerrado(db: Session, payload: Dict[str, Any]) -> FactTicket:
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise CRMProcessingError("Campo requerido faltante: ticket_id")
    ticket = _get_or_create_ticket(db, ticket_id, payload)
    ticket.estado = "Cerrado"
    ticket.closed_at = _parse_dt(payload.get("closed_at")) or datetime.utcnow()
    if payload.get("csat_score") is not None:
        ticket.csat_score = int(payload["csat_score"])
    ticket.updated_at = datetime.utcnow()
    db.add(ticket)
    db.flush()
    return ticket


def _handle_interaccion_creada(db: Session, payload: Dict[str, Any]) -> FactInteraccion:
    interaccion_id = payload.get("interaccion_id")
    if not interaccion_id:
        raise CRMProcessingError("Campo requerido faltante: interaccion_id")
    existing = (
        db.query(FactInteraccion)
        .filter(FactInteraccion.interaccion_id == interaccion_id)
        .first()
    )
    if existing:
        return existing
    interaccion = FactInteraccion(
        interaccion_id=interaccion_id,
        ticket_id=payload.get("ticket_id", ""),
        autor_tipo=payload.get("autor_tipo", "Sistema"),
        autor_id=payload.get("autor_id"),
        contenido=payload.get("contenido"),
        es_nota_interna=bool(payload.get("es_nota_interna", False)),
        creado_en=_parse_dt(payload.get("creado_en")),
    )
    db.add(interaccion)
    db.flush()
    return interaccion


def _handle_kb_articulo_usado(db: Session, payload: Dict[str, Any]) -> FactTicketArticulo:
    ticket_id = payload.get("ticket_id")
    articulo_id = payload.get("articulo_id")
    if not ticket_id or not articulo_id:
        raise CRMProcessingError("Campos requeridos faltantes: ticket_id, articulo_id")
    registro = FactTicketArticulo(
        ticket_id=ticket_id,
        articulo_id=articulo_id,
        articulo_titulo=payload.get("articulo_titulo"),
        articulo_categoria=payload.get("articulo_categoria"),
        fue_enviado_al_cliente=bool(payload.get("fue_enviado_al_cliente", False)),
        agente_id=payload.get("agente_id"),
        vinculado_en=_parse_dt(payload.get("vinculado_en")),
    )
    db.add(registro)
    db.flush()
    return registro


def _handle_ticket_sla_violado(db: Session, payload: Dict[str, Any]) -> FactSlaViolacion:
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise CRMProcessingError("Campo requerido faltante: ticket_id")
    violacion = FactSlaViolacion(
        ticket_id=ticket_id,
        cliente_identidad_id=payload.get("cliente_identidad_id"),
        prioridad=payload.get("prioridad", "Media"),
        canal=payload.get("canal"),
        source_project=payload.get("source_project"),
        sla_threshold_hours=float(payload.get("sla_threshold_hours", 8)),
        elapsed_hours=float(payload.get("elapsed_hours", 0)),
        breach_percentage=float(payload.get("breach_percentage", 0)),
        threshold_crossed=int(payload.get("threshold_crossed", 100)),
        escalation_required=bool(payload.get("escalation_required", False)),
        escalado_hacia=payload.get("escalado_hacia"),
        fecha_vencimiento_sla=_parse_dt(payload.get("fecha_vencimiento_sla")),
        violation_detected_at=_parse_dt(payload.get("violation_detected_at")) or datetime.utcnow(),
    )
    db.add(violacion)
    db.flush()
    return violacion


_HANDLERS = {
    "ticket.creado": _handle_ticket_creado,
    "ticket.asignado": _handle_ticket_asignado,
    "ticket.escalado": _handle_ticket_escalado,
    "ticket.resuelto": _handle_ticket_resuelto,
    "ticket.cerrado": _handle_ticket_cerrado,
    "interaccion.creada": _handle_interaccion_creada,
    "kb.articulo.usado": _handle_kb_articulo_usado,
    "ticket.sla_violado": _handle_ticket_sla_violado,
}


def process_crm_event(db: Session, raw_event: Any) -> Optional[Any]:
    try:
        handler = _HANDLERS.get(raw_event.event_type)
        if not handler:
            raise CRMProcessingError(
                f"event_type no soportado para crm: {raw_event.event_type}"
            )
        payload = raw_event.payload or {}
        return handler(db, payload)
    except CRMProcessingError:
        raise
    except SQLAlchemyError:
        raise
    except Exception as e:
        raise CRMProcessingError(str(e)) from e
