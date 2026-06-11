import logging
from sqlalchemy.orm import Session

from app.models.raw.raw_events import RawEvent

logger = logging.getLogger(__name__)


def process_payment_event(db: Session, raw_event: RawEvent) -> None:
    if raw_event.event_type == "intento_pago":
        _process_intento_pago(db, raw_event)
    elif raw_event.event_type == "confirmar_pago":
        _process_confirmar_pago(db, raw_event)
    elif raw_event.event_type == "cierre_diario_completado":
        _process_cierre_diario_completado(db, raw_event)
    else:
        raise ValueError(f"PAYMENT-ETL event_type desconocido: {raw_event.event_type}")


def _process_intento_pago(db: Session, raw_event: RawEvent) -> None:
    from app.pagos.schemas.payment_schema import AttemptPaymentPayload
    from app.pagos.services.payment_service import register_payment_attempt
    from app.pagos.models.fact_payments_events import FactPaymentsEvent

    attempt = AttemptPaymentPayload.model_validate(raw_event.payload)
    fact = register_payment_attempt(db, attempt.model_dump())
    db.add(FactPaymentsEvent(
        transaction_id=fact.transaction_id,
        order_id=fact.order_id,
        subscription_id=fact.subscription_id,
        amount=fact.monto,
        token_transaccion=fact.token_transaccion,
        codigo_error=None,
        status="esperando_revisión",
        timestamp_evento=fact.timestamp_evento,
    ))
    db.flush()
    logger.info("PAYMENT-ETL intento_pago procesado: %s", fact.transaction_id)


def _process_confirmar_pago(db: Session, raw_event: RawEvent) -> None:
    from app.pagos.schemas.payment_schema import ConfirmPaymentPayload
    from app.pagos.services.payment_service import confirm_payment
    from app.pagos.models.fact_payments_events import FactPaymentsEvent
    from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion

    confirm = ConfirmPaymentPayload.model_validate(raw_event.payload)
    fact = confirm_payment(db, confirm.token_transaccion, confirm.model_dump())
    estado = db.get(DimEstadosConciliacion, fact.estado_conciliacion_id)
    status_val = estado.nombre if estado else ("Aprobado" if confirm.approved else "discrepancia_de_monto")
    db.add(FactPaymentsEvent(
        transaction_id=fact.transaction_id,
        order_id=fact.order_id,
        subscription_id=fact.subscription_id,
        amount=fact.monto,
        token_transaccion=fact.token_transaccion,
        codigo_error=None,
        status=status_val,
        timestamp_evento=fact.timestamp_evento,
    ))
    db.flush()
    logger.info("PAYMENT-ETL confirmar_pago procesado: %s", fact.transaction_id)


def _process_cierre_diario_completado(db: Session, raw_event: RawEvent) -> None:
    from app.pagos.schemas.closure_schema import CierreDiarioPayload
    from app.pagos.services.closure_service import process_cierre_diario

    cierre = CierreDiarioPayload.model_validate(raw_event.payload)
    cierre_record = process_cierre_diario(db, cierre.model_dump())
    db.flush()
    logger.info("PAYMENT-ETL cierre diario procesado: id=%s estado_id=%s", cierre_record.id, cierre_record.estado_id)
