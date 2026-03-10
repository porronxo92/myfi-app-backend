"""
Modelo Investment - Inversiones Bursátiles
==========================================

SEGURIDAD (GDPR/PSD2):
- symbol, company_name, shares, average_price: Encriptados con AES-256-GCM
- Protege la estrategia de inversión del usuario (información muy sensible)
- TypeDecorators manejan encriptación/desencriptación automáticamente
"""

from sqlalchemy import Column, String, Numeric, Date, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
import enum
import uuid

from app.database import Base
from app.models.encrypted_fields import EncryptedString, EncryptedNumeric


class InvestmentStatus(str, enum.Enum):
    """Estados posibles de una inversión"""
    ACTIVE = "active"       # Posición abierta actualmente
    SOLD = "sold"           # Posición cerrada (swing trade completado)
    WATCHLIST = "watchlist" # Acción en lista de seguimiento


class Investment(Base):
    """
    Modelo ORM para la tabla 'investments'
    
    Representa las posiciones bursátiles de cada usuario.
    Los datos de inversión están encriptados con AES-256-GCM.
    """
    
    __tablename__ = "investments"
    
    # ============================================
    # COLUMNAS IDENTIFICADORAS (no sensibles)
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
    
    purchase_date = Column(
        Date,
        nullable=False,
        comment="Fecha de compra de la posición"
    )
    
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
    # COLUMNAS ENCRIPTADAS (AES-256-GCM)
    # ============================================
    
    symbol = Column(
        EncryptedString(10),
        nullable=False,
        comment="Ticker - ENCRIPTADO AES-256-GCM"
    )
    
    company_name = Column(
        EncryptedString(255),
        nullable=False,
        comment="Nombre de empresa - ENCRIPTADO AES-256-GCM"
    )
    
    shares = Column(
        EncryptedNumeric,
        nullable=False,
        comment="Cantidad de acciones - ENCRIPTADO AES-256-GCM"
    )
    
    average_price = Column(
        EncryptedNumeric,
        nullable=False,
        comment="Precio promedio de compra - ENCRIPTADO AES-256-GCM"
    )
    
    # ============================================
    # RELACIONES
    # ============================================
    
    user = relationship(
        "User",
        back_populates="investments"
    )
    
    # ============================================
    # MÉTODOS
    # ============================================
    
    def __repr__(self):
        return f"<Investment(id={self.id}, status={self.status}, user_id={self.user_id})>"
    
    def to_dict(self):
        """Convierte el objeto a diccionario con datos desencriptados"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "symbol": self.symbol,
            "company_name": self.company_name,
            "shares": float(self.shares) if self.shares else 0.0,
            "average_price": float(self.average_price) if self.average_price else 0.0,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "sale_price": float(self.sale_price) if self.sale_price else None,
            "sale_date": self.sale_date.isoformat() if self.sale_date else None,
            "status": self.status.value if self.status else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    # ============================================
    # PROPERTIES Y HELPERS
    # ============================================
    
    def get_shares_as_decimal(self) -> Decimal:
        """Devuelve shares como Decimal"""
        if self.shares is None:
            return Decimal("0.0000")
        if isinstance(self.shares, Decimal):
            return self.shares
        return Decimal(str(self.shares))
    
    def get_average_price_as_decimal(self) -> Decimal:
        """Devuelve average_price como Decimal"""
        if self.average_price is None:
            return Decimal("0.00")
        if isinstance(self.average_price, Decimal):
            return self.average_price
        return Decimal(str(self.average_price))
    
    @property
    def total_cost(self) -> Decimal:
        """Costo total de la inversión (shares * average_price)"""
        return self.get_shares_as_decimal() * self.get_average_price_as_decimal()
    
    @property
    def is_active(self) -> bool:
        """Verifica si la inversión está activa"""
        return self.status == InvestmentStatus.ACTIVE
    
    @property
    def is_sold(self) -> bool:
        """Verifica si la inversión fue vendida"""
        return self.status == InvestmentStatus.SOLD
    
    def calculate_gain_loss(self, current_price: Decimal) -> Decimal:
        """
        Calcula ganancia/pérdida para un precio dado.
        
        Args:
            current_price: Precio actual de la acción
            
        Returns:
            Decimal: Ganancia (positivo) o pérdida (negativo)
        """
        if self.is_sold and self.sale_price:
            price = Decimal(str(self.sale_price))
        else:
            price = Decimal(str(current_price))
        
        shares = self.get_shares_as_decimal()
        avg_price = self.get_average_price_as_decimal()
        
        return (price - avg_price) * shares
    
    def calculate_gain_loss_percent(self, current_price: Decimal) -> Decimal:
        """
        Calcula porcentaje de ganancia/pérdida.
        
        Args:
            current_price: Precio actual de la acción
            
        Returns:
            Decimal: Porcentaje de ganancia/pérdida
        """
        avg_price = self.get_average_price_as_decimal()
        if avg_price == 0:
            return Decimal("0.00")
        
        if self.is_sold and self.sale_price:
            price = Decimal(str(self.sale_price))
        else:
            price = Decimal(str(current_price))
        
        return ((price - avg_price) / avg_price) * 100
