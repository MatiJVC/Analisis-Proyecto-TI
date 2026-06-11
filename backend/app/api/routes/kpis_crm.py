import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
from app.schemas.crm_kpi_schema import (
    CRMKPIsResponse,
    CRMTimelineResponse,
    CRMTimelinePoint,
    CRMTicketsResponse,
    CRMTicketRow,
    CRMSLASummary,
)
from app.services.crm_analytics_service import (
    get_crm_kpis,
    get_crm_timeline,
    get_recent_tickets,
    get_sla_summary,
)

logger = logging.getLogger(__name__)

CRM_ROLES = ["admin", "analista"]

router = APIRouter(tags=["kpis — crm"])


@router.get(
    "/crm/kpis",
    dependencies=[Depends(require_any_role(CRM_ROLES))],
    response_model=CRMKPIsResponse,
    summary="KPIs del módulo CRM",
)
async def get_crm_kpis_endpoint(db: Session = Depends(get_db)) -> CRMKPIsResponse:
    try:
        return CRMKPIsResponse(**get_crm_kpis(db))
    except Exception:
        logger.exception("Error KPIs CRM")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/crm/timeline",
    dependencies=[Depends(require_any_role(CRM_ROLES))],
    response_model=CRMTimelineResponse,
    summary="Volumen de tickets CRM por día",
)
async def get_crm_timeline_endpoint(
    days: int = Query(default=14, ge=1, le=90, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> CRMTimelineResponse:
    try:
        return CRMTimelineResponse(days=days, points=[CRMTimelinePoint(**p) for p in get_crm_timeline(db, days=days)])
    except Exception:
        logger.exception("Error timeline CRM")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/crm/tickets",
    dependencies=[Depends(require_any_role(CRM_ROLES))],
    response_model=CRMTicketsResponse,
    summary="Tickets recientes de CRM",
)
async def get_crm_tickets_endpoint(
    limit: int = Query(default=10, ge=1, le=100, description="Máximo de tickets a retornar"),
    db: Session = Depends(get_db),
) -> CRMTicketsResponse:
    try:
        return CRMTicketsResponse(tickets=[CRMTicketRow(**t) for t in get_recent_tickets(db, limit=limit)])
    except Exception:
        logger.exception("Error tickets CRM")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/crm/sla",
    dependencies=[Depends(require_any_role(CRM_ROLES))],
    response_model=CRMSLASummary,
    summary="Resumen de SLA del módulo CRM",
)
async def get_crm_sla_endpoint(db: Session = Depends(get_db)) -> CRMSLASummary:
    try:
        return CRMSLASummary(**get_sla_summary(db))
    except Exception:
        logger.exception("Error SLA CRM")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")
