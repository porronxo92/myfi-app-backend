from sqlalchemy import Column, String, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

class Category(Base):
    """
    Modelo ORM para la tabla 'categories'
    
    Categorías de ingresos y gastos
    """
    
    __tablename__ = "categories"
    
    __table_args__ = (
        CheckConstraint(
            "color ~ '^#[0-9A-Fa-f]{6}$'",
            name='valid_hex_color'
        ),
    )
    
    # ============================================
    # COLUMNAS
    # ============================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    name = Column(
        String(100),
        nullable=False,
        unique=True,
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
        """Total gastado/ingresado en esta categoría"""
        from sqlalchemy import func
        result = db_session.query(
            func.sum(Transaction.amount)
        ).filter(
            Transaction.category_id == self.id
        ).scalar()
        
        return float(result) if result else 0.0