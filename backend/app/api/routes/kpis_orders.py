import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
from app.redis_client import redis_client
from app.api.kpi_cache import get_kpi_cache, set_kpi_cache
from app.schemas.orders_analytics_schema import (
    KPISResponse,
    ChannelsResponse,
    StatusResponse,
    TimelineResponse,
    ChannelMetric as OrderChannelMetric,
    StatusMetric as OrderStatusMetric,
)
from app.analytics.orders_kpis import (
    get_all_kpis,
    get_orders_by_channel,
    get_orders_by_status,
    get_orders_by_date,
    get_total_orders,
)

logger = logging.getLogger(__name__)

ORDERS_ROLES = ["admin", "analista", "orders"]

router = APIRouter(tags=["kpis — orders"])


@router.get(
    "/orders/kpis",
    dependencies=[Depends(require_any_role(ORDERS_ROLES))],
    response_model=KPISResponse,
    summary="KPIs consolidados de órdenes",
)
async def get_orders_kpis(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> KPISResponse:
    try:
        cache_key = f"kpi:orders:{days}"
        cached = get_kpi_cache(redis_client, cache_key)
        if cached:
            return KPISResponse(**cached)

        kpis = get_all_kpis(db, days)
        set_kpi_cache(redis_client, cache_key, kpis)
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
            fulfillment_rate=kpis["fulfillment_rate"],
        )
    except Exception:
        logger.exception("Error calculando KPIs órdenes")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/orders/channels",
    dependencies=[Depends(require_any_role(ORDERS_ROLES))],
    response_model=ChannelsResponse,
    summary="Distribución de órdenes por canal",
)
async def get_orders_by_channels(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> ChannelsResponse:
    try:
        total = get_total_orders(db, days)
        if total == 0:
            return ChannelsResponse(total_orders=0, channels=[])
        channels_data = get_orders_by_channel(db, days)
        channels_list = []
        for channel, count, revenue in channels_data:
            if channel is None:
                continue
            percentage = (count / total * 100) if total > 0 else 0
            channels_list.append(
                OrderChannelMetric(
                    channel=channel or "unknown",
                    order_count=count or 0,
                    revenue=round(float(revenue) if revenue else 0.0, 2),
                    percentage_of_total=round(percentage, 2),
                )
            )
        channels_list.sort(key=lambda x: x.revenue, reverse=True)
        return ChannelsResponse(total_orders=total, channels=channels_list)
    except Exception:
        logger.exception("Error calculando distribución por canal")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/orders/status",
    dependencies=[Depends(require_any_role(ORDERS_ROLES))],
    response_model=StatusResponse,
    summary="Distribución de órdenes por estado",
)
async def get_orders_by_statuses(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> StatusResponse:
    try:
        total = get_total_orders(db, days)
        if total == 0:
            return StatusResponse(total_orders=0, statuses=[])
        status_data = get_orders_by_status(db, days)
        statuses_list = []
        for status_name, count in status_data:
            percentage = (count / total * 100) if total > 0 else 0
            statuses_list.append(
                OrderStatusMetric(
                    status=status_name,
                    count=count,
                    percentage_of_total=round(percentage, 2),
                )
            )
        statuses_list.sort(key=lambda x: x.count, reverse=True)
        return StatusResponse(total_orders=total, statuses=statuses_list)
    except Exception:
        logger.exception("Error calculando distribución por estado")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/orders/timeline",
    dependencies=[Depends(require_any_role(ORDERS_ROLES))],
    response_model=TimelineResponse,
    summary="Línea de tiempo de órdenes",
)
async def get_orders_timeline(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> TimelineResponse:
    try:
        timeline_data = get_orders_by_date(db, days)
        start_date = (datetime.now(tz=timezone.utc) - timedelta(days=days)).date().isoformat()
        end_date = datetime.now(tz=timezone.utc).date().isoformat()
        if not timeline_data:
            return TimelineResponse(start_date=start_date, end_date=end_date, total_orders=0, timeline=[])
        total_orders = sum(point["order_count"] for point in timeline_data)
        return TimelineResponse(
            start_date=start_date,
            end_date=end_date,
            total_orders=total_orders,
            timeline=[
                {
                    "date": p["date"],
                    "order_count": p["order_count"],
                    "delivered_count": p.get("delivered_count", 0),
                    "failed_count": p.get("failed_count", 0),
                    "revenue": p["revenue"],
                    "avg_order_value": p["avg_order_value"],
                }
                for p in timeline_data
            ],  # ty:ignore[invalid-argument-type]
        )
    except Exception:
        logger.exception("Error calculando timeline órdenes")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/orders/health",
    dependencies=[Depends(require_any_role(ORDERS_ROLES))],
    summary="Health check de analítica de órdenes",
)
async def orders_health_check(db: Session = Depends(get_db)):
    try:
        return {"status": "healthy", "orders_in_database": get_total_orders(db)}
    except Exception:
        logger.exception("Health check órdenes failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Error interno del servidor")
