from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import KPIResponse, SubscriptionSummary
from app.analytics import (
    get_renewal_rate,
    get_error_rate,
    get_auto_service_rate,
    get_subscription_summary
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
    description="Retorna todos los KPIs de suscripciones en un solo endpoint"
)
async def get_subscription_summary_endpoint(
    db: Session = Depends(get_db)
) -> SubscriptionSummary:
    try:
        summary = get_subscription_summary(db)
        return SubscriptionSummary(
            renewal_rate=summary["renewal_rate"],
            error_rate=summary["error_rate"],
            auto_service_rate=summary["auto_service_rate"],
            stats=summary["stats"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculando resumen: {str(e)}"
        )
