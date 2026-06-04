from typing import List

from pydantic import BaseModel, Field


class CRMKPIsResponse(BaseModel):
    totalCustomers: int = Field(..., description="Clientes únicos registrados")
    openTickets: int = Field(..., description="Tickets en estado Abierto o Progreso")
    avgResponseTimeMinutes: float = Field(..., description="Tiempo promedio de resolución en minutos")
    csatScore: float = Field(..., description="Puntaje CSAT promedio (1–5)")
    messagesToday: int = Field(..., description="Interacciones creadas hoy")
    resolutionRate: float = Field(..., description="Porcentaje de tickets cerrados sobre el total")


class CRMTimelinePoint(BaseModel):
    date: str
    opened: int
    resolved: int


class CRMTimelineResponse(BaseModel):
    days: int
    points: List[CRMTimelinePoint]


class CRMTicketRow(BaseModel):
    ticketId: str
    asunto: str
    estado: str
    prioridad: str
    canal: str
    sourceProject: str
    openedAt: str
    updatedAt: str


class CRMTicketsResponse(BaseModel):
    tickets: List[CRMTicketRow]


class CRMSLASummary(BaseModel):
    totalViolations: int
    criticalViolations: int
    slaComplianceRate: float = Field(..., description="Porcentaje de tickets resueltos dentro del SLA")
