"""
Consultas analíticas sobre el warehouse de salud (dims + facts).
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, nullslast
from sqlalchemy.orm import Session

from app.models.warehouse import (
    DimPacientes,
    DimProfesionales,
    DimZonas,
    FactVisitas,
)


def get_salud_dashboard_summary(db: Session) -> Dict[str, Any]:
    active_patients = (
        db.query(func.count(DimPacientes.id))
        .filter(and_(DimPacientes.es_actual == True))
        .scalar()
        or 0
    )

    today = date.today()
    today_visits = (
        db.query(func.count(FactVisitas.id))
        .filter(FactVisitas.fecha_programada == today)
        .scalar()
        or 0
    )

    healthcare_staff = (
        db.query(func.count(DimProfesionales.id))
        .filter(
            and_(
                DimProfesionales.es_actual == True,
                DimProfesionales.activo == True,
            )
        )
        .scalar()
        or 0
    )

    avg_minutes: Optional[float] = (
        db.query(func.avg(FactVisitas.duracion_minutos))
        .filter(
            and_(
                FactVisitas.completada == 1,
                FactVisitas.duracion_minutos.isnot(None),
            )
        )
        .scalar()
    )
    if avg_minutes is not None:
        avg_minutes = round(float(avg_minutes), 1)

    coverage_zones = (
        db.query(func.count(DimZonas.id))
        .filter(and_(DimZonas.es_actual == True, DimZonas.activa == True))
        .scalar()
        or 0
    )

    return {
        "active_patients": int(active_patients),
        "today_visits": int(today_visits),
        "healthcare_staff": int(healthcare_staff),
        "avg_visit_time_minutes": avg_minutes,
        "coverage_zones": int(coverage_zones),
        "satisfaction_score": None,
    }


def get_salud_visit_trends(db: Session, days: int = 14) -> Dict[str, Any]:
    if days < 1:
        days = 14
    if days > 90:
        days = 90

    end = date.today()
    start = end - timedelta(days=days - 1)

    points: List[Dict[str, Any]] = []
    d = start
    while d <= end:
        visits = (
            db.query(func.count(FactVisitas.id))
            .filter(FactVisitas.fecha_programada == d)
            .scalar()
            or 0
        )
        completed = (
            db.query(func.count(FactVisitas.id))
            .filter(and_(FactVisitas.fecha_programada == d, FactVisitas.completada == 1))
            .scalar()
            or 0
        )
        points.append({"date": d.isoformat(), "visits": int(visits), "completed": int(completed)})
        d += timedelta(days=1)

    return {"days": days, "points": points}


def get_salud_today_schedule(db: Session) -> Dict[str, Any]:
    today = date.today()
    rows = (
        db.query(FactVisitas, DimPacientes, DimProfesionales)
        .join(DimPacientes, DimPacientes.id == FactVisitas.paciente_dim_id)
        .join(DimProfesionales, DimProfesionales.id == FactVisitas.profesional_dim_id)
        .filter(FactVisitas.fecha_programada == today)
        .order_by(nullslast(FactVisitas.hora_programada))
        .all()
    )

    visits: List[Dict[str, Any]] = []
    for fv, pac, prof in rows:
        t = fv.hora_programada
        if t is not None:
            time_display = f"{t.hour:02d}:{t.minute:02d}"
        else:
            time_display = "--:--"
        visits.append(
            {
                "visita_id": str(fv.visita_id),
                "time_display": time_display,
                "patient": f"{pac.nombres} {pac.apellidos}".strip(),
                "visit_type": fv.estado or "visita",
                "professional": f"{prof.nombres} {prof.apellidos}".strip(),
                "status": (fv.estado or "scheduled").lower().replace(" ", "-"),
            }
        )

    return {"date": today.isoformat(), "visits": visits}
