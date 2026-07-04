"""
KPIs para cálculos analíticos del dominio IoT.

Contiene funciones para calcular KPIs desde fact_iot y raw_events.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Integer, case
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

from app.models import FactIoT, RawEvent


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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


def _get_latest_iot_rows(db: Session, days: Optional[int] = None) -> List[Dict[str, any]]:
    """Obtiene la última fila conocida por sensor, ordenada por recencia."""
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
        FactIoT.updated_at,
        FactIoT.id,
    )

    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.updated_at >= cutoff_date)

    rows = query.order_by(
        FactIoT.sensor_id,
        FactIoT.updated_at.desc(),
        FactIoT.id.desc(),
    ).all()

    latest_by_sensor = {}
    for (
        sensor_id,
        asset_id,
        sensor_type,
        is_online,
        battery_level,
        last_data_received_at,
        location,
        has_anomaly,
        low_battery_alert,
        updated_at,
        row_id,
    ) in rows:
        if sensor_id not in latest_by_sensor:
            latest_by_sensor[sensor_id] = {
                "sensor_id": sensor_id,
                "asset_id": asset_id,
                "sensor_type": sensor_type,
                "is_online": is_online,
                "battery_level": battery_level,
                "last_reading_at": last_data_received_at,
                "location": location,
                "has_anomaly": bool(has_anomaly),
                "low_battery_alert": bool(low_battery_alert),
                "updated_at": _to_utc(updated_at),
                "id": row_id,
            }

    return list(latest_by_sensor.values())


def get_data_validity_rate(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula porcentaje de datos válidos usando el último estado por sensor.
    Fórmula: COUNT(último has_anomaly=FALSE) / COUNT(DISTINCT sensor_id)
    
    Rango: 0.0 a 1.0
    """
    latest_rows = _get_latest_iot_rows(db, days)
    total = len(latest_rows)
    valid = sum(1 for row in latest_rows if not row["has_anomaly"])
    
    if total == 0:
        return 0.0
    
    return round(valid / total, 2)


def get_anomalies_detected(db: Session, days: Optional[int] = None) -> int:
    """Obtiene cantidad de sensores con anomalías en su último estado."""
    latest_rows = _get_latest_iot_rows(db, days)
    return sum(1 for row in latest_rows if row["has_anomaly"])


def get_avg_processing_latency_seconds(db: Session, days: Optional[int] = None) -> float:
    """
    Calcula la latencia promedio real en segundos.
    Usa la diferencia entre last_data_received_at y updated_at.
    """
    query = db.query(
        func.avg(
            func.extract('epoch', FactIoT.updated_at - FactIoT.last_data_received_at)
        )
    ).filter(
        FactIoT.last_data_received_at.isnot(None)
    )

    if days:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
        query = query.filter(FactIoT.last_data_received_at >= cutoff_date)

    result = query.scalar()
    return round(result, 3) if result else 0.0


def get_avg_processing_latency_ms(db: Session, days: Optional[int] = None) -> float:
    """Compatibilidad: devuelve la misma latencia expresada en milisegundos."""
    return round(get_avg_processing_latency_seconds(db, days) * 1000, 1)


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
    - data_validity_rate, anomalies_detected, avg_processing_latency_seconds
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
    avg_processing_latency_seconds = get_avg_processing_latency_seconds(db, days)
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
        "avg_processing_latency_seconds": avg_processing_latency_seconds,
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
    status: str = "all",
    search: Optional[str] = None,
) -> Dict[str, any]:
    """Obtiene el último estado por sensor con paginación y filtro de estado."""
    latest_rows = _get_latest_iot_rows(db, days)

    if search:
        search_term = search.strip().lower()
        if search_term:
            latest_rows = [
                row
                for row in latest_rows
                if search_term in (row["sensor_id"] or "").lower()
                or search_term in (row["asset_id"] or "").lower()
                or search_term in (row["sensor_type"] or "").lower()
            ]

    if status == "active":
        latest_rows = [row for row in latest_rows if row["is_online"]]
    elif status == "inactive":
        latest_rows = [row for row in latest_rows if not row["is_online"]]

    results = latest_rows[offset: offset + limit]
    online_count = sum(1 for row in latest_rows if row["is_online"])
    offline_count = len(latest_rows) - online_count
    
    return {
        "total_sensors": len(latest_rows),
        "online_count": online_count,
        "offline_count": offline_count,
        "sensors": [
            {
                "sensor_id": row["sensor_id"],
                "asset_id": row["asset_id"],
                "sensor_type": row["sensor_type"],
                "is_online": row["is_online"],
                "battery_level": row["battery_level"],
                "last_reading_at": _to_utc(row["last_reading_at"]),
                "location": row["location"],
                "has_anomaly": row["has_anomaly"],
                "low_battery_alert": row["low_battery_alert"],
            }
            for row in results
        ],
    }


def get_sensors_by_type(db: Session, days: Optional[int] = None) -> List[Dict[str, any]]:
    """Obtiene distribución y estado de sensores por tipo usando el último estado por sensor."""
    latest_rows = _get_latest_iot_rows(db, days)
    grouped = {}

    for row in latest_rows:
        sensor_type = row["sensor_type"]
        if not sensor_type:
            continue

        bucket = grouped.setdefault(
            sensor_type,
            {
                "count": 0,
                "online_count": 0,
                "offline_count": 0,
                "battery_total": 0.0,
                "battery_count": 0,
                "anomaly_count": 0,
            },
        )
        bucket["count"] += 1
        bucket["online_count"] += 1 if row["is_online"] else 0
        bucket["offline_count"] += 0 if row["is_online"] else 1
        if row["battery_level"] is not None:
            bucket["battery_total"] += float(row["battery_level"])
            bucket["battery_count"] += 1
        bucket["anomaly_count"] += 1 if row["has_anomaly"] else 0

    results = [
        (
            sensor_type,
            bucket["count"],
            bucket["online_count"],
            bucket["offline_count"],
            (bucket["battery_total"] / bucket["battery_count"]) if bucket["battery_count"] else 0.0,
            bucket["anomaly_count"],
        )
        for sensor_type, bucket in grouped.items()
    ]
    
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
        RawEvent.event_id,
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
            "timestamp": _to_utc(row[3]),
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
                logger.exception("IoT-KPI error procesando evento %s", raw_event.event_id)
                db.rollback()

        db.commit()

    except Exception as e:
        logger.exception("IoT-KPI error en batch processing")
        db.rollback()
        raise
    
    return stats
