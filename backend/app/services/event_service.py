from sqlalchemy.orm import Session
from app.models import RawEvent
from app.schemas import EventCreate


def create_event(db: Session, event: EventCreate) -> RawEvent:
    db_event = RawEvent(
        source=event.source,
        event_type=event.event_type,
        payload=event.payload,
        processed=False
    )
    
    db.add(db_event)
    
    db.commit()
    
    db.refresh(db_event)
    
    return db_event


def get_event_by_id(db: Session, event_id: int) -> RawEvent | None:
    return db.query(RawEvent).filter(RawEvent.id == event_id).first()


def get_unprocessed_events(db: Session, source: str | None = None, limit: int = 100) -> list[RawEvent]:

    query = db.query(RawEvent).filter(RawEvent.processed == False)
    
    if source:
        query = query.filter(RawEvent.source == source)
    
    return query.limit(limit).all()


def mark_event_as_processed(db: Session, event_id: int) -> bool:

    event = db.query(RawEvent).filter(RawEvent.id == event_id).first()
    
    if not event:
        return False
    
    event.processed = True
    db.commit()
     
    return True
