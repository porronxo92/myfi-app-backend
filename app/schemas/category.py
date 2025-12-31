from pydantic import BaseModel, Field, UUID4, ConfigDict, field_serializer, computed_field
from typing import Optional
from datetime import datetime

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(income|expense)$")
    color: str = Field(default="#6B7280", pattern="^#[0-9A-Fa-f]{6}$")

class CategoryCreate(CategoryBase):
    """POST /api/categories"""
    pass

class CategoryUpdate(BaseModel):
    """PUT /api/categories/{id}"""
    name: Optional[str] = None
    color: Optional[str] = None

class CategoryResponse(CategoryBase):
    """
    GET /api/categories
    
    Response:
    {
      "id": "uuid",
      "name": "Supermercado",
      "type": "expense",
      "color": "#10B981",
      "transaction_count": 45,      # Cuántas transacciones
      "total_amount": 0.0,          # Total gastado (calculado en backend)
      "created_at": "2025-01-01T00:00:00"
    }
    """
    id: UUID4
    created_at: datetime
    
    # Estadísticas (opcionales, calculadas en el servicio)
    transaction_count: Optional[int] = 0
    total_amount: Optional[float] = 0.0
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Convierte datetime a string ISO"""
        return dt.isoformat() if dt else None