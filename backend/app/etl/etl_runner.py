from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.services import get_unprocessed_events, mark_event_as_processed
from app.etl.processors import process_subscription_event, PayloadValidationError


class ETLExecutionError(Exception):
    pass


def run_etl(db: Session, dry_run: bool = False) -> dict:
    start_time = datetime.utcnow()
    stats = {
        "start_time": start_time,
        "total_events": 0,
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    try:
        # 1. Obtener eventos sin procesar de subscriptions
        unprocessed_events = get_unprocessed_events(
            db=db,
            source="subscriptions",
            limit=1000
        )
        
        stats["total_events"] = len(unprocessed_events)
        
        if not unprocessed_events:
            stats["end_time"] = datetime.utcnow()
            stats["duration_seconds"] = (stats["end_time"] - start_time).total_seconds()
            return stats
        
        # 2. Procesar cada evento
        for idx, raw_event in enumerate(unprocessed_events, 1):
            try:
                # Procesar evento de suscripción
                process_subscription_event(db, raw_event)
                
                # Marcar como procesado
                mark_event_as_processed(db, raw_event.id)
                stats["successful"] += 1
                
            
            except PayloadValidationError as e:
                error_msg = f"Event {raw_event.id}: {str(e)}"
                stats["failed"] += 1
                stats["errors"].append(error_msg)
            
            except SQLAlchemyError as e:
                error_msg = f"Event {raw_event.id}: BD error - {str(e)}"
                stats["failed"] += 1
                stats["errors"].append(error_msg)
            
            except Exception as e:
                error_msg = f"Event {raw_event.id}: {str(e)}"
                stats["failed"] += 1
                stats["errors"].append(error_msg)
        
        # 3. Commit final (si no es dry_run)
        if not dry_run:
            db.commit()
        else:
            db.rollback()
        
        stats["end_time"] = datetime.utcnow()
        stats["duration_seconds"] = (stats["end_time"] - start_time).total_seconds()
        
        if stats["errors"]:
            for error in stats["errors"]:
                print(f"   - {error}")
        
        print("="*70 + "\n")
        
        return stats
    
    except Exception as e:
        db.rollback()
        raise ETLExecutionError(f"ETL execution failed: {str(e)}")


def run_etl_dry_run(db: Session) -> dict:
    return run_etl(db, dry_run=True)
