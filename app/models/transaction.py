from sqlalchemy import Column, String, Numeric, Date, DateTime, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

class Transaction(Base):
    """
    Modelo ORM para la tabla 'transactions'
    
    Todas las transacciones financieras (ingresos, gastos, transferencias)
    """
    
    __tablename__ = "transactions"
    
    __table_args__ = (
        Index('idx_transaction_date', 'date'),
        Index('idx_transaction_account_id', 'account_id'),
        Index('idx_transaction_category_id', 'category_id'),
        Index('idx_transaction_date_account', 'account_id', 'date'),
        CheckConstraint("amount != 0", name='non_zero_amount'),
    )
    
    # ============================================
    # COLUMNAS
    # ============================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
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
        index=True,  # Índice para búsquedas rápidas por fecha
        comment="Fecha de la transacción"
    )
    
    amount = Column(
        Numeric(12, 2),
        nullable=False,
        comment="Importe: positivo (ingreso), negativo (gasto)"
    )
    
    description = Column(
        String(500),
        nullable=False,
        comment="Descripción/concepto de la transacción"
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
        comment="income, expense, transfer"
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
        comment="Notas adicionales"
    )
    
    tags = Column(
        ARRAY(String),
        nullable=True,
        comment="Array de etiquetas"
    )
    
    external_id = Column(
        String(100),
        nullable=True,
        comment="ID del banco (para evitar duplicados)"
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
    # RELACIONES
    # ============================================
    
    account = relationship(
        "Account",
        back_populates="transactions",
        foreign_keys=[account_id]
    )
    # Puedes hacer: transaction.account.name
    
    category = relationship(
        "Category",
        back_populates="transactions"
    )
    # Puedes hacer: transaction.category.name
    
    transfer_account = relationship(
        "Account",
        foreign_keys=[transfer_account_id]
    )
    # Para transferencias: transaction.transfer_account.name
    
    # ============================================
    # MÉTODOS
    # ============================================
    
    def __repr__(self):
        return f"<Transaction(date={self.date}, amount={self.amount}, desc='{self.description[:30]}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "date": self.date.isoformat(),
            "amount": float(self.amount),
            "description": self.description,
            "category_id": str(self.category_id) if self.category_id else None,
            "type": self.type,
            "transfer_account_id": str(self.transfer_account_id) if self.transfer_account_id else None,
            "notes": self.notes,
            "tags": self.tags,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # Relaciones
            "account_name": self.account.name if self.account else None,
            "category_name": self.category.name if self.category else None,
            "category_color": self.category.color if self.category else None
        }
    
    @property
    def is_expense(self):
        """Verifica si es un gasto"""
        return self.amount < 0
    
    @property
    def is_income(self):
        """Verifica si es un ingreso"""
        return self.amount > 0
    
    @property
    def absolute_amount(self):
        """Devuelve el valor absoluto del importe"""
        return abs(float(self.amount))