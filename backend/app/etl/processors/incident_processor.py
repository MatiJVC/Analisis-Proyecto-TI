from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import FactIncident, RawEvent

VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_STATUSES = {"open", "investigating", "resolved"}


class IncidentProcessingError(Exception):
    pass


def _parse_datetime(value: Any) -> Optional[datetime]:
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


def _validate_base_payload(payload: Dict[str, Any]) -> str:
    incident_id = payload.get("incident_id")
    if not incident_id:
        raise IncidentProcessingError("Campo requerido faltante: incident_id")
    return str(incident_id)


def _get_or_create_incident(db: Session, incident_id: str, payload: Dict[str, Any]) -> FactIncident:
    existing = (
        db.query(FactIncident)
        .filter(FactIncident.incident_id == incident_id)
        .first()
    )
    if existing:
        return existing

    opened_at = _parse_datetime(payload.get("opened_at")) or datetime.now(tz=timezone.utc)
    return FactIncident(
        incident_id=incident_id,
        title=payload.get("title") or f"Incident {incident_id}",
        severity=payload.get("severity") or "medium",
        status=payload.get("status") or "open",
        assignee=payload.get("assignee"),
        opened_at=opened_at,
        updated_at=datetime.now(tz=timezone.utc),
        created_at=datetime.now(tz=timezone.utc),
    )


def _apply_common_fields(fact: FactIncident, payload: Dict[str, Any]) -> None:
    if payload.get("title"):
        fact.title = payload["title"]
    if payload.get("severity") in VALID_SEVERITIES:
        fact.severity = payload["severity"]
    if payload.get("status") in VALID_STATUSES:
        fact.status = payload["status"]
    if "assignee" in payload:
        fact.assignee = payload.get("assignee")
    fact.updated_at = datetime.now(tz=timezone.utc)


def _handle_incident_created(db: Session, raw_event: RawEvent) -> FactIncident:
    payload = raw_event.payload or {}
    incident_id = _validate_base_payload(payload)
    fact = _get_or_create_incident(db, incident_id, payload)
    _apply_common_fields(fact, payload)
    opened_at = _parse_datetime(payload.get("opened_at"))
    if opened_at:
        fact.opened_at = opened_at
    db.add(fact)
    db.flush()
    return fact


def _handle_incident_assigned(db: Session, raw_event: RawEvent) -> FactIncident:
    payload = raw_event.payload or {}
    incident_id = _validate_base_payload(payload)
    fact = _get_or_create_incident(db, incident_id, payload)
    fact.assignee = payload.get("assignee")
    fact.updated_at = datetime.now(tz=timezone.utc)
    db.add(fact)
    db.flush()
    return fact


def _handle_incident_status_changed(db: Session, raw_event: RawEvent) -> FactIncident:
    payload = raw_event.payload or {}
    incident_id = _validate_base_payload(payload)
    fact = _get_or_create_incident(db, incident_id, payload)
    _apply_common_fields(fact, payload)
    db.add(fact)
    db.flush()
    return fact


def _handle_incident_resolved(db: Session, raw_event: RawEvent) -> FactIncident:
    payload = raw_event.payload or {}
    incident_id = _validate_base_payload(payload)
    fact = _get_or_create_incident(db, incident_id, payload)
    _apply_common_fields(fact, payload)

    fact.status = "resolved"
    resolved_at = _parse_datetime(payload.get("resolved_at")) or datetime.now(tz=timezone.utc)
    fact.resolved_at = resolved_at

    if payload.get("resolution_time_hours") is not None:
        fact.resolution_time_hours = float(payload["resolution_time_hours"])
    elif fact.opened_at:
        delta = resolved_at - fact.opened_at
        fact.resolution_time_hours = round(delta.total_seconds() / 3600, 2)

    if "sla_met" in payload:
        fact.sla_met = bool(payload["sla_met"])

    fact.updated_at = datetime.now(tz=timezone.utc)
    db.add(fact)
    db.flush()
    return fact


_HANDLERS = {
    "incident_created": _handle_incident_created,
    "incident_upsert": _handle_incident_created,
    "incident_assigned": _handle_incident_assigned,
    "incident_status_changed": _handle_incident_status_changed,
    "incident_resolved": _handle_incident_resolved,
}


def process_incident_event(db: Session, raw_event: RawEvent) -> Optional[FactIncident]:
    try:
        handler = _HANDLERS.get(raw_event.event_type)
        if not handler:
            raise IncidentProcessingError(
                f"event_type no soportado para incidents: {raw_event.event_type}"
            )
        return handler(db, raw_event)
    except IncidentProcessingError:
        raise
    except SQLAlchemyError:
        raise
    except Exception as e:
        raise IncidentProcessingError(str(e)) from e
