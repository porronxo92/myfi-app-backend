from sqlalchemy import Column, String, DateTime, CheckConstraint, UniqueConstraint, DECIMAL, ForeignKey, Text, func as sql_func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

class BudgetItem(Base):
    """
    Modelo ORM para la tabla 'budget_items'
    
    Representa una partida individual dentro de un presupuesto
    """
    
    __tablename__ = "budget_items"
    
    __table_args__ = (
        UniqueConstraint('budget_id', 'category_id', name='unique_category_per_budget'),
        CheckConstraint('allocated_amount >= 0', name='positive_allocated_amount'),
    )
    
    # ============================================
    # COLUMNAS
    # ============================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único de la partida"
    )
    
    budget_id = Column(
        UUID(as_uuid=True),
        ForeignKey('budgets.id', ondelete='CASCADE'),
        nullable=False,
        comment="ID del presupuesto padre"
    )
    
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey('categories.id', ondelete='RESTRICT'),
        nullable=False,
        comment="ID de la categoría de gasto"
    )
    
    allocated_amount = Column(
        DECIMAL(12, 2),
        nullable=False,
        comment="Cantidad asignada a esta partida"
    )
    
    notes = Column(
        Text,
        nullable=True,
        comment="Notas opcionales sobre esta partida"
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
    
    budget = relationship(
        "Budget",
        back_populates="items"
    )
    
    category = relationship(
        "Category",
        lazy="joined"
    )
    
    # ============================================
    # MÉTODOS AUXILIARES
    # ============================================
    
    def calculate_spent_amount(self, db):
        """
        Calcular cuánto se ha gastado realmente en esta categoría durante el mes del presupuesto
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Decimal: Monto total gastado
        """
        from app.models.transaction import Transaction
        from app.models.account import Account
        from sqlalchemy import extract, and_
        from decimal import Decimal
        
        # Obtener transacciones de la categoría en el mes/año del presupuesto
        # JOIN con Account para filtrar por user_id
        spent = db.query(sql_func.coalesce(sql_func.sum(Transaction.amount), 0)).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            and_(
                Transaction.category_id == self.category_id,
                Account.user_id == self.budget.user_id,
                extract('month', Transaction.date) == self.budget.month,
                extract('year', Transaction.date) == self.budget.year,
                Transaction.type == 'expense'  # Solo gastos
            )
        ).scalar()
        
        return Decimal(spent) if spent else Decimal(0)
    
    def get_remaining_amount(self, db):
        """
        Calcular cuánto queda disponible en esta partida
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Decimal: Monto restante (puede ser negativo si se excedió)
        """
        spent = self.calculate_spent_amount(db)
        return self.allocated_amount - spent
    
    def get_consumption_percent(self, db):
        """
        Calcular el porcentaje de consumo del presupuesto
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            float: Porcentaje de consumo (0-100+)
        """
        if self.allocated_amount == 0:
            return 0.0
        
        spent = self.calculate_spent_amount(db)
        return float((spent / self.allocated_amount) * 100)
    
    def get_status(self, db):
        """
        Determinar el estado de la partida según el consumo
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            str: 'ok', 'warning', o 'over'
        """
        percent = self.get_consumption_percent(db)
        
        if percent >= 100:
            return 'over'
        elif percent >= 80:
            return 'warning'
        else:
            return 'ok'
    
    def __repr__(self):
        return f"<BudgetItem(id={self.id}, budget_id={self.budget_id}, category_id={self.category_id}, allocated={self.allocated_amount})>"
