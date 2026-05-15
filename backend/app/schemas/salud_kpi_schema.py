from typing import List, Optional

from pydantic import BaseModel, Field


class SaludDashboardSummary(BaseModel):
    """KPIs agregados para el dashboard de salud (home health)."""

    active_patients: int = Field(..., description="Pacientes con registro actual en dim_pacientes")
    today_visits: int = Field(..., description="Visitas con fecha_programada = hoy")
    healthcare_staff: int = Field(..., description="Profesionales activos y versión actual en dim")
    avg_visit_time_minutes: Optional[float] = Field(
        None, description="Promedio de duracion_minutos en visitas completadas"
    )
    coverage_zones: int = Field(..., description="Zonas activas en dim_zonas")
    satisfaction_score: Optional[float] = Field(
        None,
        description="No modelado en DWH; reservado para integración futura o encuestas",
    )


class SaludVisitTrendPoint(BaseModel):
    date: str
    visits: int
    completed: int


class SaludVisitTrendsResponse(BaseModel):
    days: int
    points: List[SaludVisitTrendPoint]


class SaludTodayVisitRow(BaseModel):
    visita_id: str
    time_display: str
    patient: str
    visit_type: str
    professional: str
    status: str


class SaludTodayScheduleResponse(BaseModel):
    date: str
    visits: List[SaludTodayVisitRow]
