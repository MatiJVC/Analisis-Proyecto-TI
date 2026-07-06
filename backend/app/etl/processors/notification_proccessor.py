import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import RawEvent, FactNotifications

logger = logging.getLogger(__name__)


class NotificationPayloadValidationError(Exception):
    pass


def _validate_notification_payload(payload: Dict[str, Any], event_type: str) -> None:
    """Valida que el payload tenga los campos mínimos según el tipo de evento."""

    # id_notificacion siempre requerido
    if not payload.get("id_notificacion"):
        raise NotificationPayloadValidationError("Campo requerido faltante: id_notificacion")

    # canal_usado requerido en todos excepto fallback_activado (usa canal_fallback)
    if event_type == "fallback_activado":
        if not payload.get("canal_fallback"):
            raise NotificationPayloadValidationError(
                "fallback_activado requiere: canal_fallback"
            )
        canal = payload.get("canal_fallback")
    else:
        if not payload.get("canal_usado"):
            raise NotificationPayloadValidationError("Campo requerido faltante: canal_usado")
        canal = payload.get("canal_usado")

    canales_validos = ["sms", "email", "push"]
    if canal not in canales_validos:
        raise NotificationPayloadValidationError(
            f"Canal inválido: '{canal}'. Debe ser uno de: {canales_validos}"
        )


def _parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """Parsea timestamp del payload o retorna None."""
    if not timestamp_str:
        return None
    try:
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _get_or_create_notification(
    db: Session, id_notificacion: str, payload: Dict[str, Any], event_type: str
) -> FactNotifications:
    """Busca o crea una notificación en fact_notifications con valores por defecto."""
    fact = db.query(FactNotifications).filter(
        FactNotifications.id_notificacion == id_notificacion
    ).first()

    if not fact:
        if event_type == "fallback_activado":
            canal_original = payload.get("canal_original") or "sms"
            canal_usado = payload["canal_fallback"]
        else:
            canal_original = payload.get("canal_usado") or "sms"
            canal_usado = payload.get("canal_usado") or "sms"

        fact = FactNotifications(
            id_notificacion=id_notificacion,
            canal_original=canal_original,
            canal_usado=canal_usado,
            estado="enviado",
            intentos=payload.get("intentos", 1),
            fallback_activado=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        db.add(fact)
        logger.info(
            "Notifications-ETL creando notificación inexistente %s desde evento %s",
            id_notificacion,
            event_type,
        )
    return fact


def process_notification_event(
    db: Session, raw_event: RawEvent
) -> Optional[FactNotifications]:
    """
    Procesa un evento de notificación y lo convierte en FactNotifications.

    Soporta eventos:
    - notificacion_enviada:   Crea o actualiza el registro con estado 'enviado'
    - notificacion_entregada: Actualiza estado a 'entregado' y registra fecha_entrega
    - fallback_activado:      Cambia canal, activa flag, incrementa intentos
    - notificacion_fallida:   Actualiza estado a 'fallido', incrementa intentos
    """

    try:
        payload = raw_event.payload or {}

        # 1. Validar payload mínimo
        _validate_notification_payload(payload, raw_event.event_type)

        # 2. Extraer solo id_notificacion para el lookup
        id_notificacion = payload["id_notificacion"]

        # 3. Buscar o crear registro existente
        fact = _get_or_create_notification(db, id_notificacion, payload, raw_event.event_type)

        # 4. Lógica por event_type
        if raw_event.event_type == "notificacion_enviada":
            fact.id_api_key            = payload.get("id_api_key")
            fact.canal_usado         = payload.get("canal_usado")
            fact.canal_original      = payload.get("canal_usado")
            fact.destinatario_email    = payload.get("destinatario_email")
            fact.destinatario_telefono = payload.get("destinatario_telefono")
            fact.mensaje_asunto        = payload.get("mensaje_asunto")
            fact.mensaje_email         = payload.get("mensaje_email")
            fact.mensaje_sms           = payload.get("mensaje_sms")
            fact.estado                = "enviado"
            fact.intentos              = payload.get("intentos", 1)
            fact.fallback_activado     = False

        elif raw_event.event_type == "notificacion_entregada":
            fact.estado        = "entregado"
            fact.fecha_entrega = _parse_timestamp(payload.get("timestamp")) or datetime.now(tz=timezone.utc)

        elif raw_event.event_type == "fallback_activado":
            fact.canal_original   = fact.canal_original or fact.canal_usado or payload.get("canal_original") or "sms"
            fact.canal_usado       = payload["canal_fallback"]
            fact.fallback_activado = True
            fact.intentos          = (fact.intentos or 1) + 1

        elif raw_event.event_type == "notificacion_fallida":
            fact.estado   = "fallido"
            fact.intentos = payload.get("intentos") or (fact.intentos or 1) + 1

        # 5. Actualizar timestamp
        fact.updated_at = datetime.now(tz=timezone.utc)

        db.add(fact)
        db.flush()

        logger.info("Notifications-ETL evento '%s' procesado para %s", raw_event.event_type, id_notificacion)

        return fact

    except NotificationPayloadValidationError as e:
        logger.warning("Notifications-ETL error de validación: %s", e)
        raise

    except Exception as e:
        logger.exception("Notifications-ETL error procesando evento %s", raw_event.event_id)
        raise


def process_notification_events(db: Session, limit: int = 1000) -> Dict[str, Any]:
    """
    Procesa todos los eventos de notificaciones sin procesar.
    Retorna estadísticas del procesamiento.
    """

    stats: Dict[str, Any] = {
        "total": 0,
        "processed": 0,
        "errors": 0,
        "event_types": {},
    }

    try:
        unprocessed = (
            db.query(RawEvent)
            .filter(
                RawEvent.source    == "notifications",
                RawEvent.processed == False,
            )
            .limit(limit)
            .all()
        )

        stats["total"] = len(unprocessed)

        for raw_event in unprocessed:
            try:
                process_notification_event(db, raw_event)

                raw_event.processed = True
                db.add(raw_event)

                stats["processed"] += 1
                event_type = raw_event.event_type
                stats["event_types"][event_type] = (
                    stats["event_types"].get(event_type, 0) + 1
                )

            except Exception as e:
                stats["errors"] += 1
                logger.exception("Notifications-ETL error procesando evento %s", raw_event.event_id)
                db.rollback()

        db.commit()

        logger.info(
            "Notifications-ETL procesamiento completado: %s/%s eventos",
            stats['processed'], stats['total'],
        )

        return stats

    except Exception as e:
        logger.exception("Notifications-ETL error en batch processing")
        db.rollback()
        raise