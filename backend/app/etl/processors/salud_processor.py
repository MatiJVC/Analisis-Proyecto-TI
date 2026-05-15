"""
ETL: raw_events (source=salud) → dimensiones y hechos del warehouse salud.
Resuelve claves de negocio a surrogate ids (*_dim_id) en facts.
"""

from __future__ import annotations

from datetime import date, datetime, time as time_type
from typing import Any, Callable, Dict, Optional
import uuid as uuid_pkg

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.raw import RawEvent
from app.models.warehouse import (
    DimEspecialidades,
    DimPacientes,
    DimProfesionales,
    DimUsuarios,
    DimZonas,
    FactAlertas,
    FactFichasClinicas,
    FactVisitas,
)


class SaludProcessingError(Exception):
    """Error de validación o datos faltantes al procesar evento salud."""


def _uuid(field: str, value: Any) -> uuid_pkg.UUID:
    if value is None:
        raise SaludProcessingError(f"UUID requerido: {field}")
    if isinstance(value, uuid_pkg.UUID):
        return value
    try:
        return uuid_pkg.UUID(str(value))
    except (ValueError, TypeError) as e:
        raise SaludProcessingError(f"UUID inválido en {field}: {value!r}") from e


def _uuid_opt(value: Any) -> Optional[uuid_pkg.UUID]:
    if value is None:
        return None
    return _uuid("opcional", value)


