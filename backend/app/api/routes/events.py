import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.session import SessionLocal
from app.models.raw.raw_events import RawEvent
from app.schemas import EventCreate, AcknowledgeResponse
from app.schemas.inventory_event_schema import InventoryEventCreate
from app.services import create_event
from app.etl.processors.order_processor import process_order_event
from app.etl.processors.subscription_processor import process_subscription_event
from app.etl.processors.salud_processor import process_salud_event
from app.etl.processors.incident_processor import process_incident_event
from app.pagos.services.payment_service import register_payment_attempt, confirm_payment
from app.pagos.models.fact_payments_events import FactPaymentsEvent


router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={
        400: {"description": "Payload JSON inválido o campos requeridos faltantes"},
        500: {"description": "Error interno del servidor"},
    },
)

# ---------------------------------------------------------------------------
# ETL background worker
# Abre su propia sesión DB para desacoplarse del ciclo de vida del request.
# ---------------------------------------------------------------------------

_ETL_PROCESSORS = {
    "orders": process_order_event,
    "subscriptions": process_subscription_event,
    "salud": process_salud_event,
    "incidents": process_incident_event,
}


def _run_etl(event_id: uuid.UUID, source: str) -> None:
    """Corre después de enviar el 202. Usa sesión DB propia para aislamiento."""
    processor = _ETL_PROCESSORS.get(source)
    if processor is None:
        return  # fuente sin ETL registrado — se guarda en raw_events igualmente

    db: Session = SessionLocal()
    try:
        raw_event = db.query(RawEvent).filter(RawEvent.event_id == event_id).first()
        if not raw_event:
            return

        processor(db, raw_event)
        raw_event.processed = True
        db.commit()
        print(f"[ETL] {source}/{raw_event.event_type} OK — event_id={event_id}")
    except Exception as exc:
        db.rollback()
        print(f"[ETL-ERROR] {source} event_id={event_id}: {exc}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoint principal
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=AcknowledgeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingestar un evento",
    description=(
        "Valida el JSON de entrada (source, event_type, payload). "
        "Añade event_id (UUID v4) e ingested_at (UTC) generados por el servidor "
        "y persiste en raw_events. "
        "Devuelve 202 Accepted de inmediato; el ETL al warehouse corre en background."
    ),
)
async def ingest_event(
    event: EventCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AcknowledgeResponse:
    event_id = uuid.uuid4()
    ingested_at = datetime.now(tz=timezone.utc)

    # Validación estricta para eventos del módulo de Inventario (Grupo 5)
    if event.source == "inventory":
        try:
            InventoryEventCreate(
                source=event.source,
                event_type=event.event_type,
                payload=event.payload,
            )
        except ValidationError as ve:
            errores = [
                f"• {err['loc'][-1] if err['loc'] else 'payload'}: {err['msg']}"
                for err in ve.errors()
            ]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Evento de inventario con datos inválidos",
                    "event_type": event.event_type,
                    "errores": errores,
                    "ayuda": (
                        "Revise el formato de los campos. UUIDs deben ser v4, "
                        "fechas en ISO 8601 (ej: '2026-05-28T10:00:00Z'), "
                        "y valores numéricos deben ser enteros."
                    ),
                },
            )

    try:
        db_event = create_event(db=db, event=event, event_id=event_id, ingested_at=ingested_at)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al persistir el evento: {exc}",
        )

    # Pagos: procesamiento inline (flujo complejo con múltiples event_types y auditoría)
    if db_event.source == "payments":
        if db_event.event_type == "intento_pago":
            try:
                from app.pagos.schemas.payment_schema import AttemptPaymentPayload
                attempt = AttemptPaymentPayload.model_validate(db_event.payload)
            except ValidationError as ve:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment attempt payload: {ve}")

            try:
                fact = register_payment_attempt(db, attempt.model_dump())
                audit = FactPaymentsEvent(
                    transaction_id=fact.transaction_id,
                    order_id=fact.order_id,
                    subscription_id=fact.subscription_id,
                    amount=fact.monto,
                    token_transaccion=fact.token_transaccion,
                    codigo_error=None,
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
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment confirm payload: {ve}")

            try:
                fact = confirm_payment(db, confirm.token_transaccion, confirm.model_dump())
                from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion
                estado = db.get(DimEstadosConciliacion, fact.estado_conciliacion_id)
                status_val = estado.nombre if estado else ("Aprobado" if confirm.approved else "discrepancia_de_monto")
                audit = FactPaymentsEvent(
                    transaction_id=fact.transaction_id,
                    order_id=fact.order_id,
                    subscription_id=fact.subscription_id,
                    amount=fact.monto,
                    token_transaccion=fact.token_transaccion,
                    codigo_error=None,
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
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid cierre payload: {ve}")

            try:
                cierre_record = process_cierre_diario(db, cierre.model_dump())
                db_event.processed = True
                db.commit()
                print(f"✅ [AUTO-ETL] Cierre diario procesado: {cierre_record.id} estado_id={cierre_record.estado_id}")
            except Exception as etl_error:
                db.rollback()
                print(f"⚠️  [AUTO-ETL-CIERRE] Error: {str(etl_error)}")

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
    else:
        # ETL en background — la conexión del cliente ya está liberada cuando corre
        background_tasks.add_task(_run_etl, event_id=db_event.event_id, source=db_event.source)

    return AcknowledgeResponse(status="acknowledged", event_id=event_id)
