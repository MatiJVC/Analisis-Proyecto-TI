from typing import List

from pydantic import BaseModel, Field


class IncidentKPIsResponse(BaseModel):
    activeIncidents: int = Field(..., description="Incidentes con status distinto de resolved")
    resolvedToday: int = Field(..., description="Incidentes resueltos hoy (UTC)")
    avgResolutionTime: float = Field(..., description="Promedio de horas hasta resolución")
    slaCompliance: float = Field(..., description="Porcentaje de incidentes resueltos dentro de SLA")
    criticalCount: int = Field(..., description="Incidentes críticos activos")


class IncidentTimelinePoint(BaseModel):
    date: str
    opened: int
    resolved: int
    critical: int


class IncidentTimelineResponse(BaseModel):
    days: int
    points: List[IncidentTimelinePoint]


class IncidentRow(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    assignee: str
    createdAt: str
    updatedAt: str


class IncidentListResponse(BaseModel):
    incidents: List[IncidentRow]
