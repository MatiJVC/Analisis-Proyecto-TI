from datetime import datetime
from typing import Callable, Tuple, Type

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.etl.processors import (
    PayloadValidationError,
    SaludProcessingError,
    process_salud_event,
    process_subscription_event,
)
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
        _process_source_pipeline(
            db,
            source="subscriptions",
            process_fn=process_subscription_event,
            validation_errors=(PayloadValidationError,),
            stats=stats,
            dry_run=dry_run,
        )
        _process_source_pipeline(
            db,
            source="salud",
            process_fn=process_salud_event,
            validation_errors=(SaludProcessingError,),
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
