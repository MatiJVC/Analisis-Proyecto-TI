import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.pagos.models.fact_pagos import FactPagos
from app.pagos.models.dim_error_codes import get_error_code_id
from app.pagos.services.payment_service import get_or_create_estado


PAYMENT_STATUS_NAMES = [
    "Aprobado",
    "esperando_revisión",
    "discrepancia_de_monto",
    "discrepancia_de_transacciones",
]


def _normalize_error_code(error_code: Optional[str]) -> Optional[str]:
    if not error_code:
        return None
    return error_code.strip()


def _resolve_status_name(event_type: str, error_code: Optional[str]) -> str:
    if event_type == "pago_exitoso":
        return "Aprobado"

    if event_type == "intento_pago":
        return "esperando_revisión"

    if event_type == "pago_rechazado":
        normalized = _normalize_error_code(error_code)
        if normalized:
            lower_code = normalized.lower()
            if "monto" in lower_code or "amount" in lower_code:
                return "discrepancia_de_monto"
            if "transaccion" in lower_code or "transaction" in lower_code:
                return "discrepancia_de_transacciones"
        return "esperando_revisión"

    return "esperando_revisión"


def process_payment_event(db: Session, raw_event) -> FactPagos:
    payload = raw_event.payload or {}
    transaction_token = payload.get("transaction_token")
    if not transaction_token:
        raise ValueError("transaction_token es obligatorio para eventos de pagos")

    try:
        transaction_id = uuid.UUID(str(transaction_token))
    except ValueError:
        raise ValueError("transaction_token debe ser un UUID válido")

    amount = payload.get("amount", 0.0)
    if amount is None:
        amount = 0.0

    order_id = payload.get("order_id")
    subscription_id = payload.get("subscription_id")
    error_code = _normalize_error_code(payload.get("error_code"))

    status_name = _resolve_status_name(raw_event.event_type, error_code)
    estado = get_or_create_estado(db, status_name)

    timestamp = payload.get("timestamp")
    if timestamp:
        try:
            timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except Exception:
            timestamp = datetime.utcnow()
    else:
        timestamp = datetime.utcnow()

    fact = FactPagos(
        transaction_id=transaction_id,
        order_id=str(order_id) if order_id is not None else None,
        subscription_id=str(subscription_id) if subscription_id is not None else None,
        monto=amount,
        token_transaccion=str(transaction_token),
        error_code_id=get_error_code_id(db, error_code),
        timestamp_evento=timestamp,
        estado_conciliacion_id=estado.id,
    )

    db.add(fact)
    db.flush()
    return fact
