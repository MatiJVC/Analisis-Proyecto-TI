from sqlalchemy.orm import Session

from app.services.incidents_analytics_service import (
    get_incidents_kpis,
    get_incidents_list,
    get_incidents_timeline,
)


def get_incident_kpis_summary(db: Session) -> dict:
    return get_incidents_kpis(db)


def get_incident_timeline(db: Session, days: int = 14) -> list:
    return get_incidents_timeline(db, days=days)


def get_incident_list(db: Session, limit: int = 50) -> list:
    return get_incidents_list(db, limit=limit)
