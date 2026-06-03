from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import RawEvent, FactNotifications


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


def process_notification_event(
    db: Session, raw_event: RawEvent
) -> Optional[FactNotifications]:
    """
    Procesa un evento de notificación y lo convierte en FactNotifications.

    Soporta eventos:
    - notificacion_enviada:   Crea el registro con estado 'enviado'
    - notificacion_entregada: Actualiza estado a 'entregado' y registra fecha_entrega
    - fallback_activado:      Cambia canal, activa flag, incrementa intentos
    - notificacion_fallida:   Actualiza estado a 'fallido', incrementa intentos
    """

    try:
        payload = raw_event.payload

        # 1. Validar payload mínimo
        _validate_notification_payload(payload, raw_event.event_type)

        # 2. Extraer solo id_notificacion para el lookup
        id_notificacion = payload["id_notificacion"]

        # 3. Buscar registro existente
        fact = db.query(FactNotifications).filter(
            FactNotifications.id_notificacion == id_notificacion
        ).first()

        # 4. Lógica por event_type
        if raw_event.event_type == "notificacion_enviada":
            # Siempre crea un registro nuevo (es el primer evento del ciclo)
            if fact:
                # Si por alguna razón ya existe, actualizar en vez de duplicar
                print(f"[Notifications-ETL] Notificación {id_notificacion} ya existe, actualizando")
            else:
                fact = FactNotifications(
                    id_notificacion=id_notificacion,
                    created_at=datetime.utcnow(),
                )
                db.add(fact)
                print(f"[Notifications-ETL] Creando notificación {id_notificacion}")

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
            if not fact:
                raise NotificationPayloadValidationError(
                    f"No existe notificación {id_notificacion} para marcar como entregada"
                )
            fact.estado        = "entregado"
            fact.fecha_entrega = _parse_timestamp(payload.get("timestamp")) or datetime.utcnow()

        elif raw_event.event_type == "fallback_activado":
            if not fact:
                raise NotificationPayloadValidationError(
                    f"No existe notificación {id_notificacion} para activar fallback"
                )
            fact.canal_original   = fact.canal_usado or payload.get("canal_original")
            fact.canal_usado       = payload["canal_fallback"]
            fact.fallback_activado = True
            fact.intentos          = (fact.intentos or 1) + 1

        elif raw_event.event_type == "notificacion_fallida":
            if not fact:
                raise NotificationPayloadValidationError(
                    f"No existe notificación {id_notificacion} para marcar como fallida"
                )
            fact.estado   = "fallido"
            fact.intentos = payload.get("intentos") or (fact.intentos or 1) + 1

        # 5. Actualizar timestamp
        fact.updated_at = datetime.utcnow()

        db.add(fact)
        db.flush()

        print(f"[Notifications-ETL] Evento '{raw_event.event_type}' procesado para {id_notificacion}")

        return fact

    except NotificationPayloadValidationError as e:
        print(f"[Notifications-ETL] Error de validación: {str(e)}")
        raise

    except Exception as e:
        print(f"[Notifications-ETL] Error procesando evento {raw_event.id}: {str(e)}")
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
                print(f"[Notifications-ETL] Error procesando evento {raw_event.id}: {str(e)}")
                db.rollback()

        db.commit()

        print(
            f"[Notifications-ETL] Procesamiento completado: "
            f"{stats['processed']}/{stats['total']} eventos"
        )

        return stats

    except Exception as e:
        print(f"[Notifications-ETL] Error en batch processing: {str(e)}")
        db.rollback()
        raise