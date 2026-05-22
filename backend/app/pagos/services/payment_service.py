from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.pagos.models.fact_pagos import FactPagos
from app.pagos.models.dim_estados_conciliacion import DimEstadosConciliacion
from app.pagos.models.dim_error_codes import get_error_code_id


ALLOWED_ESTADOS = [
    "Aprobado",
    "esperando_revisión",
    "discrepancia_de_monto",
    "discrepancia_de_transacciones",
]


def get_or_create_estado(db: Session, nombre: str) -> DimEstadosConciliacion:
    estado = db.query(DimEstadosConciliacion).filter(DimEstadosConciliacion.nombre == nombre).one_or_none()
    if estado:
        return estado
    estado = DimEstadosConciliacion(nombre=nombre)
    db.add(estado)
    db.flush()
    return estado


def register_payment_attempt(db: Session, payload: dict) -> FactPagos:
    """Registra un intento de pago con estado 'esperando_revisión' y token asociado."""
    try:
        estado = get_or_create_estado(db, "esperando_revisión")

        fact = FactPagos(
            transaction_id=payload["transaction_id"],
            order_id=payload.get("order_id"),
            subscription_id=payload.get("subscription_id"),
            monto=payload["monto"],
            token_transaccion=payload["token_transaccion"],
            error_code_id=None,
            timestamp_evento=payload["timestamp_evento"],
            estado_conciliacion_id=estado.id,
        )

        db.add(fact)
        db.flush()
        return fact
    except SQLAlchemyError:
        db.rollback()
        raise


def confirm_payment(db: Session, token: str, confirmation: dict) -> FactPagos:
    """Confirma un pago buscando por token; usa bloqueo FOR UPDATE para evitar race conditions."""
    try:
        fact = (
            db.query(FactPagos)
            .filter(FactPagos.token_transaccion == token)
            .with_for_update()
            .one_or_none()
        )

        if not fact:
            raise ValueError("No payment found for provided token")

        incoming_tx = confirmation.get("transaction_id")
        approved = confirmation.get("approved")
        raw_codigo_error = confirmation.get("codigo_error")

        if incoming_tx and str(incoming_tx) != str(fact.transaction_id):
            estado = get_or_create_estado(db, "discrepancia_de_transacciones")
            fact.estado_conciliacion_id = estado.id
            fact.error_code_id = get_error_code_id(db, "transaction_mismatch")
            fact.timestamp_evento = confirmation.get("timestamp_evento", fact.timestamp_evento)
            db.flush()
            return fact

        if approved:
            estado = get_or_create_estado(db, "Aprobado")
            fact.estado_conciliacion_id = estado.id
            fact.error_code_id = None
        else:
            estado = get_or_create_estado(db, "discrepancia_de_monto")
            fact.estado_conciliacion_id = estado.id
            fact.error_code_id = get_error_code_id(db, raw_codigo_error or "rejected")

        fact.timestamp_evento = confirmation.get("timestamp_evento", fact.timestamp_evento)
        db.flush()
        return fact

    except SQLAlchemyError:
        db.rollback()
        raise
