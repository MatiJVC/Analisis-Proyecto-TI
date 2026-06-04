from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.db import get_db
from app.schemas import KPIResponse, SubscriptionSummary
from app.schemas.orders_analytics_schema import (
    KPISResponse, ChannelsResponse, StatusResponse, TimelineResponse,
    ChannelMetric, StatusMetric
)
from app.schemas.subscription_analytics_schema import (
    SubscriptionTimelineResponse, SubscriptionTimelinePoint
)
from app.analytics.subscription_kpis import (
    get_renewal_rate,
    get_error_rate,
    get_auto_service_rate,
    get_subscription_summary,
    get_subscriptions_by_date,
    get_all_retention_rates
)
from app.analytics.orders_kpis import (
    get_all_kpis,
    get_orders_by_channel,
    get_orders_by_status,
    get_orders_by_date,
    get_total_orders,
)
from app.services.salud_analytics_service import (
    get_salud_dashboard_summary,
    get_salud_today_schedule,
    get_salud_visit_trends,
)
from app.schemas.salud_kpi_schema import (
    SaludDashboardSummary,
    SaludTodayScheduleResponse,
    SaludVisitTrendsResponse,
    SaludVisitTrendPoint,
    SaludTodayVisitRow,
)
from app.services.incidents_analytics_service import (
    get_incidents_kpis,
    get_incidents_list,
    get_incidents_timeline,
)
from app.schemas.incidents_kpi_schema import (
    IncidentKPIsResponse,
    IncidentTimelinePoint,
    IncidentRow,
)
from app.services.overview_analytics_service import (
    get_critical_alerts,
    get_recent_activities,
    get_service_statuses,
)
from app.services.crm_analytics_service import (
    get_crm_kpis,
    get_crm_timeline,
    get_recent_tickets,
    get_sla_summary,
)
from app.schemas.crm_kpi_schema import (
    CRMKPIsResponse,
    CRMTimelineResponse,
    CRMTimelinePoint,
    CRMTicketsResponse,
    CRMTicketRow,
    CRMSLASummary,
)
from app.schemas.overview_kpi_schema import (
    ActivityRow,
    AlertRow,
    GlobalKPIsResponse,
    ServiceStatusRow,
)


