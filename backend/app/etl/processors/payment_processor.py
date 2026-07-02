import logging
import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.raw.raw_events import RawEvent
from app.pagos.models.fact_pagos import FactPagos
from app.pagos.models.fact_payments_events import FactPaymentsEvent
from app.pagos.models.dim_error_codes import get_error_code_id
from app.pagos.services.payment_service import get_or_create_estado, confirm_payment, _hash_token

_AUDIT_STATUSES = {"esperando_revisión", "Aprobado", "discrepancia_de_monto", "discrepancia_de_transacciones"}


def _to_uuid(value) -> _uuid_mod.UUID:
    try:
        return _uuid_mod.UUID(str(value))
    except (ValueError, AttributeError):
        return _uuid_mod.uuid4()

logger = logging.getLogger(__name__)


def _resolve_status_name(event_type: str, error_code: Optional[str]) -> str:
    if event_type in ("pago_exitoso", "payment.processed"):
        return "Aprobado"
    if event_type in ("intento_pago", "intento.pago"):
        return "esperando_revisión"
    if event_type == "pago_rechazado":
        if error_code:
            lower = error_code.lower()
            if "monto" in lower or "amount" in lower:
                return "discrepancia_de_monto"
            if "transaccion" in lower or "transaction" in lower:
                return "discrepancia_de_transacciones"
        return "Rechazado"
    return "esperando_revisión"


def process_payment_event(db: Session, raw_event: RawEvent) -> None:
    if raw_event.event_type == "pago_reembolsado":
        logger.info("PAYMENT-ETL pago_reembolsado registrado en raw_events — sin acción warehouse: event_id=%s", raw_event.event_id)
        return

    if raw_event.event_type == "confirmar_pago":
        payload = raw_event.payload or {}
        token = payload.get("token_transaccion")
        if not token:
            raise ValueError("token_transaccion es obligatorio para confirmar_pago")
        confirmation = {
            "approved": payload.get("approved"),
            "transaction_id": payload.get("transaction_id"),
            "codigo_error": payload.get("codigo_error"),
            "timestamp_evento": payload.get("timestamp_evento"),
        }
        fact = confirm_payment(db, token, confirmation)
        approved = payload.get("approved")
        raw_err = (payload.get("codigo_error") or "").lower()
        if approved:
            audit_status = "Aprobado"
        elif "monto" in raw_err or "amount" in raw_err:
            audit_status = "discrepancia_de_monto"
        elif "transaccion" in raw_err or "transaction" in raw_err:
            audit_status = "discrepancia_de_transacciones"
        else:
            audit_status = "esperando_revisión"
        db.add(FactPaymentsEvent(
            transaction_id=_to_uuid(payload.get("transaction_id")),
            amount=float(fact.monto or 0),
            token_transaccion=_hash_token(token),
            codigo_error=(payload.get("codigo_error") or "").strip() or None,
            status=audit_status,
            timestamp_evento=datetime.now(tz=timezone.utc),
        ))
        db.flush()
        db.commit()
        logger.info("PAYMENT-ETL confirmar_pago procesado: token=%s estado=%s", token, audit_status)
        return

    payload = raw_event.payload or {}
    transaction_token = (
        payload.get("transaction_token")
        or payload.get("token_transaccion")
        or payload.get("transaction_id")
    )
    if not transaction_token:
        raise ValueError("transaction_token es obligatorio para eventos de pagos")

    amount = payload.get("amount") or payload.get("monto") or 0.0
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

    hashed = _hash_token(str(transaction_token))
    fact = db.query(FactPagos).filter(FactPagos.token_transaccion == hashed).first()
    if fact:
        fact.estado_conciliacion_id = estado.id
        fact.error_code_id = get_error_code_id(db, error_code)
    else:
        fact = FactPagos(
            order_id=str(order_id) if order_id is not None else None,
            subscription_id=str(subscription_id) if subscription_id is not None else None,
            monto=amount,
            token_transaccion=hashed,
            payment_method=payment_method,
            error_code_id=get_error_code_id(db, error_code),
            timestamp_evento=timestamp,
            estado_conciliacion_id=estado.id,
        )
        db.add(fact)
    db.flush()
    audit_status = status_name if status_name in _AUDIT_STATUSES else "esperando_revisión"
    db.add(FactPaymentsEvent(
        transaction_id=_to_uuid(payload.get("transaction_id")),
        order_id=str(order_id) if order_id is not None else None,
        subscription_id=str(subscription_id) if subscription_id is not None else None,
        amount=float(amount),
        token_transaccion=hashed,
        codigo_error=error_code,
        status=audit_status,
        timestamp_evento=timestamp,
    ))
    db.flush()
    logger.info("PAYMENT-ETL %s procesado: token=%s estado=%s", raw_event.event_type, transaction_token, status_name)