def _parse_date(field: str, value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not value:
        raise SaludProcessingError(f"Fecha requerida: {field}")
    if isinstance(value, str):
        return date.fromisoformat(value.strip()[:10])
    raise SaludProcessingError(f"Fecha no soportada en {field}")


def _parse_dt(field: str, value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        raise SaludProcessingError(f"DateTime requerido: {field}")
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError as e:
        raise SaludProcessingError(f"DateTime inválido en {field}: {value!r}") from e


def _parse_time_opt(value: Any) -> Optional[time_type]:
    if value is None or value == "":
        return None
    if isinstance(value, time_type):
        return value
    parts = str(value).strip().split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    sec = int(parts[2]) if len(parts) > 2 else 0
    return time_type(h, m, sec)


def _get_dim_usuario_actual(db: Session, usuario_bk: uuid_pkg.UUID) -> DimUsuarios:
    row = (
        db.query(DimUsuarios)
        .filter(and_(DimUsuarios.usuario_id == usuario_bk, DimUsuarios.es_actual == True))
        .first()
    )
    if not row:
        raise SaludProcessingError(
            f"No existe dim_usuarios actual para usuario_id={usuario_bk}; envíe usuario_upsert primero"
        )
    return row


def _get_dim_paciente_actual(db: Session, paciente_bk: uuid_pkg.UUID) -> DimPacientes:
    row = (
        db.query(DimPacientes)
        .filter(and_(DimPacientes.paciente_id == paciente_bk, DimPacientes.es_actual == True))
        .first()
    )
    if not row:
        raise SaludProcessingError(
            f"No existe dim_pacientes actual para paciente_id={paciente_bk}; envíe paciente_upsert primero"
        )
    return row


def _get_dim_profesional_actual(db: Session, profesional_bk: uuid_pkg.UUID) -> DimProfesionales:
    row = (
        db.query(DimProfesionales)
        .filter(
            and_(DimProfesionales.profesional_id == profesional_bk, DimProfesionales.es_actual == True)
        )
        .first()
    )
    if not row:
        raise SaludProcessingError(
            f"No existe dim_profesionales actual para profesional_id={profesional_bk}; "
            "envíe profesional_upsert primero"
        )
    return row


def _get_dim_zona_actual_opt(db: Session, zona_bk: Optional[uuid_pkg.UUID]) -> Optional[DimZonas]:
    if zona_bk is None:
        return None
    row = (
        db.query(DimZonas)
        .filter(and_(DimZonas.zona_id == zona_bk, DimZonas.es_actual == True))
        .first()
    )
    return row


def _calc_duracion_retraso(
    hora_programada: Optional[time_type],
    fecha_inicio_real: Optional[datetime],
    fecha_fin_real: Optional[datetime],
) -> tuple[Optional[int], Optional[int]]:
    duracion_minutos = None
    retraso_minutos = None
    if fecha_inicio_real and fecha_fin_real:
        duracion_minutos = int((fecha_fin_real - fecha_inicio_real).total_seconds() / 60)
    if hora_programada and fecha_inicio_real:
        try:
            hora_float = hora_programada.hour + hora_programada.minute / 60.0
            inicio_hora_float = fecha_inicio_real.hour + fecha_inicio_real.minute / 60.0
            retraso_minutos = int((inicio_hora_float - hora_float) * 60)
        except Exception:
            retraso_minutos = None
    return duracion_minutos, retraso_minutos


def _handle_usuario_upsert(db: Session, p: Dict[str, Any]) -> DimUsuarios:
    uid = _uuid("usuario_id", p.get("usuario_id"))
    nombres = p.get("nombres")
    apellidos = p.get("apellidos")
    if not nombres or not apellidos:
        raise SaludProcessingError("nombres y apellidos son obligatorios en usuario_upsert")

    row = (
        db.query(DimUsuarios)
        .filter(and_(DimUsuarios.usuario_id == uid, DimUsuarios.es_actual == True))
        .first()
    )
    now = datetime.utcnow()
    if row:
        row.nombres = nombres
        row.apellidos = apellidos
        row.rut = p.get("rut")
        row.email = p.get("email")
        row.telefono = p.get("telefono")
        if p.get("activo") is not None:
            row.activo = bool(p["activo"])
        row.updated_at = now
        return row

    row = DimUsuarios(
        usuario_id=uid,
        nombres=nombres,
        apellidos=apellidos,
        rut=p.get("rut"),
        email=p.get("email"),
        telefono=p.get("telefono"),
        activo=bool(p.get("activo", True)),
        fecha_inicio=now,
        es_actual=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_paciente_upsert(db: Session, p: Dict[str, Any]) -> DimPacientes:
    pid = _uuid("paciente_id", p.get("paciente_id"))
    nombres = p.get("nombres")
    apellidos = p.get("apellidos")
    if not nombres or not apellidos:
        raise SaludProcessingError("nombres y apellidos son obligatorios en paciente_upsert")

    row = (
        db.query(DimPacientes)
        .filter(and_(DimPacientes.paciente_id == pid, DimPacientes.es_actual == True))
        .first()
    )
    now = datetime.utcnow()
    fn = p.get("fecha_nacimiento")
    fecha_nac = _parse_date("fecha_nacimiento", fn) if fn else None

    if row:
        row.nombres = nombres
        row.apellidos = apellidos
        row.rut = p.get("rut")
        row.fecha_nacimiento = fecha_nac
        row.sexo = p.get("sexo")
        row.telefono = p.get("telefono")
        row.email = p.get("email")
        row.direccion = p.get("direccion")
        row.updated_at = now
        return row

    row = DimPacientes(
        paciente_id=pid,
        nombres=nombres,
        apellidos=apellidos,
        rut=p.get("rut"),
        fecha_nacimiento=fecha_nac,
        sexo=p.get("sexo"),
        telefono=p.get("telefono"),
        email=p.get("email"),
        direccion=p.get("direccion"),
        fecha_inicio=now,
        es_actual=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_profesional_upsert(db: Session, p: Dict[str, Any]) -> DimProfesionales:
    prid = _uuid("profesional_id", p.get("profesional_id"))
    usuario_bk = _uuid("usuario_id", p.get("usuario_id"))
    _get_dim_usuario_actual(db, usuario_bk)

    nombres = p.get("nombres")
    apellidos = p.get("apellidos")
    if not nombres or not apellidos:
        raise SaludProcessingError("nombres y apellidos son obligatorios en profesional_upsert")

    row = (
        db.query(DimProfesionales)
        .filter(and_(DimProfesionales.profesional_id == prid, DimProfesionales.es_actual == True))
        .first()
    )
    now = datetime.utcnow()
    if row:
        row.usuario_id = usuario_bk
        row.nombres = nombres
        row.apellidos = apellidos
        row.profesion = p.get("profesion")
        row.numero_registro = p.get("numero_registro")
        if p.get("activo") is not None:
            row.activo = bool(p["activo"])
        row.updated_at = now
        return row

    row = DimProfesionales(
        profesional_id=prid,
        usuario_id=usuario_bk,
        nombres=nombres,
        apellidos=apellidos,
        profesion=p.get("profesion"),
        numero_registro=p.get("numero_registro"),
        activo=bool(p.get("activo", True)),
        fecha_inicio=now,
        es_actual=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_zona_upsert(db: Session, p: Dict[str, Any]) -> DimZonas:
    zid = _uuid("zona_id", p.get("zona_id"))
    nombre = p.get("nombre")
    if not nombre:
        raise SaludProcessingError("nombre es obligatorio en zona_upsert")

    row = (
        db.query(DimZonas).filter(and_(DimZonas.zona_id == zid, DimZonas.es_actual == True)).first()
    )
    now = datetime.utcnow()
    if row:
        row.nombre = nombre
        row.descripcion = p.get("descripcion")
        row.comuna = p.get("comuna")
        row.region = p.get("region")
        if p.get("activa") is not None:
            row.activa = bool(p["activa"])
        row.updated_at = now
        return row

    row = DimZonas(
        zona_id=zid,
        nombre=nombre,
        descripcion=p.get("descripcion"),
        comuna=p.get("comuna"),
        region=p.get("region"),
        activa=bool(p.get("activa", True)),
        fecha_inicio=now,
        es_actual=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_especialidad_upsert(db: Session, p: Dict[str, Any]) -> DimEspecialidades:
    eid = _uuid("especialidad_id", p.get("especialidad_id"))
    nombre = p.get("nombre")
    if not nombre:
        raise SaludProcessingError("nombre es obligatorio en especialidad_upsert")

    row = (
        db.query(DimEspecialidades)
        .filter(and_(DimEspecialidades.especialidad_id == eid, DimEspecialidades.es_actual == True))
        .first()
    )
    now = datetime.utcnow()
    if row:
        row.nombre = nombre
        row.descripcion = p.get("descripcion")
        row.updated_at = now
        return row

    row = DimEspecialidades(
        especialidad_id=eid,
        nombre=nombre,
        descripcion=p.get("descripcion"),
        fecha_inicio=now,
        es_actual=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_visita_upsert(db: Session, p: Dict[str, Any]) -> FactVisitas:
    visita_bk = _uuid("visita_id", p.get("visita_id"))
    paciente_dim = _get_dim_paciente_actual(db, _uuid("paciente_id", p.get("paciente_id")))
    prof_dim = _get_dim_profesional_actual(db, _uuid("profesional_id", p.get("profesional_id")))
    zona_bk = _uuid_opt(p.get("zona_id"))
    zona_dim = _get_dim_zona_actual_opt(db, zona_bk)

    usuario_creador_bk = _uuid_opt(p.get("usuario_creador_id"))
    usuario_creador_dim_id = None
    if usuario_creador_bk:
        usuario_creador_dim_id = _get_dim_usuario_actual(db, usuario_creador_bk).id

    fecha_prog = _parse_date("fecha_programada", p.get("fecha_programada"))
    hora_prog = _parse_time_opt(p.get("hora_programada"))
    estado = p.get("estado")
    if not estado:
        raise SaludProcessingError("estado es obligatorio en visita_upsert")

    fecha_inicio = None
    if p.get("fecha_inicio_real") is not None:
        fecha_inicio = _parse_dt("fecha_inicio_real", p.get("fecha_inicio_real"))
    fecha_fin = None
    if p.get("fecha_fin_real") is not None:
        fecha_fin = _parse_dt("fecha_fin_real", p.get("fecha_fin_real"))

    completada = int(p.get("completada", 0))
    puntual = int(p.get("puntual", 0))
    duracion_minutos, retraso_minutos = _calc_duracion_retraso(hora_prog, fecha_inicio, fecha_fin)

    row = db.query(FactVisitas).filter(FactVisitas.visita_id == visita_bk).first()
    now = datetime.utcnow()
    if row:
        row.paciente_dim_id = paciente_dim.id
        row.profesional_dim_id = prof_dim.id
        row.zona_dim_id = zona_dim.id if zona_dim else None
        row.usuario_creador_dim_id = usuario_creador_dim_id
        row.fecha_programada = fecha_prog
        row.hora_programada = hora_prog
        row.fecha_inicio_real = fecha_inicio
        row.fecha_fin_real = fecha_fin
        row.estado = estado[:30]
        row.completada = completada
        row.puntual = puntual
        row.duracion_minutos = duracion_minutos
        row.retraso_minutos = retraso_minutos
        row.updated_at = now
        return row

    row = FactVisitas(
        visita_id=visita_bk,
        paciente_dim_id=paciente_dim.id,
        profesional_dim_id=prof_dim.id,
        zona_dim_id=zona_dim.id if zona_dim else None,
        usuario_creador_dim_id=usuario_creador_dim_id,
        fecha_programada=fecha_prog,
        hora_programada=hora_prog,
        fecha_inicio_real=fecha_inicio,
        fecha_fin_real=fecha_fin,
        estado=estado[:30],
        completada=completada,
        puntual=puntual,
        duracion_minutos=duracion_minutos,
        retraso_minutos=retraso_minutos,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_visita_inicio(db: Session, p: Dict[str, Any]) -> FactVisitas:
    visita_bk = _uuid("visita_id", p.get("visita_id"))
    row = db.query(FactVisitas).filter(FactVisitas.visita_id == visita_bk).first()
    if not row:
        raise SaludProcessingError("visita no existe; envíe visita_upsert primero")
    fecha_inicio = _parse_dt("fecha_inicio_real", p.get("fecha_inicio_real"))
    row.fecha_inicio_real = fecha_inicio
    row.duracion_minutos, row.retraso_minutos = _calc_duracion_retraso(
        row.hora_programada, row.fecha_inicio_real, row.fecha_fin_real
    )
    row.updated_at = datetime.utcnow()
    return row


def _handle_visita_fin(db: Session, p: Dict[str, Any]) -> FactVisitas:
    visita_bk = _uuid("visita_id", p.get("visita_id"))
    row = db.query(FactVisitas).filter(FactVisitas.visita_id == visita_bk).first()
    if not row:
        raise SaludProcessingError("visita no existe; envíe visita_upsert primero")
    fecha_fin = _parse_dt("fecha_fin_real", p.get("fecha_fin_real"))
    row.fecha_fin_real = fecha_fin
    if p.get("completada") is not None:
        row.completada = int(p["completada"])
    if p.get("puntual") is not None:
        row.puntual = int(p["puntual"])
    if p.get("estado"):
        row.estado = str(p["estado"])[:30]
    row.duracion_minutos, row.retraso_minutos = _calc_duracion_retraso(
        row.hora_programada, row.fecha_inicio_real, row.fecha_fin_real
    )
    row.updated_at = datetime.utcnow()
    return row


def _handle_alerta_upsert(db: Session, p: Dict[str, Any]) -> FactAlertas:
    aid = _uuid("alerta_id", p.get("alerta_id"))
    paciente_dim = _get_dim_paciente_actual(db, _uuid("paciente_id", p.get("paciente_id")))
    tipo = p.get("tipo")
    if not tipo:
        raise SaludProcessingError("tipo es obligatorio en alerta_upsert")
    prioridad = p.get("prioridad") or "MEDIUM"
    estado = p.get("estado") or "OPEN"

    visita_dim_id = None
    if p.get("visita_id"):
        fv = db.query(FactVisitas).filter(FactVisitas.visita_id == _uuid("visita_id", p.get("visita_id"))).first()
        if fv:
            visita_dim_id = fv.id

    row = db.query(FactAlertas).filter(FactAlertas.alerta_id == aid).first()
    now = datetime.utcnow()
    if row:
        row.paciente_dim_id = paciente_dim.id
        row.visita_dim_id = visita_dim_id
        row.tipo = tipo[:50]
        if p.get("mensaje") is not None:
            row.mensaje = str(p.get("mensaje"))[:500]
        row.prioridad = prioridad[:20]
        row.estado = estado[:20]
        row.dias_abierta = p.get("dias_abierta")
        row.updated_at = now
        return row

    msg = p.get("mensaje")
    if msg is not None:
        msg = str(msg)[:500]

    row = FactAlertas(
        alerta_id=aid,
        paciente_dim_id=paciente_dim.id,
        visita_dim_id=visita_dim_id,
        tipo=tipo[:50],
        mensaje=msg,
        prioridad=prioridad[:20],
        estado=estado[:20],
        dias_abierta=p.get("dias_abierta"),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _handle_ficha_upsert(db: Session, p: Dict[str, Any]) -> FactFichasClinicas:
    fid = _uuid("ficha_id", p.get("ficha_id"))
    visita_bk = _uuid("visita_id", p.get("visita_id"))
    fv = db.query(FactVisitas).filter(FactVisitas.visita_id == visita_bk).first()
    if not fv:
        raise SaludProcessingError("visita no existe; envíe visita_upsert antes de ficha_upsert")

    estado = p.get("estado")
    if not estado:
        raise SaludProcessingError("estado es obligatorio en ficha_upsert (ej. DRAFT, COMPLETED)")

    creador_dim = None
    if p.get("usuario_creador_id"):
        creador_dim = _get_dim_usuario_actual(db, _uuid("usuario_creador_id", p.get("usuario_creador_id"))).id
    actualizador_dim = None
    if p.get("usuario_actualizador_id"):
        actualizador_dim = _get_dim_usuario_actual(
            db, _uuid("usuario_actualizador_id", p.get("usuario_actualizador_id"))
        ).id

    contenido = p.get("contenido")
    tiene_adj = str(p.get("tiene_adjuntos", "0"))[:1]
    cant_adj = str(p.get("cantidad_adjuntos", "0"))[:10]

    row = db.query(FactFichasClinicas).filter(FactFichasClinicas.ficha_id == fid).first()
    now = datetime.utcnow()
    if row:
        row.visita_dim_id = fv.id
        row.estado = estado[:30]
        row.contenido = contenido
        row.usuario_creador_dim_id = creador_dim or row.usuario_creador_dim_id
        row.usuario_actualizador_dim_id = actualizador_dim
        row.tiene_adjuntos = tiene_adj
        row.cantidad_adjuntos = cant_adj
        row.updated_at = now
        return row

    row = FactFichasClinicas(
        ficha_id=fid,
        visita_dim_id=fv.id,
        usuario_creador_dim_id=creador_dim,
        usuario_actualizador_dim_id=actualizador_dim,
        estado=estado[:30],
        contenido=contenido,
        tiene_adjuntos=tiene_adj,
        cantidad_adjuntos=cant_adj,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


_HANDLERS: Dict[str, Callable[[Session, Dict[str, Any]], Any]] = {
    "usuario_upsert": _handle_usuario_upsert,
    "paciente_upsert": _handle_paciente_upsert,
    "profesional_upsert": _handle_profesional_upsert,
    "zona_upsert": _handle_zona_upsert,
    "especialidad_upsert": _handle_especialidad_upsert,
    "visita_upsert": _handle_visita_upsert,
    "visita_inicio": _handle_visita_inicio,
    "visita_fin": _handle_visita_fin,
    "alerta_upsert": _handle_alerta_upsert,
    "ficha_upsert": _handle_ficha_upsert,
}


def process_salud_event(db: Session, raw_event: RawEvent):
    if raw_event.source != "salud":
        raise SaludProcessingError(f'se esperaba source="salud", recibido {raw_event.source!r}')

    handler = _HANDLERS.get(raw_event.event_type or "")
    if not handler:
        raise SaludProcessingError(f"event_type no soportado en salud: {raw_event.event_type!r}")

    payload = raw_event.payload or {}
    return handler(db, payload)
