import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.pagos.models.fact_payments import FactPayment
from app.pagos.models.dim_status import DimStatus


PAYMENT_STATUS_NAMES = [
    "aprobado",
    "esperando_revisión",
    "discrepancia_monto",
    "discrepancia_transacciones",
]


def _normalize_error_code(error_code: Optional[str]) -> Optional[str]:
    if not error_code:
        return None
    return error_code.strip()


def _resolve_status_name(event_type: str, error_code: Optional[str]) -> str:
    if event_type == "pago_exitoso":
        return "aprobado"

    if event_type == "intento_pago":
        return "esperando_revisión"

    if event_type == "pago_rechazado":
        normalized = _normalize_error_code(error_code)
        if normalized:
            lower_code = normalized.lower()
            if "monto" in lower_code or "amount" in lower_code:
                return "discrepancia_monto"
            if "transaccion" in lower_code or "transaction" in lower_code:
                return "discrepancia_transacciones"
        return "esperando_revisión"

    return "esperando_revisión"


def _get_or_create_status(db: Session, name: str) -> DimStatus:
    status = db.query(DimStatus).filter(DimStatus.name == name).first()
    if not status:
        status = DimStatus(name=name, description=f"Estado de pago: {name}")
        db.add(status)
        db.flush()
    return status


def process_payment_event(db: Session, raw_event) -> FactPayment:
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
    status_obj = _get_or_create_status(db, status_name)

    timestamp = payload.get("timestamp")
    if timestamp:
        try:
            timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except Exception:
            timestamp = datetime.utcnow()
    else:
        timestamp = datetime.utcnow()

    fact_payment = FactPayment(
        transaction_id=transaction_id,
        order_id=order_id,
        subscription_id=subscription_id,
        amount=float(amount),
        status_id=status_obj.id,
        error_code=error_code,
        timestamp=timestamp,
    )

    db.add(fact_payment)
    db.flush()
    return fact_payment
