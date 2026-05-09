"""
ETL: dominio incidentes → tablas dim_inc_* / fact_inc_*.
Contrato esperado en raw_events cuando source=\"incidentes\".
"""

from datetime import datetime
from typing import Any, Callable, Dict, Optional
import uuid as uuid_pkg
from sqlalchemy.orm import Session

from app.models.raw import RawEvent
from app.models.warehouse.incidentes import (
    DimIncPoliticaSla,
    DimIncReglaEscalamiento,
    DimIncSistema,
    FactIncAccionPlaybook,
    FactIncAuditoria,
    FactIncEvidencia,
    FactIncEventoAlerta,
    FactIncHistorialEstado,
    FactIncidente,
)


class IncidentProcessingError(Exception):
    """Error de validación o regla de negocio al procesar un evento de incidentes."""


def _to_uuid(field: str, value: Any) -> uuid_pkg.UUID:
    if value is None:
        raise IncidentProcessingError(f"Campo requerido UUID: {field}")
    if isinstance(value, uuid_pkg.UUID):
        return value
    try:
        return uuid_pkg.UUID(str(value))
    except (ValueError, TypeError) as e:
        raise IncidentProcessingError(f"UUID inválido para {field}: {value!r}") from e


def _to_uuid_opt(value: Any) -> Optional[uuid_pkg.UUID]:
    if value is None:
        return None
    try:
        return _to_uuid("optional", value)
    except IncidentProcessingError:
        return None


