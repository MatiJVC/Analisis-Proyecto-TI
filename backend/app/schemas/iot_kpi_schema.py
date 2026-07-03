"""
Schemas Pydantic para respuestas de analítica de IoT.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ============ Event Types ============
class IoTEventType:
    """Tipos de eventos soportados por el sistema IoT."""
    
    TELEMETRY_RECEIVED = "telemetry_received"
    GPS_UPDATED = "gps_updated"
    SENSOR_OFFLINE = "sensor_offline"
    LOW_BATTERY = "low_battery"
    OUT_OF_RANGE = "out_of_range"
    SIGNAL_LOST = "signal_lost"
    ANOMALY_DETECTED = "anomaly_detected"


# ============ KPIs Response ============
class SensorKPIs(BaseModel):
    """KPIs consolidados para sensores IoT."""
    
    total_sensors: int = Field(..., description="Cantidad total de sensores")
    online_sensors: int = Field(..., description="Sensores actualmente online")
    offline_sensors: int = Field(..., description="Sensores actualmente offline")
    availability_rate: float = Field(..., ge=0.0, le=1.0, description="Tasa de disponibilidad (0.0-1.0)")
    avg_battery_level: float = Field(..., ge=0.0, le=100.0, description="Nivel promedio de batería (%)")
    low_battery_count: int = Field(..., description="Cantidad de sensores con batería baja")
    data_validity_rate: float = Field(..., ge=0.0, le=1.0, description="Porcentaje de datos válidos (0.0-1.0)")
    anomalies_detected: int = Field(..., description="Cantidad de anomalías detectadas")
    avg_processing_latency_seconds: float = Field(..., ge=0.0, description="Latencia promedio de procesamiento (s)")
    avg_processing_latency_ms: float = Field(..., description="Latencia promedio de procesamiento (ms)")

    class Config:
        json_schema_extra = {
            "example": {
                "total_sensors": 50,
                "online_sensors": 48,
                "offline_sensors": 2,
                "availability_rate": 0.96,
                "avg_battery_level": 75.3,
                "low_battery_count": 5,
                "data_validity_rate": 0.98,
                "anomalies_detected": 2,
                "avg_processing_latency_seconds": 0.045,
                "avg_processing_latency_ms": 45.2
            }
        }


# ============ Sensor Status ============
class SensorStatus(BaseModel):
    """Estado actual de un sensor."""
    
    sensor_id: str
    asset_id: str
    sensor_type: str
    is_online: bool
    battery_level: Optional[float] = None
    last_reading_at: Optional[datetime] = None
    location: Optional[str] = None
    has_anomaly: bool = False
    low_battery_alert: bool = False


class SensorsStatusResponse(BaseModel):
    """Response con estado de todos los sensores."""
    
    total_sensors: int
    online_count: int
    offline_count: int
    sensors: List[SensorStatus]

    class Config:
        json_schema_extra = {
            "example": {
                "total_sensors": 50,
                "online_count": 48,
                "offline_count": 2,
                "sensors": [
                    {
                        "sensor_id": "SENSOR_001",
                        "asset_id": "ASSET_A",
                        "sensor_type": "temperature",
                        "is_online": True,
                        "battery_level": 85.5,
                        "last_reading_at": "2026-05-24T12:30:00",
                        "location": "Warehouse - Section A",
                        "has_anomaly": False,
                        "low_battery_alert": False
                    }
                ]
            }
        }


# ============ Sensor by Type ============
class SensorTypeMetric(BaseModel):
    """Métrica para un tipo de sensor."""
    
    sensor_type: str
    count: int
    online_count: int
    offline_count: int
    avg_battery: float
    anomaly_count: int


class SensorsByTypeResponse(BaseModel):
    """Response con distribución de sensores por tipo."""
    
    total_sensors: int
    sensor_types: List[SensorTypeMetric]

    class Config:
        json_schema_extra = {
            "example": {
                "total_sensors": 50,
                "sensor_types": [
                    {
                        "sensor_type": "temperature",
                        "count": 20,
                        "online_count": 20,
                        "offline_count": 0,
                        "avg_battery": 78.5,
                        "anomaly_count": 1
                    },
                    {
                        "sensor_type": "gps",
                        "count": 15,
                        "online_count": 14,
                        "offline_count": 1,
                        "avg_battery": 72.3,
                        "anomaly_count": 0
                    }
                ]
            }
        }


# ============ Events & Alerts ============
class SensorEvent(BaseModel):
    """Evento de sensor."""
    
    event_id: Optional[int] = None
    sensor_id: str
    event_type: str
    timestamp: datetime
    severity: str  # info, warning, critical
    message: str
    data: Optional[dict] = None


class EventsResponse(BaseModel):
    """Response con eventos recientes."""
    
    total_events: int
    critical_count: int
    warning_count: int
    info_count: int
    events: List[SensorEvent]

    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 5,
                "critical_count": 1,
                "warning_count": 2,
                "info_count": 2,
                "events": [
                    {
                        "event_id": 1,
                        "sensor_id": "SENSOR_005",
                        "event_type": "sensor_offline",
                        "timestamp": "2026-05-24T12:25:00",
                        "severity": "critical",
                        "message": "Sensor SENSOR_005 is offline",
                        "data": {}
                    }
                ]
            }
        }


# ============ Timeline ============
class TimelinePoint(BaseModel):
    """Punto en línea de tiempo de IoT."""
    
    date: str = Field(..., description="Fecha en formato YYYY-MM-DD")
    events_count: int
    sensors_online: int
    sensors_offline: int
    avg_battery: float
    anomalies: int


class IoTTimelineResponse(BaseModel):
    """Response para timeline de actividad IoT."""
    
    start_date: str
    end_date: str
    total_events: int
    timeline: List[TimelinePoint]

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2026-05-20",
                "end_date": "2026-05-24",
                "total_events": 245,
                "timeline": [
                    {
                        "date": "2026-05-24",
                        "events_count": 52,
                        "sensors_online": 48,
                        "sensors_offline": 2,
                        "avg_battery": 75.3,
                        "anomalies": 1
                    }
                ]
            }
        }
