import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.session import SessionLocal
from app.models.raw.raw_events import RawEvent
from app.schemas import EventCreate, AcknowledgeResponse
from app.services import create_event
from app.etl.processors.order_processor import process_order_event
from app.etl.processors.subscription_processor import process_subscription_event
from app.etl.processors.salud_processor import process_salud_event
from app.etl.processors.incident_processor import process_incident_event


router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={
        400: {"description": "Payload JSON inválido o campos requeridos faltantes"},
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
        print(f"[ETL] {source}/{raw_event.event_type} OK — event_id={event_id}")
    except Exception as exc:
        db.rollback()
        print(f"[ETL-ERROR] {source} event_id={event_id}: {exc}")
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
) -> AcknowledgeResponse:
    # Metadatos de auditoría — generados por el servidor, nunca del cliente
    event_id = uuid.uuid4()
    ingested_at = datetime.now(tz=timezone.utc)

    try:
        db_event = create_event(db=db, event=event, event_id=event_id, ingested_at=ingested_at)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al persistir el evento: {exc}",
        )

    # ETL en background — la conexión del cliente ya está liberada cuando corre
    background_tasks.add_task(_run_etl, event_id=db_event.event_id, source=db_event.source)

    return AcknowledgeResponse(status="acknowledged", event_id=event_id)
