from sqlalchemy import Column, String, Boolean, Numeric, DateTime, Text, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

class Account(Base):
    """
    Modelo ORM para la tabla 'accounts'
    
    Representa cuentas bancarias del usuario
    """
    
    # ============================================
    # Nombre de la tabla en PostgreSQL
    # ============================================
    __tablename__ = "accounts"
    
    __table_args__ = (
        CheckConstraint(
            "type IN ('checking', 'savings', 'investment', 'credit_card', 'cash')",
            name='valid_account_type'
        ),
        CheckConstraint("balance >= 0", name='positive_balance'),
    )
    
    # ============================================
    # COLUMNAS (mapean a campos de la tabla)
    # ============================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único de la cuenta"
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=True,  # Nullable para mantener compatibilidad con datos existentes
        comment="Usuario propietario de la cuenta (FK)"
    )
    
    name = Column(
        String(100),
        nullable=False,
        comment="Nombre descriptivo de la cuenta"
    )
    
    type = Column(
        String(20),
        nullable=False,
        comment="Tipo: checking, savings, investment, credit_card, cash"
    )
    
    balance = Column(
        Numeric(12, 2),
        nullable=False,
        default=0.00,
        comment="Saldo actual de la cuenta"
    )
    
    currency = Column(
        String(3),
        nullable=False,
        default='EUR',
        comment="Moneda de la cuenta"
    )
    
    bank_name = Column(
        String(100),
        nullable=True,
        comment="Nombre del banco"
    )
    
    account_number = Column(
        String(50),
        nullable=True,
        comment="IBAN o número de cuenta"
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Si la cuenta está activa"
    )
    
    notes = Column(
        Text,
        nullable=True,
        comment="Notas adicionales"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Fecha de creación"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Fecha de última actualización"
    )
    
    # ============================================
    # RELACIONES (JOINs automáticos)
    # ============================================
    
    user = relationship(
        "User",
        back_populates="accounts"
    )
    # Relación con el usuario propietario
    
    transactions = relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="select",
        foreign_keys="[Transaction.account_id]"
    )
    # Explicación:
    # - "Transaction": Relacionado con el modelo Transaction
    # - back_populates="account": La relación inversa
    # - cascade="all, delete-orphan": Si borras la cuenta, borra sus transacciones
    # - lazy="select": Carga las transacciones solo cuando las pides
    # - foreign_keys: Especifica qué FK usar (account_id, NO transfer_account_id)
    
    # ============================================
    # MÉTODOS ÚTILES
    # ============================================
    
    def __repr__(self):
        """Representación legible del objeto"""
        return f"<Account(id={self.id}, name='{self.name}', balance={self.balance})>"
    
    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            "id": str(self.id),
            "name": self.name,
            "type": self.type,
            "balance": float(self.balance),
            "currency": self.currency,
            "bank_name": self.bank_name,
            "account_number": self.account_number,
            "is_active": self.is_active,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def transaction_count(self):
        """Número de transacciones de esta cuenta"""
        return len(self.transactions)
    
    def calculate_balance(self, db_session):
        """Calcula el balance sumando todas las transacciones"""
        from sqlalchemy import func
        result = db_session.query(
            func.sum(Transaction.amount)
        ).filter(
            Transaction.account_id == self.id
        ).scalar()
        
        return float(result) if result else 0.0