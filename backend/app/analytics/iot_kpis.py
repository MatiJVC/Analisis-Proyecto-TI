"""
KPIs para cálculos analíticos del dominio IoT.

Contiene funciones para calcular KPIs desde fact_iot y raw_events.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Integer, case
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

from app.models import FactIoT, RawEvent


# ================================================================
# FUNCIONES DE CÁLCULO DE KPIs BÁSICOS
# ================================================================

def get_total_sensors(db: Session, days: Optional[int] = None) -> int:
    """Obtiene cantidad total de sensores únicos."""
    query = db.query(func.count(func.distinct(FactIoT.sensor_id)))
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.created_at >= cutoff_date)
    return query.scalar() or 0


def get_online_sensors(db: Session, days: Optional[int] = None) -> int:
    """Obtiene cantidad de sensores actualmente online."""
    query = db.query(func.count(func.distinct(FactIoT.sensor_id))).filter(
        FactIoT.is_online == True
    )
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.updated_at >= cutoff_date)
    return query.scalar() or 0


def get_offline_sensors(db: Session, days: Optional[int] = None) -> int:
    """Obtiene cantidad de sensores actualmente offline."""
    query = db.query(func.count(func.distinct(FactIoT.sensor_id))).filter(
        FactIoT.is_online == False
    )
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.updated_at >= cutoff_date)
    return query.scalar() or 0


def get_availability_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula tasa de disponibilidad.
    Fórmula: COUNT(is_online=TRUE) / COUNT(DISTINCT sensor_id)
    
    Rango: 0.0 a 1.0
    """
    total = get_total_sensors(db, days)
    online = get_online_sensors(db, days)
    
    if total == 0:
        return 0.0
    
    return round(online / total, 2)


def get_avg_battery_level(db: Session, days: Optional[int] = None) -> float:
    """Obtiene nivel promedio de batería (%). Retorna 0-100."""
    query = db.query(func.avg(FactIoT.battery_level)).filter(
        FactIoT.battery_level.isnot(None)
    )
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.updated_at >= cutoff_date)
    
    result = query.scalar()
    return round(result, 1) if result else 0.0


def get_low_battery_count(db: Session, days: Optional[int] = None, threshold: int = 20) -> int:
    """
    Obtiene cantidad de sensores con batería baja.
    Por defecto: battery_level < 20%
    """
    query = db.query(func.count(func.distinct(FactIoT.sensor_id))).filter(
        FactIoT.battery_level.isnot(None),
        FactIoT.battery_level < threshold
    )
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.updated_at >= cutoff_date)
    
    return query.scalar() or 0


def get_data_validity_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula porcentaje de datos válidos (sin anomalías).
    Fórmula: COUNT(has_anomaly=FALSE) / COUNT(DISTINCT sensor_id)
    
    Rango: 0.0 a 1.0
    """
    total_query = db.query(func.count(func.distinct(FactIoT.sensor_id)))
    valid_query = db.query(func.count(func.distinct(FactIoT.sensor_id))).filter(
        FactIoT.has_anomaly == False
    )
    
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        total_query = total_query.filter(FactIoT.updated_at >= cutoff_date)
        valid_query = valid_query.filter(FactIoT.updated_at >= cutoff_date)
    
    total = total_query.scalar() or 0
    valid = valid_query.scalar() or 0
    
    if total == 0:
        return 0.0
    
    return round(valid / total, 2)


def get_anomalies_detected(db: Session, days: Optional[int] = None) -> int:
    """Obtiene cantidad de sensores con anomalías detectadas."""
    query = db.query(func.count(func.distinct(FactIoT.sensor_id))).filter(
        FactIoT.has_anomaly == True
    )
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.updated_at >= cutoff_date)
    
    return query.scalar() or 0


def get_avg_processing_latency_ms(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula latencia promedio de procesamiento en milisegundos.
    Basado en diferencia entre created_at y last_data_received_at.
    """
    query = db.query(
        func.avg(
            func.extract('epoch', FactIoT.last_data_received_at - FactIoT.created_at) * 1000
        )
    ).filter(
        FactIoT.last_data_received_at.isnot(None)
    )
    
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.updated_at >= cutoff_date)
    
    result = query.scalar()
    return round(result, 1) if result else 0.0


