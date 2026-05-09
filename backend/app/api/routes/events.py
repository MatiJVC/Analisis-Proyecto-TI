from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import EventCreate, EventCreateResponse
from app.services import create_event


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
    description="Recibe un evento de cualquier dominio y lo almacena en raw_events para procesamiento posterior"
)
async def create_event_endpoint(
    event: EventCreate,
    db: Session = Depends(get_db)
) -> EventCreateResponse:

    try:
        db_event = create_event(db=db, event=event)
        
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
