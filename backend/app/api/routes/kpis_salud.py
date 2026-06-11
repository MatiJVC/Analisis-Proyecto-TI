import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
from app.schemas.salud_kpi_schema import (
    SaludDashboardSummary,
    SaludTodayScheduleResponse,
    SaludVisitTrendsResponse,
    SaludVisitTrendPoint,
    SaludTodayVisitRow,
)
from app.services.salud_analytics_service import (
    get_salud_dashboard_summary,
    get_salud_today_schedule,
    get_salud_visit_trends,
)

logger = logging.getLogger(__name__)

SALUD_ROLES = ["admin", "analista", "salud"]

router = APIRouter(tags=["kpis — salud"])


@router.get(
    "/salud/dashboard",
    dependencies=[Depends(require_any_role(SALUD_ROLES))],
    response_model=SaludDashboardSummary,
    summary="KPIs agregados salud",
)
async def get_salud_dashboard(db: Session = Depends(get_db)) -> SaludDashboardSummary:
    try:
        return SaludDashboardSummary(**get_salud_dashboard_summary(db))
    except Exception:
        logger.exception("Error KPIs salud")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/salud/visit-trends",
    dependencies=[Depends(require_any_role(SALUD_ROLES))],
    response_model=SaludVisitTrendsResponse,
    summary="Tendencia diaria de visitas",
)
async def get_salud_visit_trends_endpoint(
    days: int = Query(default=14, ge=1, le=90, description="Número de días en el rango de tendencia"),
    db: Session = Depends(get_db),
) -> SaludVisitTrendsResponse:
    try:
        raw = get_salud_visit_trends(db, days=days)
        return SaludVisitTrendsResponse(days=raw["days"], points=[SaludVisitTrendPoint(**p) for p in raw["points"]])
    except Exception:
        logger.exception("Error tendencia visitas")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/salud/today-schedule",
    dependencies=[Depends(require_any_role(SALUD_ROLES))],
    response_model=SaludTodayScheduleResponse,
    summary="Agenda del día",
)
async def get_salud_today_schedule_endpoint(db: Session = Depends(get_db)) -> SaludTodayScheduleResponse:
    try:
        raw = get_salud_today_schedule(db)
        return SaludTodayScheduleResponse(date=raw["date"], visits=[SaludTodayVisitRow(**v) for v in raw["visits"]])
    except Exception:
        logger.exception("Error agenda salud")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")
