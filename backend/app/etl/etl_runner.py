from datetime import datetime
from typing import Callable, Tuple, Type

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.services import get_unprocessed_events, mark_event_as_processed
from app.etl.processors import (
    process_subscription_event,
    PayloadValidationError,
    process_incident_event,
    IncidentProcessingError,
)
from app.models.raw import RawEvent


class ETLExecutionError(Exception):
    pass


def _process_pipeline(
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
            mark_event_as_processed(db, raw_event.id)
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

    # Commit intermedio para no contaminar otros pipelines ante fallo parcial
    if dry_run:
        db.rollback()
    else:
        db.commit()


def run_etl(db: Session, dry_run: bool = False) -> dict:
    start_time = datetime.utcnow()
    stats = {
        "start_time": start_time,
        "total_events": 0,
        "successful": 0,
        "failed": 0,
        "errors": [],
    }

    try:
        _process_pipeline(
            db,
            source="subscriptions",
            process_fn=process_subscription_event,
            validation_errors=(PayloadValidationError,),
            stats=stats,
            dry_run=dry_run,
        )
        _process_pipeline(
            db,
            source="incidentes",
            process_fn=process_incident_event,
            validation_errors=(IncidentProcessingError,),
            stats=stats,
            dry_run=dry_run,
        )

        stats["end_time"] = datetime.utcnow()
        stats["duration_seconds"] = (stats["end_time"] - start_time).total_seconds()

        if stats["errors"]:
            for error in stats["errors"]:
                print(f"   - {error}")

        print("=" * 70 + "\n")

        return stats

    except Exception as e:
        db.rollback()
        raise ETLExecutionError(f"ETL execution failed: {str(e)}")


def run_etl_dry_run(db: Session) -> dict:
    return run_etl(db, dry_run=True)
