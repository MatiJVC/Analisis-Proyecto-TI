from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import EventCreate, EventCreateResponse
from app.services import create_event
from app.etl.processors.order_processor import process_order_event
from app.etl.processors.subscription_processor import process_subscription_event
from app.etl.processors.salud_processor import process_salud_event
from app.etl.processors.incident_processor import process_incident_event
from app.etl.processors.iot_processor import process_iot_event
from app.etl.processors.notification_proccessor import process_notification_event

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
    description="Recibe un evento (data lake: raw_events). Procesa automáticamente orders, subscriptions, salud e incidents hacia el warehouse cuando aplica."
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

        elif db_event.source == "incidents":
            try:
                process_incident_event(db, db_event)
                db_event.processed = True
                db.commit()
                print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (incidents) procesado automáticamente")
            except Exception as etl_error:
                db.rollback()
                print(f"⚠️  [AUTO-ETL-INCIDENTS] Error: {str(etl_error)}")

        elif db_event.source == "iot_devices":
            try:
                process_iot_event(db, db_event)
                db_event.processed = True
                db.commit()
                print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (iot_devices) procesado automáticamente")
            except Exception as etl_error:
                db.rollback()
                print(f"⚠️  [AUTO-ETL-IoT] Error: {str(etl_error)}")
        elif db_event.source == "notifications":
            try:
                process_notification_event(db, db_event)
                db_event.processed = True
                db.commit()
                print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (notifications) procesado automáticamente")
            except Exception as etl_error:
                db.rollback()
                print(f"⚠️  [AUTO-ETL-NOTIFICATIONS] Error: {str(etl_error)}")

        return EventCreateResponse(
            message="event stored",
            event_id=db_event.id,  # ty:ignore[invalid-argument-type]
            source=db_event.source,  # ty:ignore[invalid-argument-type]
            event_type=db_event.event_type  # ty:ignore[invalid-argument-type]
        ) 
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el evento: {str(e)}"
        )