def _parse_dt(field: str, value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        raise IncidentProcessingError(f"Timestamp requerido: {field}")
    if isinstance(value, str):
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except ValueError as e:
            raise IncidentProcessingError(f"Formato de fecha inválido en {field}: {value!r}") from e
    raise IncidentProcessingError(f"Tipo de fecha no soportado en {field}")


def _sistema_dim(db: Session, sistema_id_bk: str) -> DimIncSistema:
    row = db.query(DimIncSistema).filter(DimIncSistema.sistema_id == sistema_id_bk).first()
    if not row:
        raise IncidentProcessingError(
            f"Sistema '{sistema_id_bk}' no existe en DWH; envíe primero evento sistema_upsert"
        )
    return row


def _politica_dim_opt(db: Session, pid: uuid_pkg.UUID) -> Optional[DimIncPoliticaSla]:
    return db.query(DimIncPoliticaSla).filter(DimIncPoliticaSla.politica_sla_id == pid).first()


def _handle_sistema_upsert(db: Session, payload: Dict[str, Any]) -> DimIncSistema:
    bk = payload.get("sistema_id")
    if not bk:
        raise IncidentProcessingError("sistema_id requerido")

    nombre = payload.get("nombre") or bk
    descripcion = payload.get("descripcion")
    row = db.query(DimIncSistema).filter(DimIncSistema.sistema_id == bk).first()
    now = datetime.utcnow()
    if row:
        row.nombre = nombre
        if descripcion is not None:
            row.descripcion = descripcion
        row.updated_at = now
        return row

    row = DimIncSistema(sistema_id=bk, nombre=nombre, descripcion=descripcion, created_at=now, updated_at=now)
    db.add(row)
    db.flush()
    return row


def _handle_politica_sla_upsert(db: Session, payload: Dict[str, Any]) -> DimIncPoliticaSla:
    pk = _to_uuid("politica_sla_id", payload.get("politica_sla_id"))
    nombre = payload.get("nombre")
    if not nombre:
        raise IncidentProcessingError("nombre es requerido para politica_sla_upsert")
    tmr = payload.get("tiempo_maximo_resolucion_minutos")
    if tmr is None:
        raise IncidentProcessingError("tiempo_maximo_resolucion_minutos requerido")

    row = db.query(DimIncPoliticaSla).filter(DimIncPoliticaSla.politica_sla_id == pk).first()
    now = datetime.utcnow()
    if row:
        row.nombre = nombre
        row.tiempo_maximo_resolucion_minutos = int(tmr)
        row.updated_at = now
        return row

    row = DimIncPoliticaSla(
        politica_sla_id=pk,
        nombre=nombre,
        tiempo_maximo_resolucion_minutos=int(tmr),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_regla_escalamiento_upsert(db: Session, payload: Dict[str, Any]) -> DimIncReglaEscalamiento:
    rid = _to_uuid("regla_id", payload.get("regla_id"))
    politica_bk = _to_uuid("politica_sla_id", payload.get("politica_sla_id"))
    t_act = payload.get("tiempo_activacion_minutos")
    if t_act is None:
        raise IncidentProcessingError("tiempo_activacion_minutos requerido")

    sla = _politica_dim_opt(db, politica_bk)
    if not sla:
        raise IncidentProcessingError("política SLA no existe en DWH; envíe politica_sla_upsert primero")

    notif_user = _to_uuid_opt(payload.get("notificar_a_usuario_id"))
    row = db.query(DimIncReglaEscalamiento).filter(DimIncReglaEscalamiento.regla_id == rid).first()
    now = datetime.utcnow()
    if row:
        row.politica_sla_dim_id = sla.id
        row.tiempo_activacion_minutos = int(t_act)
        row.notificar_a_usuario_id = notif_user
        row.updated_at = now
        return row

    row = DimIncReglaEscalamiento(
        regla_id=rid,
        politica_sla_dim_id=sla.id,
        tiempo_activacion_minutos=int(t_act),
        notificar_a_usuario_id=notif_user,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_incidente_upsert(db: Session, payload: Dict[str, Any]) -> FactIncidente:
    iid = _to_uuid("incidente_id", payload.get("incidente_id"))
    sid = payload.get("sistema_id")
    if not sid:
        raise IncidentProcessingError("sistema_id requerido")

    sistema_dim = _sistema_dim(db, sid)
    politica_bk = _to_uuid_opt(payload.get("politica_sla_id"))
    politica_dim_id = None
    if politica_bk:
        ps = _politica_dim_opt(db, politica_bk)
        if not ps:
            raise IncidentProcessingError("política SLA referenciada no existe en DWH")
        politica_dim_id = ps.id

    titulo = payload.get("titulo")
    if titulo is None:
        raise IncidentProcessingError("titulo requerido")
    estado = payload.get("estado")
    if estado is None:
        raise IncidentProcessingError("estado requerido")
    creado_en = _parse_dt("creado_en", payload.get("creado_en"))

    row = db.query(FactIncidente).filter(FactIncidente.incidente_id == iid).first()
    now = datetime.utcnow()
    desc = payload.get("descripcion")
    creador_user = _to_uuid_opt(payload.get("creador_usuario_id"))

    if row:
        row.titulo = titulo
        row.descripcion = desc
        row.estado = estado
        row.sistema_dim_id = sistema_dim.id
        row.politica_sla_dim_id = politica_dim_id
        if creador_user is not None:
            row.creador_usuario_id = creador_user
        row.updated_at = now
        return row

    row = FactIncidente(
        incidente_id=iid,
        sistema_dim_id=sistema_dim.id,
        politica_sla_dim_id=politica_dim_id,
        titulo=titulo,
        descripcion=desc,
        estado=estado,
        creador_usuario_id=creador_user,
        creado_en=creado_en,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_evento_alerta_creado(db: Session, payload: Dict[str, Any]) -> FactIncEventoAlerta:
    eid = _to_uuid("evento_alerta_id", payload.get("evento_alerta_id"))
    sid_bk = payload.get("sistema_id")
    if not sid_bk:
        raise IncidentProcessingError("sistema_id requerido")
    sistema_dim = _sistema_dim(db, sid_bk)

    incidente_bk = _to_uuid_opt(payload.get("incidente_id"))
    creado_en = _parse_dt("creado_en", payload.get("creado_en"))

    existing = db.query(FactIncEventoAlerta).filter(FactIncEventoAlerta.evento_alerta_id == eid).first()
    now = datetime.utcnow()
    if existing:
        existing.sistema_dim_id = sistema_dim.id
        existing.incidente_id = incidente_bk
        existing.payload = payload.get("payload")
        existing.creado_en = creado_en
        existing.updated_at = now
        return existing

    row = FactIncEventoAlerta(
        sistema_dim_id=sistema_dim.id,
        incidente_id=incidente_bk,
        evento_alerta_id=eid,
        payload=payload.get("payload"),
        creado_en=creado_en,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _require_incident_fk(db: Session, incidente_uuid: uuid_pkg.UUID) -> None:
    exists = db.query(FactIncidente.incidente_id).filter(FactIncidente.incidente_id == incidente_uuid).first()
    if not exists:
        raise IncidentProcessingError(
            "incidente_id no existe en fact_inc_incidentes; envíe incidente_upsert primero"
        )


def _handle_historial_estado_registrado(db: Session, payload: Dict[str, Any]) -> FactIncHistorialEstado:
    hid = _to_uuid("historial_id", payload.get("historial_id"))
    iid = _to_uuid("incidente_id", payload.get("incidente_id"))
    _require_incident_fk(db, iid)
    nuevo = payload.get("estado_nuevo")
    if nuevo is None:
        raise IncidentProcessingError("estado_nuevo requerido")
    cambiado_en = _parse_dt("cambiado_en", payload.get("cambiado_en"))

    row = db.query(FactIncHistorialEstado).filter(FactIncHistorialEstado.historial_id == hid).first()
    if row:
        row.estado_anterior = payload.get("estado_anterior")
        row.estado_nuevo = nuevo
        row.cambiado_por_usuario_id = _to_uuid_opt(payload.get("cambiado_por_usuario_id"))
        row.cambiado_en = cambiado_en
        return row

    row = FactIncHistorialEstado(
        incidente_id=iid,
        historial_id=hid,
        estado_anterior=payload.get("estado_anterior"),
        estado_nuevo=nuevo,
        cambiado_por_usuario_id=_to_uuid_opt(payload.get("cambiado_por_usuario_id")),
        cambiado_en=cambiado_en,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def _handle_auditoria_registrada(db: Session, payload: Dict[str, Any]) -> FactIncAuditoria:
    aid = _to_uuid("auditoria_id", payload.get("auditoria_id"))
    iid = _to_uuid("incidente_id", payload.get("incidente_id"))
    _require_incident_fk(db, iid)
    descr = payload.get("descripcion_accion")
    if descr is None:
        raise IncidentProcessingError("descripcion_accion requerido")
    creado_en = _parse_dt("creado_en", payload.get("creado_en"))

    row = db.query(FactIncAuditoria).filter(FactIncAuditoria.auditoria_id == aid).first()
    if row:
        row.descripcion_accion = descr
        row.accion_por_usuario_id = _to_uuid_opt(payload.get("accion_por_usuario_id"))
        row.creado_en = creado_en
        return row

    row = FactIncAuditoria(
        incidente_id=iid,
        auditoria_id=aid,
        accion_por_usuario_id=_to_uuid_opt(payload.get("accion_por_usuario_id")),
        descripcion_accion=descr,
        creado_en=creado_en,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def _handle_accion_playbook_ejecutada(db: Session, payload: Dict[str, Any]) -> FactIncAccionPlaybook:
    aid = _to_uuid("accion_id", payload.get("accion_id"))
    iid = _to_uuid("incidente_id", payload.get("incidente_id"))
    _require_incident_fk(db, iid)
    tipo = payload.get("tipo_accion")
    if not tipo:
        raise IncidentProcessingError("tipo_accion requerido")
    ejecutado_en = _parse_dt("ejecutado_en", payload.get("ejecutado_en"))

    row = db.query(FactIncAccionPlaybook).filter(FactIncAccionPlaybook.accion_id == aid).first()
    if row:
        row.tipo_accion = tipo
        row.ejecutado_por_usuario_id = _to_uuid_opt(payload.get("ejecutado_por_usuario_id"))
        row.ejecutado_en = ejecutado_en
        return row

    row = FactIncAccionPlaybook(
        incidente_id=iid,
        accion_id=aid,
        tipo_accion=tipo,
        ejecutado_por_usuario_id=_to_uuid_opt(payload.get("ejecutado_por_usuario_id")),
        ejecutado_en=ejecutado_en,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def _handle_evidencia_subida(db: Session, payload: Dict[str, Any]) -> FactIncEvidencia:
    eid = _to_uuid("evidencia_id", payload.get("evidencia_id"))
    iid = _to_uuid("incidente_id", payload.get("incidente_id"))
    _require_incident_fk(db, iid)
    url = payload.get("url_archivo")
    if not url:
        raise IncidentProcessingError("url_archivo requerido")
    subido = _parse_dt("subido_en", payload.get("subido_en"))

    row = db.query(FactIncEvidencia).filter(FactIncEvidencia.evidencia_id == eid).first()
    if row:
        row.url_archivo = url
        row.descripcion = payload.get("descripcion")
        row.subido_en = subido
        return row

    row = FactIncEvidencia(
        incidente_id=iid,
        evidencia_id=eid,
        url_archivo=url,
        descripcion=payload.get("descripcion"),
        subido_en=subido,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


_HANDLERS: Dict[str, Callable[[Session, Dict[str, Any]], Any]] = {
    "sistema_upsert": _handle_sistema_upsert,
    "politica_sla_upsert": _handle_politica_sla_upsert,
    "regla_escalamiento_upsert": _handle_regla_escalamiento_upsert,
    "incidente_upsert": _handle_incidente_upsert,
    "evento_alerta_creado": _handle_evento_alerta_creado,
    "historial_estado_registrado": _handle_historial_estado_registrado,
    "auditoria_registrada": _handle_auditoria_registrada,
    "accion_playbook_ejecutada": _handle_accion_playbook_ejecutada,
    "evidencia_subida": _handle_evidencia_subida,
}


def process_incident_event(db: Session, raw_event: RawEvent):
    """Procesa un raw_event cuando source sea 'incidentes'."""
    if raw_event.source != "incidentes":
        raise IncidentProcessingError(
            f"Multi-tenant incidents: raw_event.source debe ser 'incidentes', fue {raw_event.source!r}"
        )

    handler = _HANDLERS.get(raw_event.event_type or "")
    if not handler:
        raise IncidentProcessingError(f"event_type no soportado en dominio incidentes: {raw_event.event_type!r}")

    payload = raw_event.payload or {}
    return handler(db, payload)
