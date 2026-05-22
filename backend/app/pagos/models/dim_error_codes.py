from sqlalchemy import Column, Integer, String, Boolean

from app.db.base import Base


class DimErrorCode(Base):
    __tablename__ = "dim_error_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=False)
    categoria = Column(String(50), nullable=False)
    es_falla_masiva = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<DimErrorCode(code={self.code}, categoria={self.categoria})>"


# Catálogo oficial de códigos de error estandarizados.
# es_falla_masiva=True indica que múltiples ocurrencias pueden señalar
# una falla masiva del proveedor externo (útil para alertas SLA).
ERROR_CODE_CATALOG = [
    # code                   descripcion                                          categoria     es_falla_masiva
    ("transaction_mismatch", "ID de transacción no coincide con el token",       "interno",    False),
    ("rejected",             "Rechazo genérico del proveedor",                   "proveedor",  False),
    ("insufficient_funds",   "Fondos insuficientes en la cuenta",                "tarjeta",    False),
    ("card_expired",         "Tarjeta expirada",                                 "tarjeta",    False),
    ("card_blocked",         "Tarjeta bloqueada o suspendida",                   "tarjeta",    False),
    ("card_not_supported",   "Tipo de tarjeta no soportado por el proveedor",    "tarjeta",    False),
    ("provider_timeout",     "Timeout en la comunicación con el proveedor",      "proveedor",  True),
    ("provider_unavailable", "Proveedor externo no disponible",                  "proveedor",  True),
    ("provider_error",       "Error genérico del proveedor externo",             "proveedor",  True),
    ("duplicate_transaction","Transacción duplicada detectada",                  "validacion", False),
    ("invalid_amount",       "Monto inválido o fuera de rango permitido",        "validacion", False),
    ("internal_error",       "Error interno del sistema de pagos",               "interno",    False),
]


def get_error_code_id(db, raw_code: str | None) -> int | None:
    """Resuelve un código crudo a su id en dim_error_codes.

    Si el código no existe en el catálogo, retorna el id de 'provider_error'
    para no perder trazabilidad ni dejar el campo nulo en casos inesperados.
    """
    if not raw_code:
        return None

    normalized = raw_code.strip().lower()
    record = db.query(DimErrorCode).filter(DimErrorCode.code == normalized).first()
    if record:
        return record.id

    fallback = db.query(DimErrorCode).filter(DimErrorCode.code == "provider_error").first()
    return fallback.id if fallback else None
