from sqlalchemy import Column, String, DateTime, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

class Category(Base):
    """
    Modelo ORM para la tabla 'categories'

    Categorías de ingresos y gastos, asociadas a un usuario específico.
    Cada usuario tiene sus propias categorías (privacidad).
    """

    __tablename__ = "categories"

    __table_args__ = (
        CheckConstraint(
            "color ~ '^#[0-9A-Fa-f]{6}$'",
            name='valid_hex_color'
        ),
        # Nombre único por usuario y tipo (permite "Bizum" en income y expense a la vez)
        UniqueConstraint('user_id', 'name', 'type', name='unique_category_per_user'),
    )

    # ============================================
    # COLUMNAS
    # ============================================

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Usuario propietario de la categoría"
    )

    name = Column(
        String(100),
        nullable=False,
        comment="Nombre de la categoría"
    )

    type = Column(
        String(20),
        nullable=False,
        comment="income o expense"
    )

    color = Column(
        String(7),
        nullable=False,
        default='#6B7280',
        comment="Color hexadecimal para UI"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # ============================================
    # RELACIONES
    # ============================================

    user = relationship(
        "User",
        back_populates="categories"
    )

    transactions = relationship(
        "Transaction",
        back_populates="category",
        lazy="select"
    )
    # No cascade: Si borras una categoría, las transacciones quedan sin categoría (NULL)
    
    # ============================================
    # MÉTODOS
    # ============================================
    
    def __repr__(self):
        return f"<Category(name='{self.name}', type='{self.type}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "type": self.type,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def transaction_count(self):
        """Número de transacciones con esta categoría"""
        return len(self.transactions)
    
    def total_amount(self, db_session):
        """Total gastado/ingresado en esta categoría.
        Nota: Cálculos en Python porque amount está encriptado.
        """
        from app.models.transaction import Transaction

        transactions = db_session.query(Transaction).filter(
            Transaction.category_id == self.id
        ).all()

        # Sumar en Python (amount se desencripta automáticamente)
        total = sum([float(t.amount) if t.amount else 0.0 for t in transactions])

        return total