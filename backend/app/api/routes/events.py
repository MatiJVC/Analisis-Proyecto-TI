from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import EventCreate, EventCreateResponse
from app.services import create_event
from app.etl.processors.order_processor import process_order_event
from app.etl.processors.subscription_processor import process_subscription_event
from app.etl.processors.salud_processor import process_salud_event
from pydantic import ValidationError

from app.pagos.services.payment_service import register_payment_attempt, confirm_payment
from app.pagos.models.fact_payments_events import FactPaymentsEvent
from decimal import Decimal


router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={
        400: {"description": "Invalid event data"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "",
    response_model=EventCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo evento",
    description="Recibe un evento (data lake: raw_events). Procesa automáticamente orders, subscriptions y salud hacia el warehouse cuando aplica."
)
async def create_event_endpoint(
    event: EventCreate,
    db: Session = Depends(get_db)
) -> EventCreateResponse:

    try:
        # 1. Guardar evento en raw_events
        db_event = create_event(db=db, event=event)
        
        # 2. Procesar automáticamente según el dominio
        if db_event.source == "orders":
            try:
                process_order_event(db, db_event)
                db_event.processed = True
                db.commit()
                print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (orders) procesado automáticamente")
            except Exception as etl_error:
                db.rollback()
                print(f"⚠️  [AUTO-ETL-ORDERS] Error: {str(etl_error)}")
        
        elif db_event.source == "subscriptions":
            try:
                process_subscription_event(db, db_event)
                db_event.processed = True
                db.commit()
                print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (subscriptions) procesado automáticamente")
            except Exception as etl_error:
                db.rollback()
                print(f"⚠️  [AUTO-ETL-SUBSCRIPTIONS] Error: {str(etl_error)}")

        elif db_event.source == "salud":
            try:
                process_salud_event(db, db_event)
                db_event.processed = True
                db.commit()
                print(f"✅ [AUTO-ETL] Evento {db_event.event_type} (salud) procesado automáticamente")
            except Exception as etl_error:
                db.rollback()
                print(f"⚠️  [AUTO-ETL-SALUD] Error: {str(etl_error)}")

        elif db_event.source == "payments":
            # payload must conform to PaymentPayload
            # Distinguish event types for payments flow
            if db_event.event_type == "intento_pago":
                try:
                    from app.pagos.schemas.payment_schema import AttemptPaymentPayload
                    attempt = AttemptPaymentPayload.model_validate(db_event.payload)
                except ValidationError as ve:
                    db.rollback()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment attempt payload: {ve}")

                try:
                    fact = register_payment_attempt(db, attempt.model_dump())
                    # insert immutable audit event
                    audit = FactPaymentsEvent(
                        transaction_id=fact.transaction_id,
                        order_id=fact.order_id,
                        subscription_id=fact.subscription_id,
                        amount=fact.monto,
                        token_transaccion=fact.token_transaccion,
                        codigo_error=fact.codigo_error,
                        status="esperando_revisión",
                        timestamp_evento=fact.timestamp_evento,
                    )
                    db.add(audit)
                    db.flush()
                    db_event.processed = True
                    db.commit()
                    print(f"✅ [AUTO-ETL] Evento intento_pago procesado: {fact.transaction_id}")
                except Exception as etl_error:
                    db.rollback()
                    print(f"⚠️  [AUTO-ETL-PAYMENTS] Error on intento_pago: {str(etl_error)}")

            elif db_event.event_type == "confirmar_pago":
                try:
                    from app.pagos.schemas.payment_schema import ConfirmPaymentPayload
                    confirm = ConfirmPaymentPayload.model_validate(db_event.payload)
                except ValidationError as ve:
                    db.rollback()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment confirm payload: {ve}")

                try:
                    fact = confirm_payment(db, confirm.token_transaccion, confirm.model_dump())
                    # resolve status name from dim table (already set by confirm_payment)
                    from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion
                    estado = db.get(DimEstadosConciliacion, fact.estado_conciliacion_id)
                    status_val = estado.nombre if estado else ("Aprobado" if confirm.approved else "discrepancia_de_monto")

                    audit = FactPaymentsEvent(
                        transaction_id=fact.transaction_id,
                        order_id=fact.order_id,
                        subscription_id=fact.subscription_id,
                        amount=fact.monto,
                        token_transaccion=fact.token_transaccion,
                        codigo_error=fact.codigo_error,
                        status=status_val,
                        timestamp_evento=fact.timestamp_evento,
                    )
                    db.add(audit)
                    db.flush()
                    db_event.processed = True
                    db.commit()
                    print(f"✅ [AUTO-ETL] Evento confirmar_pago procesado: {fact.transaction_id}")
                except Exception as etl_error:
                    db.rollback()
                    print(f"⚠️  [AUTO-ETL-PAYMENTS] Error on confirmar_pago: {str(etl_error)}")
            
            elif db_event.event_type == "cierre_diario_completado":
                try:
                    from app.pagos.schemas.closure_schema import CierreDiarioPayload
                    from app.pagos.services.closure_service import process_cierre_diario
                    from app.services.monitoring_service import check_payments_uptime
                    cierre = CierreDiarioPayload.model_validate(db_event.payload)
                except ValidationError as ve:
                    db.rollback()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid cierre payload: {ve}")

                try:
                    cierre_record = process_cierre_diario(db, cierre.model_dump())
                    db_event.processed = True
                    db.commit()
                    print(f"✅ [AUTO-ETL] Cierre diario procesado: {cierre_record.id} estado_id={cierre_record.estado_id}")
                except Exception as etl_error:
                    db.rollback()
                    print(f"⚠️  [AUTO-ETL-CIERRE] Error: {str(etl_error)}")
                
                # After closure, run monitoring checks
                try:
                    metrics = check_payments_uptime(db)
                    if metrics.get("alert_id"):
                        db.commit()
                        print(f"🔔 [MONITOR] Alert created id={metrics.get('alert_id')}")
                    else:
                        db.rollback()
                except Exception as me:
                    db.rollback()
                    print(f"⚠️ [MONITOR] Error running monitoring: {str(me)}")
            else:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown payment event_type")

        return EventCreateResponse(
            message="event stored",
            event_id=db_event.id,
            source=db_event.source,
            event_type=db_event.event_type
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el evento: {str(e)}"
        )