router = APIRouter(
    prefix="/kpis",
    tags=["analytics"],
    responses={
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "/subscriptions/renewal-rate",
    response_model=KPIResponse,
    summary="Obtener tasa de renovación de suscripciones",
    description="Retorna el porcentaje de suscripciones renovadas (renewed=true)"
)
async def get_renewal_rate_endpoint(
    db: Session = Depends(get_db)
) -> KPIResponse:
    try:
        rate = get_renewal_rate(db)
        return KPIResponse(
            kpi="renewal_rate",
            value=rate
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculando renewal_rate: {str(e)}"
        )


@router.get(
    "/subscriptions/error-rate",
    response_model=KPIResponse,
    summary="Obtener tasa de error de facturación",
    description="Retorna el porcentaje de suscripciones con errores de facturación (billing_success=false)"
)
async def get_error_rate_endpoint(
    db: Session = Depends(get_db)
) -> KPIResponse:
    try:
        rate = get_error_rate(db)
        return KPIResponse(
            kpi="error_rate",
            value=rate
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculando error_rate: {str(e)}"
        )


@router.get(
    "/subscriptions/auto-service-rate",
    response_model=KPIResponse,
    summary="Obtener tasa de auto-servicio",
    description="Retorna el porcentaje de suscripciones con auto-servicio habilitado (auto_service=true)"
)
async def get_auto_service_rate_endpoint(
    db: Session = Depends(get_db)
) -> KPIResponse:
    try:
        rate = get_auto_service_rate(db)
        return KPIResponse(
            kpi="auto_service_rate",
            value=rate
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculando auto_service_rate: {str(e)}"
        )


@router.get(
    "/subscriptions/summary",
    response_model=SubscriptionSummary,
    summary="Obtener resumen de KPIs de suscripciones",
    description="Retorna todos los KPIs de suscripciones. Puede filtrar por período de días"
)
async def get_subscription_summary_endpoint(
    days: int = 30,
    db: Session = Depends(get_db)
) -> SubscriptionSummary:
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        summary = get_subscription_summary(db, days)
        return SubscriptionSummary(
            renewal_rate=summary["renewal_rate"],
            error_rate=summary["error_rate"],
            auto_service_rate=summary["auto_service_rate"],
            stats=summary["stats"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculando resumen: {str(e)}"
        )


@router.get(
    "/subscriptions/timeline",
    response_model=SubscriptionTimelineResponse,
    summary="Línea de tiempo de suscripciones",
    description="Obtiene línea de tiempo de suscripciones agrupada por fecha (nuevas, renovaciones, cancelaciones)"
)
async def get_subscriptions_timeline(days: int = 30, db: Session = Depends(get_db)) -> SubscriptionTimelineResponse:
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        timeline_data = get_subscriptions_by_date(db, days)
        
        # Devuelve respuesta válida incluso si no hay datos
        total_subscriptions = sum(
            point["new_subscriptions"] + point["renewals"] + point["cancellations"]
            for point in timeline_data
        ) if timeline_data else 0
        
        start_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
        end_date = datetime.utcnow().date().isoformat()
        
        timeline_points = [
            SubscriptionTimelinePoint(
                date=point["date"],
                new_subscriptions=point["new_subscriptions"],
                renewals=point["renewals"],
                cancellations=point["cancellations"]
            )
            for point in timeline_data
        ] if timeline_data else []
        
        return SubscriptionTimelineResponse(
            start_date=start_date,
            end_date=end_date,
            total_subscriptions=total_subscriptions,
            timeline=timeline_points
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating subscriptions timeline: {str(e)}"
        )


@router.get(
    "/subscriptions/retention",
    summary="Tasas de retención de suscripciones",
    description="Retorna retention rates para 30 días, 90 días y período anual (365 días)"
)
async def get_subscriptions_retention(db: Session = Depends(get_db)):
    try:
        retention_data = get_all_retention_rates(db)
        
        return {
            "retention_rates": {
                "30_days": retention_data["retention_30_days"],
                "90_days": retention_data["retention_90_days"],
                "annual": retention_data["retention_annual"]
            },
            "description": {
                "30_days": f"De las suscripciones activas hace 30 días, {retention_data['retention_30_days']}% siguen activas",
                "90_days": f"De las suscripciones activas hace 90 días, {retention_data['retention_90_days']}% siguen activas",
                "annual": f"De las suscripciones activas hace 1 año, {retention_data['retention_annual']}% siguen activas"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculando retention rates: {str(e)}"
        )


# ================================================================
# ORDERS ANALYTICS ENDPOINTS
# ================================================================

@router.get(
    "/orders/kpis",
    response_model=KPISResponse,
    summary="KPIs consolidados de órdenes",
    description="Retorna todos los KPIs principales del dominio Orders"
)
async def get_orders_kpis(db: Session = Depends(get_db)) -> KPISResponse:
    try:
        kpis = get_all_kpis(db)
        
        return KPISResponse(
            total_orders=kpis["total_orders"],
            delivery_rate=kpis["delivery_rate"],
            payment_failure_rate=kpis["payment_failure_rate"],
            payment_success_rate=kpis["payment_success_rate"],
            avg_processing_time_hours=kpis["avg_processing_time_hours"],
            revenue_total=kpis["revenue_total"],
            average_order_value=kpis["average_order_value"],
            sla_compliance=kpis["sla_compliance"],
            stock_reservation_rate=kpis["stock_reservation_rate"],
            fulfillment_rate=kpis["fulfillment_rate"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating KPIs: {str(e)}"
        )


@router.get(
    "/orders/channels",
    response_model=ChannelsResponse,
    summary="Distribución de órdenes por canal",
    description="Obtiene distribución de órdenes por canal de venta (web, app, call_center, store)"
)
async def get_orders_by_channels(db: Session = Depends(get_db)) -> ChannelsResponse:
    try:
        total = get_total_orders(db)
        
        if total == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No orders found in database"
            )
        
        channels_data = get_orders_by_channel(db)
        
        channels_list = []
        for channel, count, revenue in channels_data:
            percentage = (count / total * 100) if total > 0 else 0
            channels_list.append(
                ChannelMetric(
                    channel=channel,
                    order_count=count,
                    revenue=round(revenue, 2),
                    percentage_of_total=round(percentage, 2)
                )
            )
        
        channels_list.sort(key=lambda x: x.revenue, reverse=True)
        
        return ChannelsResponse(
            total_orders=total,
            channels=channels_list
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating channel distribution: {str(e)}"
        )


@router.get(
    "/orders/status",
    response_model=StatusResponse,
    summary="Distribución de órdenes por estado",
    description="Obtiene distribución de órdenes por estado del ciclo de vida"
)
async def get_orders_by_statuses(db: Session = Depends(get_db)) -> StatusResponse:
    try:
        total = get_total_orders(db)
        
        if total == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No orders found in database"
            )
        
        status_data = get_orders_by_status(db)
        
        statuses_list = []
        for status_name, count in status_data:
            percentage = (count / total * 100) if total > 0 else 0
            statuses_list.append(
                StatusMetric(
                    status=status_name,
                    count=count,
                    percentage_of_total=round(percentage, 2)
                )
            )
        
        statuses_list.sort(key=lambda x: x.count, reverse=True)
        
        return StatusResponse(
            total_orders=total,
            statuses=statuses_list
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating status distribution: {str(e)}"
        )


@router.get(
    "/orders/timeline",
    response_model=TimelineResponse,
    summary="Línea de tiempo de órdenes",
    description="Obtiene línea de tiempo de órdenes grouped por fecha (últimos N días)"
)
async def get_orders_timeline(days: int = 30, db: Session = Depends(get_db)) -> TimelineResponse:
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        timeline_data = get_orders_by_date(db, days)
        
        if not timeline_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No orders found in the last {days} days"
            )
        
        total_orders = sum(point["order_count"] for point in timeline_data)
        
        start_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
        end_date = datetime.utcnow().date().isoformat()
        
        return TimelineResponse(
            start_date=start_date,
            end_date=end_date,
            total_orders=total_orders,
            timeline=[
                {
                    "date": point["date"],
                    "order_count": point["order_count"],
                    "delivered_count": point.get("delivered_count", 0),
                    "failed_count": point.get("failed_count", 0),
                    "revenue": point["revenue"],
                    "avg_order_value": point["avg_order_value"]
                }
                for point in timeline_data
            ]  # ty:ignore[invalid-argument-type]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating timeline: {str(e)}"
        )


@router.get(
    "/orders/health",
    summary="Health check de analítica de órdenes",
    description="Verifica disponibilidad del servicio de analítica de órdenes"
)
async def orders_health_check(db: Session = Depends(get_db)):
    try:
        total = get_total_orders(db)
        return {
            "status": "healthy",
            "orders_in_database": total
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


# ================================================================
# SALUD / HOME HEALTH — KPIs desde el warehouse
# ================================================================


@router.get(
    "/salud/dashboard",
    response_model=SaludDashboardSummary,
    summary="KPIs agregados salud",
    description="Métricas desde dim_pacientes, dim_profesionales, dim_zonas y fact_visitas",
)
async def get_salud_dashboard(db: Session = Depends(get_db)) -> SaludDashboardSummary:
    try:
        data = get_salud_dashboard_summary(db)
        return SaludDashboardSummary(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error KPIs salud: {str(e)}",
        )


@router.get(
    "/salud/visit-trends",
    response_model=SaludVisitTrendsResponse,
    summary="Tendencia diaria de visitas",
    description="Conteo por fecha_programada: visitas totales y completadas (últimos N días)",
)
async def get_salud_visit_trends_endpoint(
    days: int = 14,
    db: Session = Depends(get_db),
) -> SaludVisitTrendsResponse:
    try:
        if days < 1 or days > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="days debe estar entre 1 y 90",
            )
        raw = get_salud_visit_trends(db, days=days)
        points = [SaludVisitTrendPoint(**p) for p in raw["points"]]
        return SaludVisitTrendsResponse(days=raw["days"], points=points)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error tendencia visitas: {str(e)}",
        )


