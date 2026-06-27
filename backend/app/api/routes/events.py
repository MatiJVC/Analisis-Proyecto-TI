import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
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
from app.etl.processors.notification_processor import process_notification_event
from app.api.rate_limit import require_rate_limit

logger = logging.getLogger(__name__)

# Maximum number of failed ETL attempts before an event is permanently dead-lettered.
MAX_ETL_RETRIES = 5

# Rows that are processed=TRUE or failed=TRUE older than this are deleted daily.
# Only terminal rows are eligible — pending rows (processed=FALSE, failed=FALSE)
# are never removed regardless of age.
RAW_EVENTS_RETENTION_DAYS = int(os.getenv("RAW_EVENTS_RETENTION_DAYS", "30"))

# Idempotent DDL applied at startup to add retry tracking columns to fact_raw_events.
# The old ETL partial index (processed, source) is replaced with one that also
# excludes permanently-failed events so retry queries stay fast.
ETL_RETRY_DDL = """
ALTER TABLE fact_raw_events
    ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE fact_raw_events
    ADD COLUMN IF NOT EXISTS failed BOOLEAN NOT NULL DEFAULT FALSE;
DROP INDEX IF EXISTS idx_fre_processed_source;
CREATE INDEX IF NOT EXISTS idx_fre_pending
    ON fact_raw_events (processed, failed, ingested_at)
    WHERE processed = FALSE AND failed = FALSE
"""

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


def retry_stale_events() -> None:
    """Reintenta el ETL para eventos stuck en processed=False por más de 5 minutos.

    Excluye eventos marcados como failed=True (límite de reintentos alcanzado).
    Usa SELECT FOR UPDATE SKIP LOCKED para que múltiples workers no seleccionen
    el mismo lote simultáneamente. Los locks se liberan con commit() antes de
    llamar a _run_etl, que abre su propia sesión con FOR UPDATE NOWAIT para
    garantizar que sólo un worker procese cada evento individual.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
    db: Session = SessionLocal()
    try:
        stale = (
            db.query(RawEvent)
            .filter(
                RawEvent.processed == False,
                RawEvent.failed == False,
                RawEvent.ingested_at < cutoff,
            )
            .with_for_update(skip_locked=True)
            .limit(25)
            .all()
        )
        # Snapshot IDs before committing — releasing the row locks so that
        # _run_etl (which opens its own session) can acquire FOR UPDATE NOWAIT
        # without deadlocking against this transaction.
        stale_ids = [(e.event_id, e.source) for e in stale]
        db.commit()

        if stale_ids:
            logger.info("retry_stale_events: %d eventos pendientes encontrados", len(stale_ids))
        for event_id, source in stale_ids:
            if source in _ETL_PROCESSORS:
                _run_etl(event_id, source)
    except Exception:
        logger.exception("retry_stale_events: error consultando eventos pendientes")
        db.rollback()
    finally:
        db.close()


def purge_stale_raw_events(retention_days: int = RAW_EVENTS_RETENTION_DAYS) -> None:
    """Deletes terminal raw events older than retention_days to bound table growth.

    Only rows that are processed=TRUE (already promoted to Silver/Gold) or
    failed=TRUE (dead-lettered, no further ETL action possible) are eligible.
    Pending rows (processed=FALSE, failed=FALSE) are never deleted.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=retention_days)
    db: Session = SessionLocal()
    try:
        result = db.execute(
            text(
                "DELETE FROM fact_raw_events"
                " WHERE ingested_at < :cutoff"
                "   AND (processed = TRUE OR failed = TRUE)"
            ),
            {"cutoff": cutoff},
        )
        db.commit()
        deleted = result.rowcount
        if deleted:
            logger.info(
                "purge_stale_raw_events: %d filas eliminadas (retención %d días)",
                deleted, retention_days,
            )
    except Exception:
        db.rollback()
        logger.exception("purge_stale_raw_events: error al purgar fact_raw_events")
    finally:
        db.close()


def _run_etl(event_id: uuid.UUID, source: str) -> None:
    """Corre después de enviar el 202. Usa sesión DB propia para aislamiento.

    Adquiere FOR UPDATE NOWAIT sobre la fila antes de procesar para garantizar
    que sólo un worker (background task o retry) ejecute el ETL de un evento.
    Si la fila ya está bloqueada por otro worker, OperationalError se captura y
    se retorna sin procesar — el otro worker lo está manejando.
    """
    processor = _ETL_PROCESSORS.get(source)
    if processor is None:
        return  # sólo alcanzable para eventos históricos escritos antes de la validación de source

    db: Session = SessionLocal()
    try:
        try:
            raw_event = (
                db.query(RawEvent)
                .filter(RawEvent.event_id == event_id)
                .with_for_update(nowait=True)
                .first()
            )
        except OperationalError:
            # Another worker holds the row lock — skip, it will handle this event.
            db.rollback()
            logger.debug(
                "ETL %s event_id=%s — saltado, otra instancia lo está procesando", source, event_id
            )
            return

        if not raw_event or raw_event.processed or raw_event.failed:
            return

        processor(db, raw_event)
        raw_event.processed = True
        db.commit()
        logger.info("ETL %s/%s OK — event_id=%s", source, raw_event.event_type, event_id)
    except Exception:
        db.rollback()
        logger.exception("ETL %s event_id=%s falló", source, event_id)
        # Increment retry_count in a fresh transaction; mark as failed if cap reached.
        try:
            raw_event = db.query(RawEvent).filter(RawEvent.event_id == event_id).first()
            if raw_event:
                raw_event.retry_count += 1
                if raw_event.retry_count >= MAX_ETL_RETRIES:
                    raw_event.failed = True
                    logger.critical(
                        "ETL %s event_id=%s dead-lettered después de %d intentos — "
                        "revisar payload en fact_raw_events",
                        source, event_id, raw_event.retry_count,
                    )
                db.commit()
        except Exception:
            db.rollback()
            logger.exception(
                "ETL %s event_id=%s — no se pudo actualizar retry_count", source, event_id
            )
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
        "Fuentes válidas: orders, subscriptions, salud, incidents, crm, inventory, payments, iot, notifications. "
        "Cualquier otro valor retorna 422 inmediatamente. "
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