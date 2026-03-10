"""
Modelo Account - Cuentas Bancarias
===================================

SEGURIDAD (GDPR/PSD2):
- balance, account_number, notes: Encriptados con AES-256-GCM
- Los datos se almacenan encriptados en PostgreSQL
- TypeDecorators manejan encriptación/desencriptación automáticamente
- Filtrado y agregaciones se hacen en Python (no en SQL)
"""

from sqlalchemy import Column, String, Boolean, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
import uuid

from app.database import Base
from app.models.encrypted_fields import EncryptedString, EncryptedText, EncryptedNumeric


class Account(Base):
    """
    Modelo ORM para la tabla 'accounts'
    
    Representa cuentas bancarias del usuario.
    Todos los datos financieros están encriptados con AES-256-GCM.
    """
    
    __tablename__ = "accounts"
    
    __table_args__ = (
        CheckConstraint(
            "type IN ('checking', 'savings', 'investment', 'credit_card', 'cash')",
            name='valid_account_type'
        ),
    )
    
    # ============================================
    # COLUMNAS IDENTIFICADORAS (no sensibles)
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
        nullable=True,
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
    
    currency = Column(
        String(3),
        nullable=False,
        default='EUR',
        comment="Moneda de la cuenta (ISO 4217)"
    )
    
    bank_name = Column(
        String(100),
        nullable=True,
        comment="Nombre del banco"
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Si la cuenta está activa"
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
    # COLUMNAS ENCRIPTADAS (AES-256-GCM)
    # ============================================
    
    balance = Column(
        EncryptedNumeric,
        nullable=True,
        default=Decimal("0.00"),
        comment="Saldo actual - ENCRIPTADO AES-256-GCM"
    )
    
    account_number = Column(
        EncryptedString(50),
        nullable=True,
        comment="IBAN/Número de cuenta - ENCRIPTADO AES-256-GCM"
    )
    
    notes = Column(
        EncryptedText,
        nullable=True,
        comment="Notas adicionales - ENCRIPTADO AES-256-GCM"
    )
    
    # ============================================
    # RELACIONES
    # ============================================
    
    user = relationship(
        "User",
        back_populates="accounts"
    )
    
    transactions = relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="select",
        foreign_keys="[Transaction.account_id]"
    )
    
    # ============================================
    # MÉTODOS
    # ============================================
    
    def __repr__(self):
        """Representación legible del objeto"""
        return f"<Account(id={self.id}, name='{self.name}', type='{self.type}')>"
    
    def to_dict(self):
        """Convierte el objeto a diccionario con datos desencriptados"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "name": self.name,
            "type": self.type,
            "balance": float(self.balance) if self.balance else 0.0,
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
        return len(self.transactions) if self.transactions else 0
    
    def get_balance_as_decimal(self) -> Decimal:
        """
        Devuelve el balance como Decimal.
        
        Returns:
            Decimal: Balance de la cuenta (0 si es None)
        """
        if self.balance is None:
            return Decimal("0.00")
        if isinstance(self.balance, Decimal):
            return self.balance
        return Decimal(str(self.balance))
    
    def add_to_balance(self, amount: Decimal):
        """
        Añade un monto al balance.
        
        Args:
            amount: Decimal a añadir (puede ser negativo)
        """
        current = self.get_balance_as_decimal()
        self.balance = current + Decimal(str(amount))
    
    def subtract_from_balance(self, amount: Decimal):
        """
        Resta un monto del balance.
        
        Args:
            amount: Decimal a restar
        """
        current = self.get_balance_as_decimal()
        self.balance = current - Decimal(str(amount))
