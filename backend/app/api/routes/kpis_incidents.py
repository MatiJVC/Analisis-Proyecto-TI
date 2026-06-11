import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
from app.schemas.incidents_kpi_schema import (
    IncidentKPIsResponse,
    IncidentTimelinePoint,
    IncidentRow,
)
from app.services.incidents_analytics_service import (
    get_incidents_kpis,
    get_incidents_list,
    get_incidents_timeline,
)

logger = logging.getLogger(__name__)

INCIDENTS_ROLES = ["admin", "analista", "incidents"]

router = APIRouter(tags=["kpis — incidents"])


@router.get(
    "/incidents/kpis",
    dependencies=[Depends(require_any_role(INCIDENTS_ROLES))],
    response_model=IncidentKPIsResponse,
    summary="KPIs de gestión de incidentes",
)
async def get_incidents_kpis_endpoint(db: Session = Depends(get_db)) -> IncidentKPIsResponse:
    try:
        return IncidentKPIsResponse(**get_incidents_kpis(db))
    except Exception:
        logger.exception("Error KPIs incidentes")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/incidents/timeline",
    dependencies=[Depends(require_any_role(INCIDENTS_ROLES))],
    response_model=list[IncidentTimelinePoint],
    summary="Línea de tiempo de incidentes",
)
async def get_incidents_timeline_endpoint(
    days: int = Query(default=14, ge=1, le=90, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> list[IncidentTimelinePoint]:
    try:
        return [IncidentTimelinePoint(**p) for p in get_incidents_timeline(db, days=days)]
    except Exception:
        logger.exception("Error timeline incidentes")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/incidents/list",
    dependencies=[Depends(require_any_role(INCIDENTS_ROLES))],
    response_model=list[IncidentRow],
    summary="Lista de incidentes recientes",
)
async def get_incidents_list_endpoint(
    limit: int = Query(default=50, ge=1, le=200, description="Máximo de incidentes a retornar"),
    db: Session = Depends(get_db),
) -> list[IncidentRow]:
    try:
        return [IncidentRow(**row) for row in get_incidents_list(db, limit=limit)]
    except Exception:
        logger.exception("Error listado incidentes")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")