@router.get(
    "/salud/today-schedule",
    response_model=SaludTodayScheduleResponse,
    summary="Agenda del día",
    description="Visitas con fecha_programada = hoy, con paciente y profesional desde dimensiones",
)
async def get_salud_today_schedule_endpoint(
    db: Session = Depends(get_db),
) -> SaludTodayScheduleResponse:
    try:
        raw = get_salud_today_schedule(db)
        rows = [SaludTodayVisitRow(**v) for v in raw["visits"]]
        return SaludTodayScheduleResponse(date=raw["date"], visits=rows)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error agenda salud: {str(e)}",
        )


# ================================================================
# INCIDENTS — KPIs desde fact_incidents
# ================================================================


@router.get(
    "/incidents/kpis",
    response_model=IncidentKPIsResponse,
    summary="KPIs de gestión de incidentes",
    description="Métricas agregadas desde fact_incidents",
)
async def get_incidents_kpis_endpoint(
    db: Session = Depends(get_db),
) -> IncidentKPIsResponse:
    try:
        data = get_incidents_kpis(db)
        return IncidentKPIsResponse(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error KPIs incidentes: {str(e)}",
        )


@router.get(
    "/incidents/timeline",
    response_model=list[IncidentTimelinePoint],
    summary="Línea de tiempo de incidentes",
    description="Volumen diario: abiertos, resueltos y críticos (últimos N días)",
)
async def get_incidents_timeline_endpoint(
    days: int = 14,
    db: Session = Depends(get_db),
) -> list[IncidentTimelinePoint]:
    try:
        if days < 1 or days > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="days debe estar entre 1 y 90",
            )
        raw = get_incidents_timeline(db, days=days)
        return [IncidentTimelinePoint(**p) for p in raw]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error timeline incidentes: {str(e)}",
        )


