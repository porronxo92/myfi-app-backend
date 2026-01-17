from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint, UniqueConstraint, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

class Budget(Base):
    """
    Modelo ORM para la tabla 'budgets'
    
    Representa un presupuesto mensual del usuario con sus partidas
    """
    
    __tablename__ = "budgets"
    
    __table_args__ = (
        UniqueConstraint('user_id', 'month', 'year', name='unique_budget_per_month'),
        CheckConstraint('month >= 1 AND month <= 12', name='valid_month'),
        CheckConstraint('year >= 2000 AND year <= 2100', name='valid_year'),
        CheckConstraint('total_budget >= 0', name='positive_total_budget'),
    )
    
    # ============================================
    # COLUMNAS
    # ============================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del presupuesto"
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        comment="Usuario propietario del presupuesto"
    )
    
    month = Column(
        Integer,
        nullable=False,
        comment="Mes del presupuesto (1-12)"
    )
    
    year = Column(
        Integer,
        nullable=False,
        comment="Año del presupuesto"
    )
    
    total_budget = Column(
        DECIMAL(12, 2),
        nullable=False,
        default=0,
        comment="Presupuesto total mensual (suma de todas las partidas)"
    )
    
    name = Column(
        String(200),
        nullable=True,
        comment="Nombre opcional del presupuesto"
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
    # RELACIONES
    # ============================================
    
    user = relationship(
        "User",
        back_populates="budgets"
    )
    
    items = relationship(
        "BudgetItem",
        back_populates="budget",
        cascade="all, delete-orphan",
        lazy="joined"
    )
    
    # ============================================
    # MÉTODOS AUXILIARES
    # ============================================
    
    @classmethod
    def get_current_budget(cls, db, user_id: uuid.UUID):
        """
        Obtener el presupuesto del mes actual para un usuario
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            
        Returns:
            Budget o None si no existe
        """
        from datetime import datetime
        now = datetime.now()
        return db.query(cls).filter(
            cls.user_id == user_id,
            cls.month == now.month,
            cls.year == now.year
        ).first()
    
    @classmethod
    def get_budget_by_period(cls, db, user_id: uuid.UUID, month: int, year: int):
        """
        Obtener presupuesto específico por mes/año
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            month: Mes (1-12)
            year: Año
            
        Returns:
            Budget o None si no existe
        """
        return db.query(cls).filter(
            cls.user_id == user_id,
            cls.month == month,
            cls.year == year
        ).first()
    
    def recalculate_total(self):
        """
        Recalcular el total del presupuesto sumando todas las partidas
        """
        self.total_budget = sum(item.allocated_amount for item in self.items)
    
    def __repr__(self):
        return f"<Budget(id={self.id}, user_id={self.user_id}, month={self.month}, year={self.year}, total={self.total_budget})>"
