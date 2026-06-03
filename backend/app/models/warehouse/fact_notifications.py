"""
Modelo warehouse para notificaciones.
Almacena historial de notificaciones enviadas con estados de entrega y reintentos.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from datetime import datetime
import uuid

from app.db.base import Base


class FactNotifications(Base):
    """
    Tabla warehouse: fact_notifications
    
    Registra historial de todas las notificaciones enviadas con:
    - Detalles de envío (canal, destinatario, mensaje)
    - Estado de entrega (enviado, entregado, fallido)
    - Reintentos y fallback
    - Timestamp de entrega
    """
    
    __tablename__ = "fact_notifications"
    
    id_notificacion = Column(
        String,
        primary_key=True,
        default=lambda: f"ntf_{uuid.uuid4().hex[:12]}",
        nullable=False,
        doc="ID único de la notificación (ntf_xxxxx)"
    )
    
    id_api_key = Column(
        String,
        nullable=True,
        doc="Identificador de la API key usada"
    )
    
    canal_original = Column(
        String,
        nullable=False,
        doc="Canal con el que se intentó enviar primero: 'sms', 'email', 'push'. Nunca cambia."
    )
    
    canal_usado = Column(
        String,
        nullable=False,
        doc="Canal que finalmente entregó la notificación. Se actualiza si hay fallback."
    )
    
    destinatario_email = Column(
        String,
        nullable=True,
        doc="Email del destinatario (si aplica)"
    )
    
    destinatario_telefono = Column(
        String,
        nullable=True,
        doc="Teléfono del destinatario (si aplica)"
    )
    
    mensaje_asunto = Column(
        String,
        nullable=True,
        doc="Asunto del mensaje (principalmente para emails)"
    )
    
    mensaje_email = Column(
        Text,
        nullable=True,
        doc="Cuerpo del mensaje para envío por email"
    )
    
    mensaje_sms = Column(
        Text,
        nullable=True,
        doc="Cuerpo del mensaje para envío por SMS"
    )
    
    estado = Column(
        String,
        nullable=False,
        doc="Estado actual: 'enviado', 'entregado', 'fallido'"
    )
    
    intentos = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Número de intentos de envío realizados"
    )
    
    fallback_activado = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Si se activó fallback a otro canal"
    )
    
    fecha_entrega = Column(
        DateTime,
        nullable=True,
        doc="Timestamp cuando se entregó la notificación"
    )
    
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Timestamp de creación del registro"
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="Timestamp de última actualización"
    )