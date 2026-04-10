"""
Modelo InvestmentSettings - Configuración de Inversiones por Usuario
====================================================================

Almacena configuraciones específicas del usuario relacionadas con inversiones,
como el balance de efectivo no invertido (cash balance).
"""

from sqlalchemy import Column, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
import uuid

from app.database import Base


class InvestmentSettings(Base):
    """
    Modelo ORM para la tabla 'investment_settings'

    Almacena configuraciones de inversión por usuario, incluyendo
    el efectivo no invertido que el usuario tiene disponible.
    """

    __tablename__ = "investment_settings"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True
    )

    cash_balance = Column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
        comment="Efectivo no invertido en USD"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relación con User
    user = relationship("User", back_populates="investment_settings")

    def __repr__(self):
        return f"<InvestmentSettings(user_id={self.user_id}, cash_balance={self.cash_balance})>"
