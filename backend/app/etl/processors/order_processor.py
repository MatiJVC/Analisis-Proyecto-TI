from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import RawEvent, FactOrder


class OrderPayloadValidationError(Exception):
    pass


def _validate_order_payload(payload: Dict[str, Any]) -> None:
    required_fields = ["order_id", "customer_id"]
    
    for field in required_fields:
        if field not in payload or payload[field] is None:
            raise OrderPayloadValidationError(
                f"Campo requerido faltante: {field}"
            )


def _map_event_to_flags(event_type: str) -> Dict[str, bool]:

    flags = {}
    
    if event_type == "pedido_pagado":
        flags["payment_success"] = True
    elif event_type == "pago_fallido":
        flags["payment_success"] = False
    elif event_type == "stock_reservado":
        flags["stock_reserved"] = True
    elif event_type == "pedido_entregado":
        flags["delivery_completed"] = True
    elif event_type == "stock_agotado":
        flags["stock_reserved"] = False
    
    return flags


def process_order_event(db: Session, raw_event: RawEvent) -> Optional[FactOrder]:

    try:
        # 1. Validar payload
        _validate_order_payload(raw_event.payload)
        
        # 2. Extraer datos del payload
        order_id = raw_event.payload.get("order_id")
        customer_id = raw_event.payload.get("customer_id")
        sales_channel = raw_event.payload.get("sales_channel", "unknown")
        total_amount = raw_event.payload.get("total_amount", 0.0)
        total_items = raw_event.payload.get("total_items", 0)
        
        # Parsear created_at si viene en el payload (para testing)
        payload_created_at = raw_event.payload.get("created_at")
        if payload_created_at:
            try:
                created_at = datetime.fromisoformat(payload_created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.utcnow()
        else:
            created_at = datetime.utcnow()
        
        # 3. Buscar FactOrder existente por order_id
        existing = db.query(FactOrder).filter(
            FactOrder.order_id == order_id
        ).first()
        
        if existing:
            # Actualizar registro existente
            fact_order = existing
            print(f"[ORDER-ETL] Actualizando orden {order_id}")
        else:
            # Crear nuevo registro
            fact_order = FactOrder(
                order_id=order_id,
                customer_id=customer_id,
                sales_channel=sales_channel,
                status="created",  # Status inicial
                total_amount=total_amount,
                total_items=total_items,
                payment_success=False,
                stock_reserved=False,
                delivery_completed=False,
                created_at=created_at,
                updated_at=datetime.utcnow()
            )
            db.add(fact_order)
            print(f"[ORDER-ETL] Creando nueva orden {order_id}")
        
        # 4. Mapear flags según event_type
        flags = _map_event_to_flags(raw_event.event_type)
        
        # Aplicar flags al registro
        for flag_name, flag_value in flags.items():
            if hasattr(fact_order, flag_name):
                setattr(fact_order, flag_name, flag_value)
        
        # 5. Actualizar status según event_type
        if raw_event.event_type == "pedido_creado":
            fact_order.status = "created"
        elif raw_event.event_type == "stock_reservado":
            fact_order.status = "stock_reserved"
        elif raw_event.event_type == "pedido_pagado":
            fact_order.status = "paid"
        elif raw_event.event_type == "pedido_entregado":
            fact_order.status = "delivered"
        elif raw_event.event_type == "pago_fallido":
            fact_order.status = "payment_failed"
        elif raw_event.event_type == "stock_agotado":
            fact_order.status = "stock_unavailable"
        
        # 6. Actualizar timestamp de modificación
        fact_order.updated_at = datetime.utcnow()
        
        # 7. Calcular processing_time_seconds si se entrega
        if raw_event.event_type == "pedido_entregado" and fact_order.created_at:
            delta = fact_order.updated_at - fact_order.created_at
            fact_order.processing_time_seconds = int(delta.total_seconds())
        
        # 7. Persistir en BD
        db.add(fact_order)
        db.flush()
        
        print(f"[ORDER-ETL] Evento {raw_event.event_type} procesado para orden {order_id}")
        
        return fact_order
    
    except OrderPayloadValidationError as e:
        print(f"[ORDER-ETL] Error validación: {str(e)}")
        raise
    
    except Exception as e:
        print(f"[ORDER-ETL] Error procesando evento {raw_event.id}: {str(e)}")
        raise


def process_orders_events(db: Session, limit: int = 1000) -> Dict[str, Any]:

    stats = {
        "total": 0,
        "processed": 0,
        "errors": 0,
        "event_types": {}
    }
    
    try:
        # 1. Obtener eventos sin procesar del dominio orders
        unprocessed = db.query(RawEvent).filter(
            RawEvent.source == "orders",
            RawEvent.processed == False
        ).limit(limit).all()
        
        stats["total"] = len(unprocessed)
        print(f"\n[ORDER-ETL] Iniciando procesamiento de {stats['total']} eventos\n")
        
        if not unprocessed:
            print("[ORDER-ETL] No hay eventos sin procesar")
            return stats
        
        # 2. Procesar cada evento
        for raw_event in unprocessed:
            try:
                process_order_event(db, raw_event)
                
                # Marcar como procesado
                raw_event.processed = True
                db.add(raw_event)
                
                stats["processed"] += 1
                event_type = raw_event.event_type
                stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1
                
            except OrderPayloadValidationError:
                stats["errors"] += 1
                raw_event.processed = True
                db.add(raw_event)
            except Exception as e:
                stats["errors"] += 1
                print(f"[ORDER-ETL] Error: {str(e)}")
        
        # 3. Commit final
        db.commit()
        
        # 4. Mostrar resumen
        print(f"\n[ORDER-ETL] === RESUMEN ===")
        print(f"[ORDER-ETL] Total procesados: {stats['processed']}")
        print(f"[ORDER-ETL] Errores: {stats['errors']}")
        print(f"[ORDER-ETL] Tipos de eventos: {stats['event_types']}\n")
        
        return stats
    
    except Exception as e:
        db.rollback()
        print(f"[ORDER-ETL] Error crítico: {str(e)}")
        raise
