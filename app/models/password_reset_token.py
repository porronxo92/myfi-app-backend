"""
Modelo PasswordResetToken - Tokens para restablecer contraseña
===============================================================

Almacena tokens temporales para el flujo de "forgot password".
Los tokens expiran después de un tiempo configurable.
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class PasswordResetToken(Base):
    """
    Modelo ORM para la tabla 'password_reset_tokens'

    Almacena tokens temporales para restablecer contraseñas.
    """

    __tablename__ = "password_reset_tokens"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del token"
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID del usuario"
    )

    token = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Token único para reset (hash)"
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Fecha de expiración del token"
    )

    used = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Si el token ya fue utilizado"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Fecha de creación"
    )

    # Relación con User
    user = relationship("User", backref="password_reset_tokens")

    def __repr__(self):
        return f"<PasswordResetToken(id='{self.id}', user_id='{self.user_id}', used={self.used})>"

    @property
    def is_expired(self) -> bool:
        """Verifica si el token ha expirado"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Verifica si el token es válido (no usado y no expirado)"""
        return not self.used and not self.is_expired