# ================================================================
# KPI CONSOLIDADO
# ================================================================

def get_all_iot_kpis(db: Session, days: Optional[int] = None) -> Dict[str, any]:
    """
    Retorna todos los KPIs de IoT consolidados.
    
    KPIs real-time (ignoran días):
    - total_sensors, online_sensors, offline_sensors, availability_rate
    - avg_battery_level, low_battery_count
    
    KPIs con filtro de días (usan parámetro days):
    - data_validity_rate, anomalies_detected, avg_processing_latency_ms
    """
    
    # Real-time siempre (sin filtro de días)
    total_sensors = get_total_sensors(db)
    online_sensors = get_online_sensors(db)
    offline_sensors = get_offline_sensors(db)
    availability_rate = get_availability_rate(db)
    avg_battery_level = get_avg_battery_level(db)
    low_battery_count = get_low_battery_count(db)
    
    # Con filtro de días (usan el parámetro days si se proporciona)
    data_validity_rate = get_data_validity_rate(db, days)
    anomalies_detected = get_anomalies_detected(db, days)
    avg_processing_latency_ms = get_avg_processing_latency_ms(db, days)
    
    return {
        "total_sensors": total_sensors,
        "online_sensors": online_sensors,
        "offline_sensors": offline_sensors,
        "availability_rate": availability_rate,
        "avg_battery_level": avg_battery_level,
        "low_battery_count": low_battery_count,
        "data_validity_rate": data_validity_rate,
        "anomalies_detected": anomalies_detected,
        "avg_processing_latency_ms": avg_processing_latency_ms,
    }


# ================================================================
# FUNCIONES DE DETALLE Y TIMELINE
# ================================================================

def get_sensors_status(
    db: Session,
    days: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, any]]:
    """Obtiene estado actual de todos los sensores."""
    query = db.query(
        FactIoT.sensor_id,
        FactIoT.asset_id,
        FactIoT.sensor_type,
        FactIoT.is_online,
        FactIoT.battery_level,
        FactIoT.last_data_received_at,
        FactIoT.location,
        FactIoT.has_anomaly,
        FactIoT.low_battery_alert,
    ).distinct(FactIoT.sensor_id)

    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.updated_at >= cutoff_date)

    query = query.order_by(FactIoT.sensor_id, FactIoT.updated_at.desc())

    results = query.offset(offset).limit(limit).all()
    
    return [
        {
            "sensor_id": row[0],
            "asset_id": row[1],
            "sensor_type": row[2],
            "is_online": row[3],
            "battery_level": row[4],
            "last_reading_at": row[5],
            "location": row[6],
            "has_anomaly": row[7],
            "low_battery_alert": row[8],
        }
        for row in results
    ]


def get_sensors_by_type(db: Session, days: Optional[int] = None) -> List[Dict[str, any]]:
    """Obtiene distribución y estado de sensores por tipo."""
    query = db.query(
        FactIoT.sensor_type,
        func.count(func.distinct(FactIoT.sensor_id)).label("count"),
        func.sum(func.cast(FactIoT.is_online, Integer)).label("online_count"),
        func.count(func.distinct(
            case((FactIoT.is_online == False, FactIoT.sensor_id), else_=None)
        )).label("offline_count"),
        func.avg(FactIoT.battery_level).label("avg_battery"),
        func.count(func.distinct(
            case((FactIoT.has_anomaly == True, FactIoT.sensor_id), else_=None)
        )).label("anomaly_count"),
    ).filter(FactIoT.sensor_type.isnot(None))
    
    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.updated_at >= cutoff_date)
    
    query = query.group_by(FactIoT.sensor_type)
    
    results = query.all()
    
    return [
        {
            "sensor_type": row[0],
            "count": row[1] or 0,
            "online_count": row[2] or 0,
            "offline_count": row[3] or 0,
            "avg_battery": round(row[4], 1) if row[4] else 0.0,
            "anomaly_count": row[5] or 0,
        }
        for row in results
    ]


