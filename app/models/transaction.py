"""
Modelo Transaction - Transacciones Financieras
===============================================

SEGURIDAD (GDPR/PSD2):
- amount, description: Encriptados con AES-256-GCM
- Los datos se almacenan encriptados en PostgreSQL
- TypeDecorators manejan encriptación/desencriptación automáticamente
- Filtrado por monto se realiza en Python (no en SQL)
"""

from sqlalchemy import Column, String, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
import uuid

from app.database import Base
from app.models.encrypted_fields import EncryptedString, EncryptedNumeric


class Transaction(Base):
    """
    Modelo ORM para la tabla 'transactions'
    
    Todas las transacciones financieras (ingresos, gastos, transferencias).
    Los datos financieros están encriptados con AES-256-GCM.
    """
    
    __tablename__ = "transactions"
    
    __table_args__ = (
        Index('idx_transaction_date', 'date'),
        Index('idx_transaction_account_id', 'account_id'),
        Index('idx_transaction_category_id', 'category_id'),
        Index('idx_transaction_date_account', 'account_id', 'date'),
    )
    
    # ============================================
    # COLUMNAS IDENTIFICADORAS (no sensibles)
    # ============================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único"
    )
    
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey('accounts.id', ondelete='CASCADE'),
        nullable=False,
        comment="Cuenta asociada (FK)"
    )
    
    date = Column(
        Date,
        nullable=False,
        index=True,
        comment="Fecha de la transacción"
    )
    
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey('categories.id', ondelete='SET NULL'),
        nullable=True,
        comment="Categoría de la transacción (FK)"
    )
    
    type = Column(
        String(20),
        nullable=False,
        comment="Tipo: income, expense, transfer"
    )
    
    transfer_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey('accounts.id', ondelete='SET NULL'),
        nullable=True,
        comment="Cuenta destino si es transferencia"
    )
    
    notes = Column(
        Text,
        nullable=True,
        comment="Notas adicionales (no encriptadas)"
    )
    
    tags = Column(
        ARRAY(String),
        nullable=True,
        comment="Array de etiquetas"
    )
    
    external_id = Column(
        String(100),
        nullable=True,
        comment="ID externo del banco (para evitar duplicados)"
    )
    
    source = Column(
        String(50),
        nullable=False,
        default='manual',
        comment="Origen: manual, import, api"
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
    
    amount = Column(
        EncryptedNumeric,
        nullable=False,
        comment="Importe - ENCRIPTADO AES-256-GCM"
    )
    
    description = Column(
        EncryptedString(500),
        nullable=False,
        comment="Descripción - ENCRIPTADO AES-256-GCM"
    )
    
    # ============================================
    # RELACIONES
    # ============================================
    
    account = relationship(
        "Account",
        back_populates="transactions",
        foreign_keys=[account_id]
    )
    
    category = relationship(
        "Category",
        back_populates="transactions"
    )
    
    transfer_account = relationship(
        "Account",
        foreign_keys=[transfer_account_id]
    )
    
    # ============================================
    # MÉTODOS
    # ============================================
    
    def __repr__(self):
        return f"<Transaction(date={self.date}, type={self.type}, id={self.id})>"
    
    def to_dict(self):
        """Convierte el objeto a diccionario con datos desencriptados"""
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "date": self.date.isoformat() if self.date else None,
            "amount": float(self.amount) if self.amount else 0.0,
            "description": self.description,
            "category_id": str(self.category_id) if self.category_id else None,
            "type": self.type,
            "transfer_account_id": str(self.transfer_account_id) if self.transfer_account_id else None,
            "notes": self.notes,
            "tags": self.tags,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "account_name": self.account.name if self.account else None,
            "category_name": self.category.name if self.category else None,
            "category_color": self.category.color if self.category else None
        }
    
    # ============================================
    # PROPERTIES
    # ============================================
    
    @property
    def is_expense(self) -> bool:
        """Verifica si es un gasto (amount negativo o type='expense')"""
        if self.amount is None:
            return self.type == 'expense'
        return float(self.amount) < 0 or self.type == 'expense'
    
    @property
    def is_income(self) -> bool:
        """Verifica si es un ingreso (amount positivo o type='income')"""
        if self.amount is None:
            return self.type == 'income'
        return float(self.amount) > 0 or self.type == 'income'
    
    @property
    def absolute_amount(self) -> float:
        """Devuelve el valor absoluto del importe"""
        if self.amount is None:
            return 0.0
        return abs(float(self.amount))
    
    def get_amount_as_decimal(self) -> Decimal:
        """
        Devuelve el amount como Decimal.
        
        Returns:
            Decimal: Monto de la transacción (0 si es None)
        """
        if self.amount is None:
            return Decimal("0.00")
        if isinstance(self.amount, Decimal):
            return self.amount
        return Decimal(str(self.amount))
