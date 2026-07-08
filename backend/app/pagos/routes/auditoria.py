from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
from app.pagos.schemas.payment_analytics_schema import (
    CierreDescuadrePoint,
    DashboardResponse,
    DetalleReporteHisto,
    GenerarReporteResponse,
    ReporteHistorico,
)
from app.pagos.services.auditoria_service import (
    generar_reporte_hoy,
    get_cierres_descuadre,
    get_dashboard,
    get_detalle_reporte,
    get_reportes_historicos,
)

router = APIRouter(
    tags=["pagos-auditoria"],
    dependencies=[Depends(require_any_role(["admin", "analista", "payments"]))],
    responses={
        401: {"description": "Falta token Bearer o token inválido"},
        403: {"description": "El usuario no tiene rol suficiente"},
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "/analitica/dashboard",
    response_model=DashboardResponse,
    summary="Dashboard general de pagos",
    description=(
        "Retorna KPIs del día (últimas 24h), crecimiento respecto a las 24h anteriores, "
        "timeline horario de transacciones y distribución por método de pago."
    ),
)
async def get_dashboard_endpoint(db: Session = Depends(get_db)) -> DashboardResponse:
    try:
        data = get_dashboard(db)
        return DashboardResponse(**data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculando dashboard de pagos",
        )


@router.get(
    "/auditoria/reportes",
    response_model=List[ReporteHistorico],
    summary="Historial de reportes de cierre diario",
    description="Retorna la lista de todos los cierres diarios registrados, ordenados por fecha descendente.",
)
async def get_reportes_endpoint(db: Session = Depends(get_db)) -> List[ReporteHistorico]:
    try:
        data = get_reportes_historicos(db)
        return [ReporteHistorico(**r) for r in data]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error consultando historial de reportes",
        )


@router.get(
    "/auditoria/reportes/{reporte_id}",
    response_model=DetalleReporteHisto,
    summary="Detalle de un reporte de cierre",
    description=(
        "Retorna el detalle completo de un cierre diario por su id: "
        "KPIs históricos calculados desde fact_pagos para esa fecha y "
        "distribución de volumen por método de pago."
    ),
)
async def get_detalle_reporte_endpoint(
    reporte_id: int,
    db: Session = Depends(get_db),
) -> DetalleReporteHisto:
    try:
        data = get_detalle_reporte(db, reporte_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error consultando detalle del reporte",
        )
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reporte {reporte_id} no encontrado",
        )
    return DetalleReporteHisto(**data)


@router.get(
    "/auditoria/cierres",
    response_model=List[CierreDescuadrePoint],
    summary="Descuadre reportado-vs-interno de cierres diarios",
    description=(
        "Retorna los últimos N cierres diarios en orden cronológico ascendente, con el "
        "total y conteo reportado por el origen frente al interno conciliado. "
        "Los campos internos son null cuando el cierre aún no se concilió."
    ),
)
async def get_cierres_endpoint(
    limit: int = Query(default=30, ge=1, le=180, description="Máximo de cierres a retornar (1–180)"),
    db: Session = Depends(get_db),
) -> List[CierreDescuadrePoint]:
    try:
        data = get_cierres_descuadre(db, limit=limit)
        return [CierreDescuadrePoint(**c) for c in data]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error consultando descuadre de cierres",
        )


@router.post(
    "/auditoria/reportes/generar",
    response_model=GenerarReporteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar reporte de cierre del día actual",
    description=(
        "Dispara el cierre diario del día en curso: calcula los totales aprobados "
        "desde fact_pagos y persiste el resultado en cierre_diario."
    ),
)
async def generar_reporte_endpoint(db: Session = Depends(get_db)) -> GenerarReporteResponse:
    try:
        generar_reporte_hoy(db)
        return GenerarReporteResponse(success=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generando reporte diario",
        )
