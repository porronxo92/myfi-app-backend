"""
Modelo GeminiUsage - Tracking de uso de API Gemini por usuario
==============================================================

Rastrea el número de peticiones diarias a Gemini AI por usuario
para implementar cuotas y límites de uso.
"""

from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class GeminiUsage(Base):
    """
    Modelo ORM para la tabla 'gemini_usage'

    Rastrea el uso diario de la API de Gemini por usuario.
    Se utiliza para implementar límites de cuota por usuario.

    El reset diario es automático: cada día se crea un nuevo registro
    con request_count=0 cuando el usuario hace su primera petición.
    """

    __tablename__ = "gemini_usage"

    __table_args__ = (
        UniqueConstraint('user_id', 'usage_date', name='unique_user_date'),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del registro"
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Usuario propietario (FK)"
    )

    usage_date = Column(
        Date,
        nullable=False,
        server_default=func.current_date(),
        comment="Fecha del uso (para reset diario)"
    )

    request_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Número de peticiones a Gemini en este día"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Fecha de creación del registro"
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Fecha de última actualización"
    )

    # Relationship
    user = relationship("User", backref="gemini_usage")

    def __repr__(self):
        return f"<GeminiUsage(user_id={self.user_id}, date={self.usage_date}, count={self.request_count})>"
