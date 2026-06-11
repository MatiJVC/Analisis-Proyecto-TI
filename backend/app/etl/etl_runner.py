import logging
from datetime import datetime, timezone
from typing import Callable, Tuple, Type

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.etl.processors import (
    CRMProcessingError,
    IncidentProcessingError,
    InventoryProcessingError,
    PayloadValidationError,
    SaludProcessingError,
    process_crm_event,
    process_incident_event,
    process_inventory_event,
    process_salud_event,
    process_subscription_event,
)
from app.etl.processors.iot_processor import process_iot_event
from app.etl.processors.notification_proccessor import process_notification_event
from app.etl.processors.order_processor import process_order_event
from app.etl.processors.payment_processor import process_payment_event
from app.models.raw import RawEvent
from app.services import get_unprocessed_events


class ETLExecutionError(Exception):
    pass


def _process_source_pipeline(
    db: Session,
    *,
    source: str,
    process_fn: Callable[[Session, RawEvent], object],
    validation_errors: Tuple[Type[BaseException], ...],
    stats: dict,
    dry_run: bool,
) -> None:
    unprocessed = get_unprocessed_events(db=db, source=source, limit=1000)
    stats["total_events"] += len(unprocessed)

    for raw_event in unprocessed:
        try:
            process_fn(db, raw_event)
            raw_event.processed = True
            stats["successful"] += 1
        except validation_errors as e:
            stats["failed"] += 1
            stats["errors"].append(f"Event {raw_event.id} [{source}]: {str(e)}")
        except SQLAlchemyError as e:
            stats["failed"] += 1
            stats["errors"].append(f"Event {raw_event.id} [{source}]: BD error - {str(e)}")
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"Event {raw_event.id} [{source}]: {str(e)}")

    if dry_run:
        db.rollback()
    else:
        db.commit()


# Mapa completo de fuentes → (procesador, errores_de_validación)
_SOURCE_PIPELINES: list[tuple[str, Callable, tuple]] = [
    ("subscriptions", process_subscription_event, (PayloadValidationError,)),
    ("salud",         process_salud_event,         (SaludProcessingError,)),
    ("incidents",     process_incident_event,      (IncidentProcessingError,)),
    ("orders",        process_order_event,         (Exception,)),
    ("crm",           process_crm_event,           (CRMProcessingError,)),
    ("inventory",     process_inventory_event,     (InventoryProcessingError,)),
    ("payments",      process_payment_event,       (Exception,)),
    ("iot",           process_iot_event,           (Exception,)),
    ("notifications", process_notification_event,  (Exception,)),
]


def run_etl(db: Session, dry_run: bool = False) -> dict:
    start_time = datetime.now(tz=timezone.utc)
    stats = {
        "start_time": start_time,
        "total_events": 0,
        "successful": 0,
        "failed": 0,
        "errors": [],
    }

    try:
        for source, process_fn, validation_errors in _SOURCE_PIPELINES:
            _process_source_pipeline(
                db,
                source=source,
                process_fn=process_fn,
                validation_errors=validation_errors,
                stats=stats,
                dry_run=dry_run,
            )

        stats["end_time"] = datetime.now(tz=timezone.utc)
        stats["duration_seconds"] = (stats["end_time"] - start_time).total_seconds()

        if stats["errors"]:
            for error in stats["errors"]:
                logger.warning("ETL error: %s", error)

        logger.info(
            "ETL run completado en %.2f s: %s exitosos, %s fallidos de %s eventos",
            stats["duration_seconds"], stats["successful"], stats["failed"], stats["total_events"],
        )

        return stats

    except Exception as e:
        db.rollback()
        raise ETLExecutionError(f"ETL execution failed: {str(e)}")


def run_etl_dry_run(db: Session) -> dict:
    return run_etl(db, dry_run=True)
