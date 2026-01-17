from sqlalchemy import Column, String, Numeric, Date, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.database import Base


class InvestmentStatus(str, enum.Enum):
    """Estados posibles de una inversión"""
    ACTIVE = "active"       # Posición abierta actualmente
    SOLD = "sold"           # Posición cerrada (swing trade completado)
    WATCHLIST = "watchlist" # Acción en lista de seguimiento


class Investment(Base):
    """
    Modelo ORM para la tabla 'investments'
    
    Representa las posiciones bursátiles de cada usuario
    """
    
    __tablename__ = "investments"
    
    # ============================================
    # COLUMNAS
    # ============================================
    
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
        index=True
    )
    
    symbol = Column(
        String(10),
        nullable=False,
        comment="Ticker de la acción (ej: AAPL, TSLA)"
    )
    
    company_name = Column(
        String(255),
        nullable=False,
        comment="Nombre completo de la empresa"
    )
    
    shares = Column(
        Numeric(10, 4),
        nullable=False,
        comment="Cantidad de acciones"
    )
    
    average_price = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Precio promedio de compra en USD"
    )
    
    purchase_date = Column(
        Date,
        nullable=False,
        comment="Fecha de compra de la posición"
    )
    
    # ============================================
    # DATOS DE VENTA (Swing Trade)
    # ============================================
    
    sale_price = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Precio de venta en USD (NULL hasta que status=sold)"
    )
    
    sale_date = Column(
        Date,
        nullable=True,
        comment="Fecha de venta (NULL hasta que status=sold)"
    )
    
    status = Column(
        Enum(InvestmentStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=InvestmentStatus.ACTIVE,
        server_default='active',
        comment="Estado: active, sold, watchlist",
        index=True
    )
    
    notes = Column(
        Text,
        nullable=True,
        comment="Notas adicionales sobre la inversión"
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
    
    # ============================================
    # RELACIONES
    # ============================================
    
    user = relationship(
        "User",
        back_populates="investments"
    )
    
    # ============================================
    # REPRESENTACIÓN
    # ============================================
    
    def __repr__(self):
        return f"<Investment(id={self.id}, symbol={self.symbol}, shares={self.shares}, user_id={self.user_id})>"
