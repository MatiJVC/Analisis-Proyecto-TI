from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import EventCreate, EventCreateResponse
from app.services import create_event
from app.etl.processors.order_processor import process_order_event
from app.etl.processors.subscription_processor import process_subscription_event
from app.etl.processors.salud_processor import process_salud_event


router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={
        400: {"description": "Invalid event data"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "",
    response_model=EventCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo evento",
    description="Recibe un evento (data lake: raw_events). Procesa automáticamente orders, subscriptions y salud hacia el warehouse cuando aplica."
)
async def create_event_endpoint(
    event: EventCreate,
    db: Session = Depends(get_db)
) -> EventCreateResponse:

    try:
        # 1. Guardar evento en raw_events
        db_event = create_event(db=db, event=event)
        
        # 2. Procesar automáticamente según el dominio
        if db_event.source == "orders":
            try:
                process_order_event(db, db_event)
                db.commit()
                print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (orders) procesado automáticamente")
            except Exception as etl_error:
                print(f"⚠️  [AUTO-ETL-ORDERS] Error: {str(etl_error)}")
        
        elif db_event.source == "subscriptions":
            try:
                process_subscription_event(db, db_event)
                db.commit()
                print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (subscriptions) procesado automáticamente")
            except Exception as etl_error:
                print(f"⚠️  [AUTO-ETL-SUBSCRIPTIONS] Error: {str(etl_error)}")

        elif db_event.source == "salud":
            try:
                process_salud_event(db, db_event)
                db_event.processed = True
                db.commit()
                print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (salud) procesado automáticamente")
            except Exception as etl_error:
                db.rollback()
                print(f"⚠️  [AUTO-ETL-SALUD] Error: {str(etl_error)}")

        return EventCreateResponse(
            message="event stored",
            event_id=db_event.id,
            source=db_event.source,
            event_type=db_event.event_type
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el evento: {str(e)}"
        )
