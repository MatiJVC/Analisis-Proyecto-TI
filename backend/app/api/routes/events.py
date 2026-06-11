import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import get_current_user, KeycloakUser
from app.db import get_db
from app.db.session import SessionLocal
from app.models.raw.raw_events import RawEvent
from app.schemas import EventCreate, AcknowledgeResponse
from app.schemas.inventory_event_schema import InventoryEventCreate
from app.services import create_event
from app.etl.processors.order_processor import process_order_event
from app.etl.processors.subscription_processor import process_subscription_event
from app.etl.processors.salud_processor import process_salud_event
from app.etl.processors.incident_processor import process_incident_event
from app.etl.processors.crm_processor import process_crm_event
from app.etl.processors.inventory_processor import process_inventory_event
from app.etl.processors.payment_processor import process_payment_event
from app.etl.processors.iot_processor import process_iot_event
from app.etl.processors.notification_proccessor import process_notification_event
from app.api.rate_limit import require_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={
        400: {"description": "Payload JSON inválido o campos requeridos faltantes"},
        401: {"description": "Falta token Bearer o token inválido"},
        500: {"description": "Error interno del servidor"},
    },
)

# ---------------------------------------------------------------------------
# ETL background worker
# Abre su propia sesión DB para desacoplarse del ciclo de vida del request.
# ---------------------------------------------------------------------------

_ETL_PROCESSORS = {
    "orders": process_order_event,
    "subscriptions": process_subscription_event,
    "salud": process_salud_event,
    "incidents": process_incident_event,
    "crm": process_crm_event,
    "inventory": process_inventory_event,
    "payments": process_payment_event,
    "iot": process_iot_event,
    "notifications": process_notification_event,
}


def _run_etl(event_id: uuid.UUID, source: str) -> None:
    """Corre después de enviar el 202. Usa sesión DB propia para aislamiento."""
    processor = _ETL_PROCESSORS.get(source)
    if processor is None:
        return  # fuente sin ETL registrado — se guarda en raw_events igualmente

    db: Session = SessionLocal()
    try:
        raw_event = db.query(RawEvent).filter(RawEvent.event_id == event_id).first()
        if not raw_event:
            return

        processor(db, raw_event)
        raw_event.processed = True
        db.commit()
        logger.info("ETL %s/%s OK — event_id=%s", source, raw_event.event_type, event_id)
    except Exception as exc:
        db.rollback()
        logger.exception("ETL %s event_id=%s", source, event_id)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoint principal
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=AcknowledgeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingestar un evento",
    description=(
        "Valida el JSON de entrada (source, event_type, payload). "
        "Añade event_id (UUID v4) e ingested_at (UTC) generados por el servidor "
        "y persiste en raw_events. "
        "Devuelve 202 Accepted de inmediato; el ETL al warehouse corre en background."
    ),
)
async def ingest_event(
    event: EventCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _user: KeycloakUser = Depends(get_current_user),
    _rl: None = Depends(require_rate_limit),
) -> AcknowledgeResponse:
    event_id = uuid.uuid4()
    ingested_at = datetime.now(tz=timezone.utc)

    # Validación estricta para eventos del módulo de Inventario (Grupo 5)
    if event.source == "inventory":
        try:
            InventoryEventCreate(
                source=event.source,
                event_type=event.event_type,
                payload=event.payload,
            )
        except ValidationError as ve:
            errores = [
                f"• {err['loc'][-1] if err['loc'] else 'payload'}: {err['msg']}"
                for err in ve.errors()
            ]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Evento de inventario con datos inválidos",
                    "event_type": event.event_type,
                    "errores": errores,
                    "ayuda": (
                        "Revise el formato de los campos. UUIDs deben ser v4, "
                        "fechas en ISO 8601 (ej: '2026-05-28T10:00:00Z'), "
                        "y valores numéricos deben ser enteros."
                    ),
                },
            )

    try:
        db_event = create_event(db=db, event=event, event_id=event_id, ingested_at=ingested_at)
    except Exception as exc:
        logger.exception("Error al persistir el evento")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )

    background_tasks.add_task(_run_etl, event_id=db_event.event_id, source=db_event.source)

    return AcknowledgeResponse(status="acknowledged", event_id=event_id)
