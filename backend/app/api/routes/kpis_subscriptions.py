import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
from app.schemas import KPIResponse, SubscriptionSummary
from app.schemas.subscription_analytics_schema import (
    SubscriptionTimelineResponse,
    SubscriptionTimelinePoint,
)
from app.analytics.subscription_kpis import (
    get_renewal_rate,
    get_error_rate,
    get_auto_service_rate,
    get_subscription_summary,
    get_subscriptions_by_date,
    get_all_retention_rates,
)

logger = logging.getLogger(__name__)

SUBS_ROLES = ["admin", "analista", "subscriptions"]

router = APIRouter(tags=["kpis — subscriptions"])


@router.get(
    "/subscriptions/renewal-rate",
    dependencies=[Depends(require_any_role(SUBS_ROLES))],
    response_model=KPIResponse,
    summary="Tasa de renovación de suscripciones",
)
async def get_renewal_rate_endpoint(db: Session = Depends(get_db)) -> KPIResponse:
    try:
        return KPIResponse(kpi="renewal_rate", value=get_renewal_rate(db))
    except Exception:
        logger.exception("Error calculando renewal_rate")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/subscriptions/error-rate",
    dependencies=[Depends(require_any_role(SUBS_ROLES))],
    response_model=KPIResponse,
    summary="Tasa de error de facturación",
)
async def get_error_rate_endpoint(db: Session = Depends(get_db)) -> KPIResponse:
    try:
        return KPIResponse(kpi="error_rate", value=get_error_rate(db))
    except Exception:
        logger.exception("Error calculando error_rate")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/subscriptions/auto-service-rate",
    dependencies=[Depends(require_any_role(SUBS_ROLES))],
    response_model=KPIResponse,
    summary="Tasa de auto-servicio",
)
async def get_auto_service_rate_endpoint(db: Session = Depends(get_db)) -> KPIResponse:
    try:
        return KPIResponse(kpi="auto_service_rate", value=get_auto_service_rate(db))
    except Exception:
        logger.exception("Error calculando auto_service_rate")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/subscriptions/summary",
    dependencies=[Depends(require_any_role(SUBS_ROLES))],
    response_model=SubscriptionSummary,
    summary="Resumen de KPIs de suscripciones",
)
async def get_subscription_summary_endpoint(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> SubscriptionSummary:
    try:
        summary = get_subscription_summary(db, days)
        return SubscriptionSummary(
            renewal_rate=summary["renewal_rate"],
            error_rate=summary["error_rate"],
            auto_service_rate=summary["auto_service_rate"],
            stats=summary["stats"],
        )
    except Exception:
        logger.exception("Error calculando resumen suscripciones")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/subscriptions/timeline",
    dependencies=[Depends(require_any_role(SUBS_ROLES))],
    response_model=SubscriptionTimelineResponse,
    summary="Línea de tiempo de suscripciones",
)
async def get_subscriptions_timeline(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> SubscriptionTimelineResponse:
    try:
        timeline_data = get_subscriptions_by_date(db, days)
        total = sum(
            p["new_subscriptions"] + p["renewals"] + p["cancellations"]
            for p in timeline_data
        ) if timeline_data else 0
        start_date = (datetime.now(tz=timezone.utc) - timedelta(days=days)).date().isoformat()
        end_date = datetime.now(tz=timezone.utc).date().isoformat()
        return SubscriptionTimelineResponse(
            start_date=start_date,
            end_date=end_date,
            total_subscriptions=total,
            timeline=[SubscriptionTimelinePoint(**p) for p in timeline_data] if timeline_data else [],
        )
    except Exception:
        logger.exception("Error calculando timeline suscripciones")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/subscriptions/retention",
    dependencies=[Depends(require_any_role(SUBS_ROLES))],
    summary="Tasas de retención de suscripciones",
)
async def get_subscriptions_retention(db: Session = Depends(get_db)):
    try:
        data = get_all_retention_rates(db)
        return {
            "retention_rates": {
                "30_days": data["retention_30_days"],
                "90_days": data["retention_90_days"],
                "annual": data["retention_annual"],
            },
        }
    except Exception:
        logger.exception("Error calculando retention rates")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")
