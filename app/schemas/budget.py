from pydantic import BaseModel, Field, UUID4, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# ============================================
# BUDGET ITEM SCHEMAS
# ============================================

class BudgetItemBase(BaseModel):
    """Schema base para partidas de presupuesto"""
    category_id: UUID4 = Field(..., description="ID de la categoría")
    allocated_amount: Decimal = Field(..., ge=0, description="Monto asignado a esta partida")
    notes: Optional[str] = Field(None, description="Notas opcionales sobre esta partida")

class BudgetItemCreate(BudgetItemBase):
    """Schema para crear una partida de presupuesto"""
    pass

class BudgetItemUpdate(BudgetItemBase):
    """Schema para actualizar una partida de presupuesto"""
    category_id: Optional[UUID4] = None
    allocated_amount: Optional[Decimal] = Field(None, ge=0)

class BudgetItemResponse(BudgetItemBase):
    """Schema de respuesta para una partida de presupuesto"""
    id: UUID4
    budget_id: UUID4
    category_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ============================================
# BUDGET SCHEMAS
# ============================================

class BudgetBase(BaseModel):
    """Schema base para presupuestos"""
    month: int = Field(..., ge=1, le=12, description="Mes del presupuesto (1-12)")
    year: int = Field(..., ge=2000, le=2100, description="Año del presupuesto")
    name: Optional[str] = Field(None, max_length=200, description="Nombre opcional del presupuesto")

class BudgetCreate(BudgetBase):
    """Schema para crear un presupuesto"""
    items: List[BudgetItemCreate] = Field(..., min_length=1, description="Lista de partidas del presupuesto")
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v):
        if not v:
            raise ValueError('El presupuesto debe tener al menos una partida')
        
        # Verificar que no haya categorías duplicadas
        category_ids = [item.category_id for item in v]
        if len(category_ids) != len(set(category_ids)):
            raise ValueError('No puede haber categorías duplicadas en el presupuesto')
        
        return v

class BudgetUpdate(BaseModel):
    """Schema para actualizar un presupuesto"""
    month: Optional[int] = Field(None, ge=1, le=12)
    year: Optional[int] = Field(None, ge=2000, le=2100)
    name: Optional[str] = Field(None, max_length=200)
    items: Optional[List[BudgetItemCreate]] = None
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v):
        if v is not None:
            if not v:
                raise ValueError('El presupuesto debe tener al menos una partida')
            
            # Verificar que no haya categorías duplicadas
            category_ids = [item.category_id for item in v]
            if len(category_ids) != len(set(category_ids)):
                raise ValueError('No puede haber categorías duplicadas en el presupuesto')
        
        return v

class BudgetResponse(BudgetBase):
    """Schema de respuesta para un presupuesto"""
    id: UUID4
    user_id: UUID4
    total_budget: Decimal
    items: List[BudgetItemResponse] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class BudgetListResponse(BudgetBase):
    """Schema de respuesta simplificado para lista de presupuestos"""
    id: UUID4
    user_id: UUID4
    total_budget: Decimal
    items_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ============================================
# BUDGET COPY SCHEMA
# ============================================

class BudgetCopyRequest(BaseModel):
    """Schema para copiar un presupuesto a otro mes"""
    target_month: int = Field(..., ge=1, le=12, description="Mes destino")
    target_year: int = Field(..., ge=2000, le=2100, description="Año destino")

# ============================================
# BUDGET PROGRESS SCHEMAS
# ============================================

class ItemProgress(BaseModel):
    """Progreso de una partida individual"""
    id: UUID4  # ID del budget item
    category_id: UUID4
    category_name: str
    allocated: Decimal
    spent: Decimal
    remaining: Decimal
    percent_used: float
    status: str = Field(..., pattern="^(ok|warning|over)$")
    transaction_count: int = 0

class BudgetProgress(BaseModel):
    """Progreso completo del presupuesto"""
    budget_id: UUID4
    month: int
    year: int
    total_allocated: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    percent_used: float
    status: str = Field(..., pattern="^(ok|warning|over)$")
    items: List[ItemProgress] = []

# ============================================
# BUDGET SUMMARY SCHEMA
# ============================================

class BudgetSummary(BaseModel):
    """Resumen ejecutivo del presupuesto"""
    budget_id: UUID4
    month: int
    year: int
    total_allocated: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    percent_used: float
    status: str
    overspent_categories: List[str] = []
    categories_at_risk: List[str] = []  # Categorías entre 80-100%
    categories_ok: List[str] = []  # Categorías < 80%

# ============================================
# BUDGET COMPARISON SCHEMA
# ============================================

class CategoryComparison(BaseModel):
    """Comparación de una categoría entre dos presupuestos"""
    category_name: str
    budget1_amount: Decimal
    budget2_amount: Decimal
    difference: Decimal
    percent_change: float

class BudgetComparison(BaseModel):
    """Comparación entre dos presupuestos"""
    budget1_id: UUID4
    budget1_period: str  # "Enero 2025"
    budget2_id: UUID4
    budget2_period: str  # "Febrero 2025"
    total_difference: Decimal
    categories: List[CategoryComparison] = []

# ============================================
# SUGGESTED BUDGET SCHEMA
# ============================================

class SuggestedBudgetItem(BaseModel):
    """Partida sugerida basada en histórico"""
    category_id: UUID4
    category_name: str
    suggested_amount: Decimal
    based_on_average: Decimal
    months_analyzed: int

class SuggestedBudget(BaseModel):
    """Presupuesto sugerido basado en histórico de gastos"""
    suggested_for_month: int
    suggested_for_year: int
    total_suggested: Decimal
    items: List[SuggestedBudgetItem] = []
    analysis_period: str  # "Últimos 3 meses"

# ============================================
# OVERSPENT CATEGORIES SCHEMA
# ============================================

class OverspentCategory(BaseModel):
    """Categoría que ha superado el presupuesto"""
    category_id: UUID4
    category_name: str
    allocated: Decimal
    spent: Decimal
    overspent_amount: Decimal
    percent_over: float
