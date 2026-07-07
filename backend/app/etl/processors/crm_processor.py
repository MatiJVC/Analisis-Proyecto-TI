from datetime import datetime, timezone
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


# Transiciones válidas: event_type → estados de origen permitidos
# Solo los eventos que cambian estado de un ticket existente están aquí.
_VALID_TRANSITIONS: Dict[str, tuple] = {
    "ticket.asignado": ("Abierto",),
    "ticket.escalado": ("Progreso",),
    "ticket.resuelto": ("Progreso",),
    "ticket.cerrado":  ("Resuelto",),
}

# ---------------------------------------------------------------------------
# Normalización de casing — el CRM externo (pgti-proyecto-crm-backend) envía
# estado/prioridad/canal en minúscula sin tilde, pero los CheckConstraint de
# fact_tickets solo aceptan el español capitalizado con tilde. Se normaliza
# aquí, en la frontera de ingesta, en vez de migrar el esquema/constraint.
# ---------------------------------------------------------------------------

_ESTADO_CANONICAL = {"Abierto", "Progreso", "Resuelto", "Cerrado"}
_ESTADO_ALIASES = {
    "abierto": "Abierto",
    "progreso": "Progreso",
    "resuelto": "Resuelto",
    "cerrado": "Cerrado",
}

_PRIORIDAD_CANONICAL = {"Baja", "Media", "Alta", "Crítica"}
_PRIORIDAD_ALIASES = {
    "baja": "Baja",
    "media": "Media",
    "alta": "Alta",
    "critica": "Crítica",
    "crítica": "Crítica",
}

_CANAL_CANONICAL = {"Chat", "Email", "Teléfono", "App"}
_CANAL_ALIASES = {
    "chat": "Chat",
    "email": "Email",
    "telefono": "Teléfono",
    "teléfono": "Teléfono",
    "app": "App",
}


def _normalize(value: Any, canonical: set, aliases: Dict[str, str], field_name: str) -> str:
    if value in canonical:
        return value
    normalized = aliases.get(str(value).strip().lower())
    if normalized is None:
        raise CRMProcessingError(f"Valor no reconocido para {field_name}: {value!r}")
    return normalized


def _normalize_estado(value: Any) -> str:
    return _normalize(value, _ESTADO_CANONICAL, _ESTADO_ALIASES, "estado")


def _normalize_prioridad(value: Any) -> str:
    return _normalize(value, _PRIORIDAD_CANONICAL, _PRIORIDAD_ALIASES, "prioridad")


def _normalize_canal(value: Any) -> Optional[str]:
    if value is None:
        return None
    return _normalize(value, _CANAL_CANONICAL, _CANAL_ALIASES, "canal")


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _require_ticket(db: Session, ticket_id: str) -> FactTicket:
    """Obtiene un ticket existente o lanza CRMProcessingError si no existe."""
    ticket = db.query(FactTicket).filter(FactTicket.ticket_id == ticket_id).first()
    if not ticket:
        raise CRMProcessingError(
            f"Ticket '{ticket_id}' no encontrado — "
            "debe procesarse ticket.creado antes de modificar su estado"
        )
    return ticket


def _validate_transition(ticket: FactTicket, event_type: str) -> None:
    """Valida que el estado actual del ticket permita la transición del evento."""
    allowed = _VALID_TRANSITIONS.get(event_type)
    if allowed is None:
        return
    if ticket.estado not in allowed:
        raise CRMProcessingError(
            f"Transición inválida para '{event_type}': "
            f"ticket '{ticket.ticket_id}' está en '{ticket.estado}' "
            f"pero se requiere {list(allowed)}"
        )


