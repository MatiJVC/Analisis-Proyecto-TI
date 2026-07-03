import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import RawEvent, FactIoT

logger = logging.getLogger(__name__)


class IoTPayloadValidationError(Exception):
    pass


def _validate_iot_payload(payload: Dict[str, Any]) -> None:
    """Valida que el payload tenga los campos requeridos."""
    required_fields = ["sensor_id", "asset_id", "sensor_type"]
    
    for field in required_fields:
        if field not in payload or payload[field] is None:
            raise IoTPayloadValidationError(
                f"Campo requerido faltante: {field}"
            )


def _detect_anomaly(event_type: str, payload: Dict[str, Any]) -> bool:
    """Detecta si hay anomalía basado en el tipo de evento."""
    anomaly_events = [
        "out_of_range",
        "anomaly_detected",
        "sensor_offline",
        "signal_lost",
        "low_battery"
    ]
    return event_type in anomaly_events


def _parse_timestamp(timestamp_str: Optional[str]) -> datetime:
    """Parsea timestamp del payload o retorna ahora."""
    if not timestamp_str:
        return datetime.now(tz=timezone.utc)
    
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except:
        return datetime.now(tz=timezone.utc)


def process_iot_event(db: Session, raw_event: RawEvent) -> Optional[FactIoT]:
    """
    Procesa un evento IoT y lo convierte en FactIoT.
    
    Soporta eventos:
    - telemetry_received: Datos de telemetría normales
    - sensor_offline: Sensor está offline
    - low_battery: Batería baja
    - out_of_range: Lectura fuera de rango
    - signal_lost: Señal perdida
    - gps_updated: Ubicación actualizada
    - anomaly_detected: Anomalía detectada
    """
    
    try:
        # 1. Validar payload
        _validate_iot_payload(raw_event.payload)
        
        # 2. Extraer datos del payload
        sensor_id = raw_event.payload.get("sensor_id")
        asset_id = raw_event.payload.get("asset_id")
        sensor_type = raw_event.payload.get("sensor_type")
        location = raw_event.payload.get("location")
        battery = raw_event.payload.get("battery")
        signal_strength = raw_event.payload.get("signal_strength")
        
        # Datos específicos por tipo de sensor
        temperature = raw_event.payload.get("temperature")
        humidity = raw_event.payload.get("humidity")
        acceleration = raw_event.payload.get("acceleration")
        connection_status = raw_event.payload.get("connection_status")
        
        # Timestamp del evento
        event_timestamp = _parse_timestamp(raw_event.payload.get("timestamp"))
        
        # 3. Buscar FactIoT existente por sensor_id
        existing = db.query(FactIoT).filter(
            FactIoT.sensor_id == sensor_id
        ).first()
        
        if existing:
            # Actualizar registro existente
            fact_iot = existing
            logger.info("IoT-ETL actualizando sensor %s", sensor_id)
        else:
            # Crear nuevo registro
            fact_iot = FactIoT(
                sensor_id=sensor_id,
                asset_id=asset_id,
                sensor_type=sensor_type,
                location=location,
                battery_level=battery,
                signal_strength=signal_strength,
                is_online=True,
                has_anomaly=False,
                low_battery_alert=False,
                created_at=event_timestamp,
                updated_at=datetime.now(tz=timezone.utc)
            )
            db.add(fact_iot)
            logger.info("IoT-ETL creando nuevo sensor %s", sensor_id)

        # Latencia real: tiempo entre ingestión del evento y cierre del ETL.
        fact_iot.last_ingested_at = raw_event.ingested_at
        
        # 4. Actualizar datos según event_type
        if raw_event.event_type == "telemetry_received":
            # Datos de telemetría normales
            fact_iot.temperature = temperature
            fact_iot.humidity = humidity
            fact_iot.acceleration = acceleration
            fact_iot.battery_level = battery
            fact_iot.signal_strength = signal_strength
            fact_iot.connection_status = connection_status or "connected"
            fact_iot.is_online = True
            fact_iot.low_battery_alert = battery is not None and battery < 20
            fact_iot.has_anomaly = fact_iot.low_battery_alert
            fact_iot.last_data_received_at = event_timestamp
            
        elif raw_event.event_type == "sensor_offline":
            # Sensor está offline
            fact_iot.is_online = False
            fact_iot.connection_status = "offline"
            fact_iot.has_anomaly = True
            
        elif raw_event.event_type == "low_battery":
            # Batería baja
            fact_iot.battery_level = raw_event.payload.get("battery", battery)
            fact_iot.low_battery_alert = True
            fact_iot.has_anomaly = True
            
        elif raw_event.event_type == "out_of_range":
            # Lectura fuera de rango
            fact_iot.has_anomaly = True
            current_value = raw_event.payload.get("current_value")
            if sensor_type == "temperature" and current_value is not None:
                fact_iot.temperature = current_value
            elif sensor_type == "humidity" and current_value is not None:
                fact_iot.humidity = current_value
                
        elif raw_event.event_type == "signal_lost":
            # Señal perdida
            fact_iot.signal_strength = raw_event.payload.get("signal_strength", signal_strength)
            fact_iot.has_anomaly = True
            
        elif raw_event.event_type == "gps_updated":
            # Ubicación actualizada
            fact_iot.location = raw_event.payload.get("location", location)
            fact_iot.last_data_received_at = event_timestamp
            
        elif raw_event.event_type == "anomaly_detected":
            # Anomalía detectada
            fact_iot.has_anomaly = True
            severity = raw_event.payload.get("severity", "warning")
            if severity == "critical":
                fact_iot.is_online = False
        
        # 5. Guardar datos extra (JSONB)
        if raw_event.payload.get("extra_data"):
            fact_iot.extra_data = raw_event.payload.get("extra_data")
        
        # 6. Actualizar timestamp de modificación
        fact_iot.updated_at = datetime.now(tz=timezone.utc)
        
        # 7. Persistir en BD
        db.add(fact_iot)
        db.flush()
        
        logger.info("IoT-ETL evento %s procesado para sensor %s", raw_event.event_type, sensor_id)
        
        return fact_iot
    
    except IoTPayloadValidationError as e:
        logger.warning("IoT-ETL error validación: %s", e)
        raise

    except Exception as e:
        logger.exception("IoT-ETL error procesando evento %s", raw_event.event_id)
        raise


