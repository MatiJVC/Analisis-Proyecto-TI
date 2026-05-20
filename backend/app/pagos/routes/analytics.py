from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.pagos.schemas.payment_analytics_schema import PaymentKPIsResponse, PaymentTimelinePoint
from app.pagos.services.payment_analytics_service import get_payment_kpis, get_payment_timeline

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    responses={500: {"description": "Internal server error"}},
)


@router.get(
    "/payments/kpis",
    response_model=PaymentKPIsResponse,
    summary="KPIs agregados del módulo de pagos",
    description=(
        "Consulta fact_payments_events y retorna métricas agregadas del rolling window "
        "indicado (default: últimas 24 h). "
        "Campos: totalTransactions, failedPayments, failureRate, revenue, "
        "avgTransactionValue, uptime."
    ),
)
async def get_payments_kpis(
    hours: int = Query(default=24, ge=1, le=8760, description="Ventana en horas (1–8760)"),
    db: Session = Depends(get_db),
) -> PaymentKPIsResponse:
    try:
        data = get_payment_kpis(db, hours=hours)
        return PaymentKPIsResponse(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculando KPIs de pagos: {exc}",
        )


@router.get(
    "/payments/timeline",
    response_model=List[PaymentTimelinePoint],
    summary="Timeline horario de transacciones de pagos",
    description=(
        "Agrupa fact_payments_events por hora y devuelve conteos de transacciones "
        "exitosas (Aprobado) y fallidas para cada bloque horario. "
        "Las horas sin actividad devuelven failed=0 y successful=0 (nunca null). "
        "Ordenado cronológicamente, hora más antigua primero."
    ),
)
async def get_payments_timeline(
    hours: int = Query(default=24, ge=1, le=168, description="Ventana en horas (1–168, default 24)"),
    db: Session = Depends(get_db),
) -> List[PaymentTimelinePoint]:
    try:
        data = get_payment_timeline(db, hours=hours)
        return [PaymentTimelinePoint(**point) for point in data]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculando timeline de pagos: {exc}",
        )
