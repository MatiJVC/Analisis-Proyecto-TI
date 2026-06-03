from pydantic import BaseModel
from typing import Optional


class NotificationKPIs(BaseModel):
    """KPIs principales del dominio notificaciones."""
    total_notifications: int
    failure_rate:        float   # % notificaciones fallidas
    delivery_rate:       float   # % notificaciones entregadas (uptime del servicio)
    backpressure_ratio:  float   # % notificaciones con fallback activado
    avg_attempts:        float   # promedio de intentos por notificación

class ChannelMetric(BaseModel):
    canal: str
    total: int
    delivered_original: int
    delivered_fallback: int
    failed: int
    fallbacks: int
    avg_attempts: float
    delivery_rate: float
    failure_rate: float


class ChannelsResponse(BaseModel):
    """Distribución de notificaciones por canal."""
    total_notifications: int
    channels:            list[ChannelMetric]


class StatusMetric(BaseModel):
    """Distribución por estado."""
    estado:     str
    count:      int
    percentage: float


class StatusResponse(BaseModel):
    """Distribución de notificaciones por estado."""
    total_notifications: int
    statuses:            list[StatusMetric]


class NotificationTimelinePoint(BaseModel):
    """Punto en la línea de tiempo diaria."""
    date:      str
    total:     int
    delivered: int
    failed:    int
    fallbacks: int


class NotificationTimelineResponse(BaseModel):
    """Timeline diario de notificaciones."""
    start_date:          str
    end_date:            str
    total_notifications: int
    timeline:            list[NotificationTimelinePoint]