@router.get(
    "/incidents/list",
    response_model=list[IncidentRow],
    summary="Lista de incidentes",
    description="Incidentes recientes desde el warehouse, ordenados por última actualización",
)
async def get_incidents_list_endpoint(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[IncidentRow]:
    try:
        if limit < 1 or limit > 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit debe estar entre 1 y 200",
            )
        raw = get_incidents_list(db, limit=limit)
        return [IncidentRow(**row) for row in raw]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listado incidentes: {str(e)}",
        )


# ================================================================
# OVERVIEW — KPIs y feeds agregados desde warehouses existentes
# ================================================================


@router.get(
    "/overview/kpis",
    response_model=GlobalKPIsResponse,
    summary="KPIs globales (overview)",
    description="Agrega métricas desde fact_orders, fact_incidents y fact_subscriptions",
)
async def get_overview_kpis_endpoint(
    db: Session = Depends(get_db),
) -> GlobalKPIsResponse:
    try:
        return GlobalKPIsResponse(**get_global_kpis(db))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error KPIs overview: {str(e)}",
        )


@router.get(
    "/overview/services",
    response_model=list[ServiceStatusRow],
    summary="Estado de servicios",
    description="Estado derivado de incidentes activos por keywords del título",
)
async def get_overview_services_endpoint(
    db: Session = Depends(get_db),
) -> list[ServiceStatusRow]:
    try:
        rows = get_service_statuses(db)
        return [ServiceStatusRow(**r) for r in rows]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error servicios overview: {str(e)}",
        )


@router.get(
    "/overview/activities",
    response_model=list[ActivityRow],
    summary="Actividad reciente",
    description="Últimos eventos cross-domain desde raw_events",
)
async def get_overview_activities_endpoint(
    limit: int = 10,
    db: Session = Depends(get_db),
) -> list[ActivityRow]:
    try:
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit debe estar entre 1 y 50",
            )
        rows = get_recent_activities(db, limit=limit)
        return [ActivityRow(**r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actividad overview: {str(e)}",
        )


@router.get(
    "/overview/alerts",
    response_model=list[AlertRow],
    summary="Alertas críticas",
    description="Incidentes activos con severidad critical/high",
)
async def get_overview_alerts_endpoint(
    limit: int = 10,
    db: Session = Depends(get_db),
) -> list[AlertRow]:
    try:
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit debe estar entre 1 y 50",
            )
        rows = get_critical_alerts(db, limit=limit)
        return [AlertRow(**r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error alertas overview: {str(e)}",
        )


@router.get(
    "/crm/kpis",
    response_model=CRMKPIsResponse,
    summary="KPIs del módulo CRM",
    description="Clientes, tickets abiertos, tiempo de respuesta promedio, CSAT, mensajes y tasa de resolución",
)
async def get_crm_kpis_endpoint(db: Session = Depends(get_db)) -> CRMKPIsResponse:
    try:
        return CRMKPIsResponse(**get_crm_kpis(db))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error KPIs CRM: {str(e)}",
        )


@router.get(
    "/crm/timeline",
    response_model=CRMTimelineResponse,
    summary="Volumen de tickets CRM por día",
    description="Tickets abiertos y resueltos por día en los últimos N días",
)
async def get_crm_timeline_endpoint(
    days: int = 14,
    db: Session = Depends(get_db),
) -> CRMTimelineResponse:
    try:
        if days < 1 or days > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="days debe estar entre 1 y 90",
            )
        points = get_crm_timeline(db, days=days)
        return CRMTimelineResponse(days=days, points=[CRMTimelinePoint(**p) for p in points])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error timeline CRM: {str(e)}",
        )


@router.get(
    "/crm/tickets",
    response_model=CRMTicketsResponse,
    summary="Tickets recientes de CRM",
    description="Lista de tickets más recientes ordenados por fecha de apertura",
)
async def get_crm_tickets_endpoint(
    limit: int = 10,
    db: Session = Depends(get_db),
) -> CRMTicketsResponse:
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit debe estar entre 1 y 100",
            )
        tickets = get_recent_tickets(db, limit=limit)
        return CRMTicketsResponse(tickets=[CRMTicketRow(**t) for t in tickets])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error tickets CRM: {str(e)}",
        )


@router.get(
    "/crm/sla",
    response_model=CRMSLASummary,
    summary="Resumen de SLA del módulo CRM",
    description="Violaciones de SLA y tasa de cumplimiento",
)
async def get_crm_sla_endpoint(db: Session = Depends(get_db)) -> CRMSLASummary:
    try:
        return CRMSLASummary(**get_sla_summary(db))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error SLA CRM: {str(e)}",
        )
