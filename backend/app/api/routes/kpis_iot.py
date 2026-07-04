import logging
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_any_role
from app.db import get_db
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
from app.services.iot_analytics_service import (
    get_all_iot_kpis,
    get_sensors_status,
    get_sensors_by_type,
    get_iot_events,
    get_iot_timeline,
)

logger = logging.getLogger(__name__)

IOT_ROLES = ["admin", "analista", "iot"]

router = APIRouter(tags=["kpis — iot"])


@router.get(
    "/iot/kpis",
    dependencies=[Depends(require_any_role(IOT_ROLES))],
    response_model=SensorKPIs,
    summary="KPIs consolidados de sensores IoT",
)
async def get_iot_kpis_endpoint(
    days: Optional[int] = Query(default=None, ge=1, le=365, description="Número de días (omitir para todos los datos)"),
    db: Session = Depends(get_db),
) -> SensorKPIs:
    try:
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
            avg_processing_latency_seconds=kpis["avg_processing_latency_seconds"],
            avg_processing_latency_ms=kpis["avg_processing_latency_ms"],
        )
    except Exception:
        logger.exception("Error calculando IoT KPIs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/iot/status",
    dependencies=[Depends(require_any_role(IOT_ROLES))],
    response_model=SensorsStatusResponse,
    summary="Estado actual de sensores",
)
async def get_iot_sensors_status(
    days: Optional[int] = Query(default=None, ge=1, le=365, description="Número de días (omitir para todos los datos)"),
    status: Literal["all", "active", "inactive"] = Query(default="all", description="Filtro por estado del sensor"),
    search: Optional[str] = Query(default=None, description="Buscar por sensor_id, asset_id o tipo"),
    limit: int = Query(default=100, ge=1, le=1000, description="Máximo de sensores a retornar"),
    offset: int = Query(default=0, ge=0, description="Número de sensores a omitir (paginación)"),
    db: Session = Depends(get_db),
) -> SensorsStatusResponse:
    try:
        status_data = get_sensors_status(db, days=days, limit=limit, offset=offset, status=status, search=search)
        sensors_list = [
            SensorStatus(
                sensor_id=s["sensor_id"],
                asset_id=s["asset_id"],
                sensor_type=s["sensor_type"],
                is_online=s["is_online"],
                battery_level=s["battery_level"],
                last_reading_at=s["last_reading_at"],
                location=s["location"],
                has_anomaly=s["has_anomaly"],
                low_battery_alert=s["low_battery_alert"],
            )
            for s in status_data["sensors"]
        ]
        return SensorsStatusResponse(
            total_sensors=status_data["total_sensors"],
            online_count=status_data["online_count"],
            offline_count=status_data["offline_count"],
            sensors=sensors_list,
        )
    except Exception:
        logger.exception("Error obteniendo estado sensores")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/iot/by-type",
    dependencies=[Depends(require_any_role(IOT_ROLES))],
    response_model=SensorsByTypeResponse,
    summary="Distribución de sensores por tipo",
)
async def get_iot_sensors_by_type(
    days: Optional[int] = Query(default=None, ge=1, le=365, description="Número de días (omitir para todos los datos)"),
    db: Session = Depends(get_db),
) -> SensorsByTypeResponse:
    try:
        types_data = get_sensors_by_type(db, days=days)
        types_list = [
            SensorTypeMetric(
                sensor_type=t["sensor_type"],
                count=t["count"],
                online_count=t["online_count"],
                offline_count=t["offline_count"],
                avg_battery=t["avg_battery"],
                anomaly_count=t["anomaly_count"],
            )
            for t in types_data
        ]
        return SensorsByTypeResponse(
            total_sensors=sum(t.count for t in types_list),
            sensor_types=types_list,
        )
    except Exception:
        logger.exception("Error obteniendo sensores por tipo")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/iot/events",
    dependencies=[Depends(require_any_role(IOT_ROLES))],
    response_model=EventsResponse,
    summary="Eventos recientes de IoT",
)
async def get_iot_events_endpoint(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    limit: int = Query(default=50, ge=1, le=200, description="Máximo de eventos a retornar"),
    db: Session = Depends(get_db),
) -> EventsResponse:
    try:
        events_data = get_iot_events(db, days, limit)
        events_list = [
            SensorEvent(
                event_id=e["event_id"],
                sensor_id=e["sensor_id"],
                event_type=e["event_type"],
                timestamp=e["timestamp"],
                severity=e["severity"],
                message=e["message"],
                data=e["data"],
            )
            for e in events_data
        ]
        return EventsResponse(
            total_events=len(events_list),
            critical_count=sum(1 for e in events_list if e.severity == "critical"),
            warning_count=sum(1 for e in events_list if e.severity == "warning"),
            info_count=sum(1 for e in events_list if e.severity == "info"),
            events=events_list,
        )
    except Exception:
        logger.exception("Error obteniendo eventos IoT")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/iot/timeline",
    dependencies=[Depends(require_any_role(IOT_ROLES))],
    response_model=IoTTimelineResponse,
    summary="Línea de tiempo de IoT",
)
async def get_iot_timeline_endpoint(
    days: int = Query(default=30, ge=1, le=365, description="Número de días en el rango de análisis"),
    db: Session = Depends(get_db),
) -> IoTTimelineResponse:
    try:
        start_date = (datetime.now(tz=timezone.utc) - timedelta(days=days)).date().isoformat()
        end_date = datetime.now(tz=timezone.utc).date().isoformat()
        timeline_data = get_iot_timeline(db, days)
        if not timeline_data:
            return IoTTimelineResponse(start_date=start_date, end_date=end_date, total_events=0, timeline=[])
        return IoTTimelineResponse(
            start_date=start_date,
            end_date=end_date,
            total_events=sum(p["events_count"] for p in timeline_data),
            timeline=[
                TimelinePoint(
                    date=p["date"],
                    events_count=p["events_count"],
                    sensors_online=p["sensors_online"],
                    sensors_offline=p["sensors_offline"],
                    avg_battery=p["avg_battery"],
                    anomalies=p["anomalies"],
                )
                for p in timeline_data
            ],
        )
    except Exception:
        logger.exception("Error calculando IoT timeline")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


@router.get(
    "/iot/health",
    dependencies=[Depends(require_any_role(IOT_ROLES))],
    summary="Health check de analítica IoT",
)
async def iot_health_check(db: Session = Depends(get_db)):
    try:
        kpis = get_all_iot_kpis(db)
        return {
            "status": "healthy",
            "total_sensors": kpis["total_sensors"],
            "online_sensors": kpis["online_sensors"],
            "availability_rate": kpis["availability_rate"],
        }
    except Exception:
        logger.exception("Health check IoT failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Error interno del servidor")
