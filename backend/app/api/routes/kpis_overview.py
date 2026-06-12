import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
from app.redis_client import redis_client
from app.api.kpi_cache import get_kpi_cache, set_kpi_cache
from app.schemas.overview_kpi_schema import (
    ActivityRow,
    AlertRow,
    GlobalKPIsResponse,
    ServiceStatusRow,
)
from app.services.overview_analytics_service import (
    get_critical_alerts,
    get_global_kpis,
    get_recent_activities,
    get_service_statuses,
)

logger = logging.getLogger(__name__)

OVERVIEW_ROLES = ["admin", "analista"]

router = APIRouter(tags=["kpis — overview"])


@router.get(
    "/overview/kpis",
    dependencies=[Depends(require_any_role(OVERVIEW_ROLES))],
    response_model=GlobalKPIsResponse,
    summary="KPIs globales (overview)",
    description="Agrega métricas desde fact_orders, fact_incidents y fact_subscriptions",
)
async def get_overview_kpis_endpoint(db: Session = Depends(get_db)) -> GlobalKPIsResponse:
    try:
        cached = get_kpi_cache(redis_client, "kpi:overview")
        if cached:
            return GlobalKPIsResponse(**cached)

        result = get_global_kpis(db)
        set_kpi_cache(redis_client, "kpi:overview", result, ttl=60)
        return GlobalKPIsResponse(**result)
    except Exception:
        logger.exception("Error KPIs overview")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/overview/services",
    dependencies=[Depends(require_any_role(OVERVIEW_ROLES))],
    response_model=list[ServiceStatusRow],
    summary="Estado de servicios",
)
async def get_overview_services_endpoint(db: Session = Depends(get_db)) -> list[ServiceStatusRow]:
    try:
        return [ServiceStatusRow(**r) for r in get_service_statuses(db)]
    except Exception:
        logger.exception("Error servicios overview")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/overview/activities",
    dependencies=[Depends(require_any_role(OVERVIEW_ROLES))],
    response_model=list[ActivityRow],
    summary="Actividad reciente",
)
async def get_overview_activities_endpoint(
    limit: int = Query(default=10, ge=1, le=50, description="Máximo de actividades a retornar"),
    db: Session = Depends(get_db),
) -> list[ActivityRow]:
    try:
        return [ActivityRow(**r) for r in get_recent_activities(db, limit=limit)]
    except Exception:
        logger.exception("Error actividad overview")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/overview/alerts",
    dependencies=[Depends(require_any_role(OVERVIEW_ROLES))],
    response_model=list[AlertRow],
    summary="Alertas críticas",
)
async def get_overview_alerts_endpoint(
    limit: int = Query(default=10, ge=1, le=50, description="Máximo de alertas a retornar"),
    db: Session = Depends(get_db),
) -> list[AlertRow]:
    try:
        return [AlertRow(**r) for r in get_critical_alerts(db, limit=limit)]
    except Exception:
        logger.exception("Error alertas overview")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")
