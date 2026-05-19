from typing import List, Optional

from pydantic import BaseModel, Field


class GlobalKPIsResponse(BaseModel):
    totalOrders: int
    deliveryRate: float = Field(..., description="Porcentaje de entregas exitosas (0-100)")
    revenue: float
    notificationSuccessRate: float = Field(0.0, description="Reservado para módulo notifications")
    activeSubscriptions: int
    iotAlerts: int = Field(0, description="Reservado para módulo iot")
    incidentCount: int = Field(..., description="Incidentes activos")
    paymentFailureRate: float = Field(..., description="Porcentaje de pagos fallidos (0-100)")


class ServiceStatusRow(BaseModel):
    name: str
    status: str
    uptime: float
    lastIncident: Optional[str] = None


class ActivityRow(BaseModel):
    id: str
    type: str
    message: str
    timestamp: str
    status: str


class AlertRow(BaseModel):
    id: str
    title: str
    message: str
    severity: str
    source: str
    timestamp: str