def _get_or_create_ticket(db: Session, ticket_id: str, payload: Dict[str, Any]) -> FactTicket:
    ticket = db.query(FactTicket).filter(FactTicket.ticket_id == ticket_id).first()
    if ticket:
        return ticket
    return FactTicket(
        ticket_id=ticket_id,
        asunto=payload.get("asunto"),
        estado=_normalize_estado(payload.get("estado", "Abierto")),
        prioridad=_normalize_prioridad(payload.get("prioridad", "Media")),
        canal=_normalize_canal(payload.get("canal")),
        source_project=payload.get("source_project"),
        cliente_identidad_id=payload.get("cliente_identidad_id"),
        agente_id=payload.get("agente_id"),
        pedido_id_ref=payload.get("pedido_id_ref"),
        suscripcion_id_red=payload.get("suscripcion_id_red"),
        cliente_id=payload.get("cliente_id"),
        cliente_nombre=payload.get("cliente_nombre"),
        pago_id_ref=payload.get("pago_id_ref"),
        salud_ref=payload.get("salud_ref"),
        fecha_vencimiento_sla=_parse_dt(payload.get("fecha_vencimiento_sla")),
        opened_at=datetime.now(tz=timezone.utc),
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
    if not cliente and payload.get("email"):
        cliente = (
            db.query(DimClienteCRM)
            .filter(DimClienteCRM.email == payload["email"])
            .first()
        )
        if cliente:
            cliente.cliente_identidad_id = identidad_id
    if cliente:
        if payload.get("email"):
            cliente.email = payload["email"]
        if payload.get("telefono"):
            cliente.telefono = payload["telefono"]
        cliente.updated_at = datetime.now(tz=timezone.utc)
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
    ticket = _require_ticket(db, ticket_id)
    _validate_transition(ticket, "ticket.asignado")
    ticket.estado = "Progreso"
    ticket.agente_id = payload.get("agente_id", ticket.agente_id)
    ticket.updated_at = datetime.now(tz=timezone.utc)
    db.add(ticket)
    db.flush()
    return ticket


def _handle_ticket_escalado(db: Session, payload: Dict[str, Any]) -> FactTicket:
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise CRMProcessingError("Campo requerido faltante: ticket_id")
    ticket = _require_ticket(db, ticket_id)
    _validate_transition(ticket, "ticket.escalado")
    if payload.get("prioridad_al_escalar"):
        ticket.prioridad = _normalize_prioridad(payload["prioridad_al_escalar"])
    ticket.updated_at = datetime.now(tz=timezone.utc)
    db.add(ticket)
    db.flush()
    return ticket


def _handle_ticket_resuelto(db: Session, payload: Dict[str, Any]) -> FactTicket:
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise CRMProcessingError("Campo requerido faltante: ticket_id")
    ticket = _require_ticket(db, ticket_id)
    _validate_transition(ticket, "ticket.resuelto")
    ticket.estado = "Resuelto"
    ticket.resolved_at = _parse_dt(payload.get("resolved_at")) or datetime.now(tz=timezone.utc)
    if payload.get("resolution_time_hours") is not None:
        ticket.resolution_time_hours = float(payload["resolution_time_hours"])
    if "within_sla" in payload:
        ticket.within_sla = bool(payload["within_sla"])
    if payload.get("prioridad"):
        ticket.prioridad = _normalize_prioridad(payload["prioridad"])
    if payload.get("agente_id"):
        ticket.agente_id = payload["agente_id"]
    if payload.get("resolucion"):
        ticket.resolucion = payload["resolucion"]
    ticket.updated_at = datetime.now(tz=timezone.utc)
    db.add(ticket)
    db.flush()
    return ticket


def _handle_ticket_cerrado(db: Session, payload: Dict[str, Any]) -> FactTicket:
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        raise CRMProcessingError("Campo requerido faltante: ticket_id")
    ticket = _require_ticket(db, ticket_id)
    _validate_transition(ticket, "ticket.cerrado")
    ticket.estado = "Cerrado"
    ticket.closed_at = _parse_dt(payload.get("closed_at")) or datetime.now(tz=timezone.utc)
    if payload.get("csat_score") is not None:
        ticket.csat_score = int(payload["csat_score"])
    ticket.updated_at = datetime.now(tz=timezone.utc)
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
        prioridad=_normalize_prioridad(payload.get("prioridad", "Media")),
        canal=_normalize_canal(payload.get("canal")),
        source_project=payload.get("source_project"),
        sla_threshold_hours=float(payload.get("sla_threshold_hours", 8)),
        elapsed_hours=float(payload.get("elapsed_hours", 0)),
        breach_percentage=float(payload.get("breach_percentage", 0)),
        threshold_crossed=int(payload.get("threshold_crossed", 100)),
        escalation_required=bool(payload.get("escalation_required", False)),
        escalado_hacia=payload.get("escalado_hacia"),
        fecha_vencimiento_sla=_parse_dt(payload.get("fecha_vencimiento_sla")),
        violation_detected_at=_parse_dt(payload.get("violation_detected_at")) or datetime.now(tz=timezone.utc),
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
