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
    CRMExternalTicketResponse,
    CRMDistributionResponse,
)
from app.services.crm_analytics_service import (
    get_crm_kpis,
    get_crm_timeline,
    get_recent_tickets,
    get_sla_summary,
    get_tickets_by_channel,
    get_tickets_by_priority,
    get_tickets_by_source_project,
    get_csat_distribution,
)
from app.services.crm_external_client import (
    get_ticket_estado,
    CRMExternalNotFoundError,
    CRMExternalAuthError,
    CRMExternalTimeoutError,
    CRMExternalError,
)

logger = logging.getLogger(__name__)

CRM_ROLES = ["admin", "analista", "crm"]

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


@router.get(
    "/crm/channels",
    dependencies=[Depends(require_any_role(CRM_ROLES))],
    response_model=CRMDistributionResponse,
    summary="Distribución de tickets por canal",
)
async def get_crm_channels_endpoint(db: Session = Depends(get_db)) -> CRMDistributionResponse:
    try:
        return CRMDistributionResponse(**get_tickets_by_channel(db))
    except Exception:
        logger.exception("Error distribución por canal CRM")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/crm/priority",
    dependencies=[Depends(require_any_role(CRM_ROLES))],
    response_model=CRMDistributionResponse,
    summary="Distribución de tickets por prioridad",
)
async def get_crm_priority_endpoint(db: Session = Depends(get_db)) -> CRMDistributionResponse:
    try:
        return CRMDistributionResponse(**get_tickets_by_priority(db))
    except Exception:
        logger.exception("Error distribución por prioridad CRM")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/crm/source-projects",
    dependencies=[Depends(require_any_role(CRM_ROLES))],
    response_model=CRMDistributionResponse,
    summary="Distribución de tickets por dominio de origen",
)
async def get_crm_source_projects_endpoint(db: Session = Depends(get_db)) -> CRMDistributionResponse:
    try:
        return CRMDistributionResponse(**get_tickets_by_source_project(db))
    except Exception:
        logger.exception("Error distribución por dominio de origen CRM")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/crm/csat",
    dependencies=[Depends(require_any_role(CRM_ROLES))],
    response_model=CRMDistributionResponse,
    summary="Distribución de puntajes CSAT (1-5)",
)
async def get_crm_csat_endpoint(db: Session = Depends(get_db)) -> CRMDistributionResponse:
    try:
        return CRMDistributionResponse(**get_csat_distribution(db))
    except Exception:
        logger.exception("Error distribución CSAT CRM")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/crm/tickets/{ticket_id}/live",
    dependencies=[Depends(require_any_role(CRM_ROLES))],
    response_model=CRMExternalTicketResponse,
    summary="Consulta en vivo del estado real de un ticket contra el CRM externo",
    description=(
        "Reconciliación puntual: consulta directamente al CRM externo "
        "(pgti-proyecto-crm-backend) por el estado actual de un ticket, "
        "sin depender del pipeline asíncrono de eventos ni de nuestra BD."
    ),
)
async def get_crm_ticket_live_endpoint(ticket_id: str) -> CRMExternalTicketResponse:
    try:
        ticket = get_ticket_estado(ticket_id)
        return CRMExternalTicketResponse(**ticket)
    except CRMExternalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except CRMExternalAuthError as exc:
        logger.error("Error de configuración consultando CRM externo: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error de configuración del servicio")
    except CRMExternalTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc))
    except CRMExternalError as exc:
        logger.warning("Error consultando CRM externo: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception:
        logger.exception("Error inesperado consultando ticket en vivo del CRM")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")
