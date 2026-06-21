import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
from app.schemas.notifications_kpi_schema import (
    NotificationKPIs,
    ChannelsResponse as NotificationChannelsResponse,
    ChannelMetric as NotificationChannelMetric,
    StatusResponse as NotificationStatusResponse,
    StatusMetric as NotificationStatusMetric,
    NotificationTimelineResponse,
    NotificationTimelinePoint,
)
from app.analytics.notifications_kpis import (
    get_notifications_kpis,
    get_notifications_by_channel,
    get_notifications_by_status,
    get_notifications_timeline,
)

logger = logging.getLogger(__name__)

NOTIFICATIONS_ROLES = ["admin", "analista", "notifications"]

router = APIRouter(tags=["kpis — notifications"])


@router.get(
    "/notifications/kpis",
    dependencies=[Depends(require_any_role(NOTIFICATIONS_ROLES))],
    response_model=NotificationKPIs,
    summary="KPIs consolidados de notificaciones",
)
async def get_notifications_kpis_endpoint(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> NotificationKPIs:
    try:
        return NotificationKPIs(**get_notifications_kpis(db, days))
    except Exception:
        logger.exception("Error KPIs notificaciones")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/notifications/channels",
    dependencies=[Depends(require_any_role(NOTIFICATIONS_ROLES))],
    response_model=NotificationChannelsResponse,
    summary="Métricas por canal de notificación",
)
async def get_notifications_channels_endpoint(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> NotificationChannelsResponse:
    try:
        channels = get_notifications_by_channel(db, days)
        total = sum(c["total"] for c in channels)
        return NotificationChannelsResponse(
            total_notifications=total,
            channels=[NotificationChannelMetric(**c) for c in channels],
        )
    except Exception:
        logger.exception("Error canales notificaciones")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/notifications/status",
    dependencies=[Depends(require_any_role(NOTIFICATIONS_ROLES))],
    response_model=NotificationStatusResponse,
    summary="Distribución por estado de notificación",
)
async def get_notifications_status_endpoint(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> NotificationStatusResponse:
    try:
        statuses = get_notifications_by_status(db, days)
        total = sum(s["count"] for s in statuses)
        return NotificationStatusResponse(
            total_notifications=total,
            statuses=[NotificationStatusMetric(**s) for s in statuses],
        )
    except Exception:
        logger.exception("Error estados notificaciones")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/notifications/timeline",
    dependencies=[Depends(require_any_role(NOTIFICATIONS_ROLES))],
    response_model=NotificationTimelineResponse,
    summary="Línea de tiempo de notificaciones",
)
async def get_notifications_timeline_endpoint(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> NotificationTimelineResponse:
    try:
        timeline = get_notifications_timeline(db, days)
        total = sum(p["total"] for p in timeline)
        start_date = (datetime.now(tz=timezone.utc) - timedelta(days=days)).date().isoformat()
        end_date = datetime.now(tz=timezone.utc).date().isoformat()
        return NotificationTimelineResponse(
            start_date=start_date,
            end_date=end_date,
            total_notifications=total,
            timeline=[NotificationTimelinePoint(**p) for p in timeline],
        )
    except Exception:
        logger.exception("Error timeline notificaciones")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")