def process_iot_events(db: Session, limit: int = 1000) -> Dict[str, Any]:
    """
    Procesa todos los eventos IoT sin procesar.
    Retorna estadísticas del procesamiento.
    """
    
    stats = {
        "total": 0,
        "processed": 0,
        "errors": 0,
        "event_types": {}
    }
    
    try:
        # 1. Obtener eventos sin procesar del dominio iot_devices
        unprocessed = db.query(RawEvent).filter(
            RawEvent.source == "iot_devices",
            RawEvent.processed == False
        ).limit(limit).all()
        
        stats["total"] = len(unprocessed)
        
        # 2. Procesar cada evento
        for raw_event in unprocessed:
            try:
                process_iot_event(db, raw_event)
                
                # Marcar como procesado
                raw_event.processed = True
                db.add(raw_event)
                
                stats["processed"] += 1
                
                # Contar por tipo de evento
                event_type = raw_event.event_type
                stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1
                
            except Exception as e:
                stats["errors"] += 1
                logger.exception("IoT-ETL error procesando evento %s", raw_event.event_id)
                db.rollback()

        # 3. Commit de todos los cambios
        db.commit()

        logger.info("IoT-ETL procesamiento completado: %s/%s eventos", stats['processed'], stats['total'])

        return stats

    except Exception as e:
        logger.exception("IoT-ETL error en batch processing")
        db.rollback()
        raise
