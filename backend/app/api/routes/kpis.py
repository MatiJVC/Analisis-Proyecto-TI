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
    get_total_orders
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
        
        if not timeline_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No subscription activity found in the last {days} days"
            )
        
        total_subscriptions = sum(
            point["new_subscriptions"] + point["renewals"] + point["cancellations"]
            for point in timeline_data
        )
        
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
        ]
        
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
