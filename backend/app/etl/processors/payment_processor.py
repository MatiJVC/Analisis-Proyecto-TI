import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.raw.raw_events import RawEvent
from app.pagos.models.fact_pagos import FactPagos
from app.pagos.models.dim_error_codes import get_error_code_id
from app.pagos.services.payment_service import get_or_create_estado

logger = logging.getLogger(__name__)


def _resolve_status_name(event_type: str, error_code: Optional[str]) -> str:
    if event_type == "pago_exitoso":
        return "Aprobado"
    if event_type == "intento_pago":
        return "esperando_revisión"
    if event_type == "pago_rechazado":
        if error_code:
            lower = error_code.lower()
            if "monto" in lower or "amount" in lower:
                return "discrepancia_de_monto"
            if "transaccion" in lower or "transaction" in lower:
                return "discrepancia_de_transacciones"
        return "esperando_revisión"
    return "esperando_revisión"


def process_payment_event(db: Session, raw_event: RawEvent) -> None:
    if raw_event.event_type == "pago_reembolsado":
        logger.info("PAYMENT-ETL pago_reembolsado registrado en raw_events — sin acción warehouse: event_id=%s", raw_event.event_id)
        return

    payload = raw_event.payload or {}
    transaction_token = payload.get("transaction_token")
    if not transaction_token:
        raise ValueError("transaction_token es obligatorio para eventos de pagos")

    amount = payload.get("amount") or 0.0
    order_id = payload.get("order_id")
    subscription_id = payload.get("subscription_id")
    error_code = (payload.get("error_code") or "").strip() or None
    payment_method = payload.get("payment_method") or None

    status_name = _resolve_status_name(raw_event.event_type, error_code)
    estado = get_or_create_estado(db, status_name)

    raw_ts = payload.get("timestamp")
    if raw_ts:
        try:
            timestamp = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
        except Exception:
            timestamp = datetime.now(tz=timezone.utc)
    else:
        timestamp = datetime.now(tz=timezone.utc)

    fact = FactPagos(
        order_id=str(order_id) if order_id is not None else None,
        subscription_id=str(subscription_id) if subscription_id is not None else None,
        monto=amount,
        token_transaccion=str(transaction_token),
        payment_method=payment_method,
        error_code_id=get_error_code_id(db, error_code),
        timestamp_evento=timestamp,
        estado_conciliacion_id=estado.id,
    )

    db.add(fact)
    db.flush()
    logger.info("PAYMENT-ETL %s procesado: token=%s estado=%s", raw_event.event_type, transaction_token, status_name)
