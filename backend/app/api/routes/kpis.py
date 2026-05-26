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
from app.services.iot_analytics_service import (
    get_all_iot_kpis,
    get_sensors_status,
    get_sensors_by_type,
    get_iot_events,
    get_iot_timeline,
)
from app.schemas.iot_kpi_schema import (
    SensorKPIs,
    SensorsStatusResponse,
    SensorStatus,
    SensorsByTypeResponse,
    SensorTypeMetric,
    EventsResponse,
    SensorEvent,
    IoTTimelineResponse,
    TimelinePoint,
)
from app.services.overview_analytics_service import (
    get_critical_alerts,
    get_recent_activities,
    get_service_statuses,
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
    description="Retorna todos los KPIs principales del dominio Orders. Puede filtrar por período de días"
)
async def get_orders_kpis(days: int = 30, db: Session = Depends(get_db)) -> KPISResponse:
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        kpis = get_all_kpis(db, days)
        
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
    description="Obtiene distribución de órdenes por canal de venta (web, app, call_center, store). Puede filtrar por período de días"
)
async def get_orders_by_channels(days: int = 30, db: Session = Depends(get_db)) -> ChannelsResponse:
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        total = get_total_orders(db, days)
        
        if total == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No orders found in database"
            )
        
        channels_data = get_orders_by_channel(db, days)
        
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
    description="Obtiene distribución de órdenes por estado del ciclo de vida. Puede filtrar por período de días"
)
async def get_orders_by_statuses(days: int = 30, db: Session = Depends(get_db)) -> StatusResponse:
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        total = get_total_orders(db, days)
        
        if total == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No orders found in database"
            )
        
        status_data = get_orders_by_status(db, days)
        
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


# ================================================================
# IoT — KPIs desde fact_iot y raw_events
# ================================================================

@router.get(
    "/iot/kpis",
    response_model=SensorKPIs,
    summary="KPIs consolidados de sensores IoT",
    description="Retorna todos los KPIs principales. Algunos son real-time (siempre actual), otros pueden filtrarse por días"
)
async def get_iot_kpis_endpoint(
    days: int = None,
    db: Session = Depends(get_db)
) -> SensorKPIs:
    try:
        if days is not None and (days < 1 or days > 365):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        kpis = get_all_iot_kpis(db, days)
        
        return SensorKPIs(
            total_sensors=kpis["total_sensors"],
            online_sensors=kpis["online_sensors"],
            offline_sensors=kpis["offline_sensors"],
            availability_rate=kpis["availability_rate"],
            avg_battery_level=kpis["avg_battery_level"],
            low_battery_count=kpis["low_battery_count"],
            data_validity_rate=kpis["data_validity_rate"],
            anomalies_detected=kpis["anomalies_detected"],
            avg_processing_latency_ms=kpis["avg_processing_latency_ms"],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating IoT KPIs: {str(e)}"
        )


@router.get(
    "/iot/status",
    response_model=SensorsStatusResponse,
    summary="Estado actual de sensores",
    description="Obtiene estado actual de todos los sensores IoT (online, battery, última lectura, etc). El parámetro days es opcional e informativo"
)
async def get_iot_sensors_status(
    days: int = None,
    db: Session = Depends(get_db)
) -> SensorsStatusResponse:
    try:
        if days is not None and (days < 1 or days > 365):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        status_data = get_sensors_status(db)
        
        sensors_list = [
            SensorStatus(
                sensor_id=sensor["sensor_id"],
                asset_id=sensor["asset_id"],
                sensor_type=sensor["sensor_type"],
                is_online=sensor["is_online"],
                battery_level=sensor["battery_level"],
                last_reading_at=sensor["last_reading_at"],
                location=sensor["location"],
                has_anomaly=sensor["has_anomaly"],
                low_battery_alert=sensor["low_battery_alert"],
            )
            for sensor in status_data
        ]
        
        online_count = sum(1 for s in sensors_list if s.is_online)
        offline_count = sum(1 for s in sensors_list if not s.is_online)
        
        return SensorsStatusResponse(
            total_sensors=len(sensors_list),
            online_count=online_count,
            offline_count=offline_count,
            sensors=sensors_list
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sensors status: {str(e)}"
        )


