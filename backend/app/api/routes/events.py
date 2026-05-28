from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import EventCreate, EventCreateResponse
from app.schemas.inventory_event_schema import InventoryEventCreate
from app.services import create_event
from app.etl.processors.order_processor import process_order_event
from app.etl.processors.subscription_processor import process_subscription_event
from app.etl.processors.salud_processor import process_salud_event
from app.etl.processors.incident_processor import process_incident_event


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

        elif db_event.source == "inventory":
            # Procesamiento ETL del módulo de Inventario — integración pendiente con Grupo 5
            db_event.processed = True
            db.commit()
            print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (inventory) almacenado correctamente")

        elif db_event.source == "incidents":
            try:
                process_incident_event(db, db_event)
                db_event.processed = True
                db.commit()
                print(f" [AUTO-ETL] Evento {db_event.event_type} (incidents) procesado automáticamente")
            except Exception as etl_error:
                db.rollback()
                print(f"  [AUTO-ETL-INCIDENTS] Error: {str(etl_error)}")

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