def get_iot_events(db: Session, days: Optional[int] = None, limit: int = 100) -> List[Dict[str, any]]:
    """Obtiene eventos de IoT recientes desde raw_events."""
    query = db.query(
        RawEvent.id,
        RawEvent.source,
        RawEvent.event_type,
        RawEvent.ingested_at,
        RawEvent.payload,
    ).filter(RawEvent.source == "iot_devices")

    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(RawEvent.ingested_at >= cutoff_date)

    query = query.order_by(RawEvent.ingested_at.desc()).limit(limit)
    
    results = query.all()
    
    return [
        {
            "event_id": row[0],
            "sensor_id": row[4].get("sensor_id") if row[4] else None,
            "event_type": row[2],
            "timestamp": row[3],
            "severity": "critical" if row[2] in ["sensor_offline", "low_battery"] else "warning" if row[2] in ["out_of_range", "signal_lost"] else "info",
            "message": f"Evento: {row[2]}",
            "data": row[4],
        }
        for row in results
    ]


def get_iot_timeline(db: Session, days: int = 30) -> List[Dict[str, any]]:
    """Obtiene timeline de actividad IoT agrupada por fecha."""
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
    
    query = db.query(
        cast(FactIoT.updated_at, Date).label("date"),
        func.count(func.distinct(FactIoT.sensor_id)).label("sensors_count"),
        func.sum(func.cast(FactIoT.is_online, Integer)).label("sensors_online"),
        func.count(func.distinct(
            func.case((FactIoT.is_online == False, FactIoT.sensor_id))
        )).label("sensors_offline"),
        func.avg(FactIoT.battery_level).label("avg_battery"),
        func.count(func.distinct(
            func.case((FactIoT.has_anomaly == True, FactIoT.sensor_id))
        )).label("anomalies"),
    ).filter(
        FactIoT.updated_at >= cutoff_date
    ).group_by(
        cast(FactIoT.updated_at, Date)
    ).order_by(
        cast(FactIoT.updated_at, Date).asc()
    )
    
    results = query.all()
    
    return [
        {
            "date": str(row[0]),
            "events_count": 0,  # Podría calcularse desde raw_events si es necesario
            "sensors_online": row[2] or 0,
            "sensors_offline": row[3] or 0,
            "avg_battery": round(row[4], 1) if row[4] else 0.0,
            "anomalies": row[5] or 0,
        }
        for row in results
    ]


# ================================================================
# FUNCIÓN BATCH PARA PROCESAR EVENTOS SIN PROCESAR
# ================================================================

def process_unprocessed_iot_events(db: Session, limit: int = 1000) -> Dict[str, any]:
    """
    Procesa eventos IoT sin procesar y actualiza fact_iot.
    Retorna estadísticas del procesamiento.
    """
    
    stats = {
        "total": 0,
        "processed": 0,
        "errors": 0,
        "event_types": {}
    }
    
    from app.etl.processors.iot_processor import process_iot_event
    
    try:
        # Obtener eventos sin procesar
        unprocessed = db.query(RawEvent).filter(
            RawEvent.source == "iot_devices",
            RawEvent.processed == False
        ).limit(limit).all()
        
        stats["total"] = len(unprocessed)
        
        for raw_event in unprocessed:
            try:
                process_iot_event(db, raw_event)
                raw_event.processed = True
                db.add(raw_event)
                
                stats["processed"] += 1
                event_type = raw_event.event_type
                stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1
                
            except Exception as e:
                stats["errors"] += 1
                logger.exception("IoT-KPI error procesando evento %s", raw_event.id)
                db.rollback()

        db.commit()

    except Exception as e:
        logger.exception("IoT-KPI error en batch processing")
        db.rollback()
        raise
    
    return stats