@router.get(
    "/iot/by-type",
    response_model=SensorsByTypeResponse,
    summary="Distribución de sensores por tipo",
    description="Obtiene distribución y estado actual de sensores agrupados por tipo. El parámetro days es opcional e informativo"
)
async def get_iot_sensors_by_type(
    days: int = None,
    db: Session = Depends(get_db)
) -> SensorsByTypeResponse:
    try:
        if days is not None and (days < 1 or days > 365):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        types_data = get_sensors_by_type(db)
        
        types_list = [
            SensorTypeMetric(
                sensor_type=sensor_type["sensor_type"],
                count=sensor_type["count"],
                online_count=sensor_type["online_count"],
                offline_count=sensor_type["offline_count"],
                avg_battery=sensor_type["avg_battery"],
                anomaly_count=sensor_type["anomaly_count"],
            )
            for sensor_type in types_data
        ]
        
        total_sensors = sum(t.count for t in types_list)
        
        return SensorsByTypeResponse(
            total_sensors=total_sensors,
            sensor_types=types_list
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sensors by type: {str(e)}"
        )


@router.get(
    "/iot/events",
    response_model=EventsResponse,
    summary="Eventos recientes de IoT",
    description="Obtiene eventos/alertas recientes desde raw_events (sensor_offline, low_battery, anomaly_detected, etc)"
)
async def get_iot_events_endpoint(
    days: int = 30,
    limit: int = 50,
    db: Session = Depends(get_db)
) -> EventsResponse:
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        if limit < 1 or limit > 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 200"
            )
        
        events_data = get_iot_events(db, days, limit)
        
        events_list = [
            SensorEvent(
                event_id=event["event_id"],
                sensor_id=event["sensor_id"],
                event_type=event["event_type"],
                timestamp=event["timestamp"],
                severity=event["severity"],
                message=event["message"],
                data=event["data"],
            )
            for event in events_data
        ]
        
        critical_count = sum(1 for e in events_list if e.severity == "critical")
        warning_count = sum(1 for e in events_list if e.severity == "warning")
        info_count = sum(1 for e in events_list if e.severity == "info")
        
        return EventsResponse(
            total_events=len(events_list),
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            events=events_list
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting IoT events: {str(e)}"
        )


@router.get(
    "/iot/timeline",
    response_model=IoTTimelineResponse,
    summary="Línea de tiempo de IoT",
    description="Obtiene timeline de actividad IoT agrupada por fecha (últimos N días)"
)
async def get_iot_timeline_endpoint(
    days: int = 30,
    db: Session = Depends(get_db)
) -> IoTTimelineResponse:
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )
        
        timeline_data = get_iot_timeline(db, days)
        
        if not timeline_data:
            # Devolver respuesta válida incluso si no hay datos
            start_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
            end_date = datetime.utcnow().date().isoformat()
            
            return IoTTimelineResponse(
                start_date=start_date,
                end_date=end_date,
                total_events=0,
                timeline=[]
            )
        
        start_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
        end_date = datetime.utcnow().date().isoformat()
        total_events = sum(point["events_count"] for point in timeline_data)
        
        timeline_points = [
            TimelinePoint(
                date=point["date"],
                events_count=point["events_count"],
                sensors_online=point["sensors_online"],
                sensors_offline=point["sensors_offline"],
                avg_battery=point["avg_battery"],
                anomalies=point["anomalies"],
            )
            for point in timeline_data
        ]
        
        return IoTTimelineResponse(
            start_date=start_date,
            end_date=end_date,
            total_events=total_events,
            timeline=timeline_points
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating IoT timeline: {str(e)}"
        )


@router.get(
    "/iot/health",
    summary="Health check de analítica IoT",
    description="Verifica disponibilidad del servicio de analítica IoT"
)
async def iot_health_check(db: Session = Depends(get_db)):
    try:
        kpis = get_all_iot_kpis(db)
        return {
            "status": "healthy",
            "total_sensors": kpis["total_sensors"],
            "online_sensors": kpis["online_sensors"],
            "availability_rate": kpis["availability_rate"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )
