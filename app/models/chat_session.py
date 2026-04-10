"""
Modelo ChatSession - Sesiones de Chat
=====================================

SEGURIDAD:
- El historial de conversación se almacena encriptado en el servidor
- Cada sesión está vinculada a un usuario específico
- Las sesiones expiran automáticamente después de 24 horas de inactividad
- El historial del frontend NO se usa - se confía solo en el servidor
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime, timedelta

from app.database import Base
from app.models.encrypted_fields import EncryptedText


class ChatSession(Base):
    """
    Modelo ORM para la tabla 'chat_sessions'.

    Almacena el historial de conversación del chat de forma segura en el servidor.
    El historial se guarda encriptado para proteger la privacidad del usuario.
    """

    __tablename__ = "chat_sessions"

    # ============================================
    # COLUMNAS PRINCIPALES
    # ============================================

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Identificador único de la sesión"
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del usuario propietario de la sesión"
    )

    # ============================================
    # DATOS DE LA SESIÓN (encriptados)
    # ============================================

    # Historial de conversación serializado como JSON y encriptado
    history = Column(
        EncryptedText,
        nullable=True,
        default="[]",
        doc="Historial de mensajes en formato JSON (encriptado)"
    )

    # Contador de mensajes para límites
    message_count = Column(
        Integer,
        default=0,
        doc="Número de mensajes en la sesión"
    )

    # ============================================
    # METADATOS
    # ============================================

    is_active = Column(
        Boolean,
        default=True,
        doc="Si la sesión está activa"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Fecha de creación de la sesión"
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        doc="Última actualización de la sesión"
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Fecha de expiración de la sesión"
    )

    # ============================================
    # RELACIONES
    # ============================================

    user = relationship(
        "User",
        back_populates="chat_sessions",
        lazy="joined"
    )

    # ============================================
    # CONSTANTES
    # ============================================

    SESSION_EXPIRY_HOURS = 24
    MAX_HISTORY_LENGTH = 50
    MAX_MESSAGE_LENGTH = 4000

    # ============================================
    # MÉTODOS DE INSTANCIA
    # ============================================

    def is_expired(self) -> bool:
        """Verifica si la sesión ha expirado."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def extend_expiry(self) -> None:
        """Extiende la fecha de expiración de la sesión."""
        self.expires_at = datetime.utcnow() + timedelta(hours=self.SESSION_EXPIRY_HOURS)

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, messages={self.message_count})>"
