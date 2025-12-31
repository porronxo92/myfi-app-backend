from pydantic import BaseModel, Field, UUID4, ConfigDict, field_serializer
from typing import Optional
from datetime import datetime
from uuid import UUID

# ============================================
# SCHEMA BASE (campos comunes)
# ============================================
class AccountBase(BaseModel):
    """Campos base que comparten todos los schemas"""
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(checking|savings|investment|credit_card|cash)$")
    balance: float = 0.0
    currency: str = "EUR"
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = ""

# ============================================
# SCHEMA PARA CREAR (POST)
# ============================================
class AccountCreate(AccountBase):
    """
    Schema para POST /api/accounts
    
    Ejemplo de request:
    {
      "name": "Cuenta Bankinter",
      "type": "checking",
      "balance": 1000.00,
      "bank_name": "Bankinter"
    }
    
    Nota: user_id se asigna automáticamente al usuario autenticado
    """
    user_id: Optional[UUID] = None  # Se asigna automáticamente en el endpoint

# ============================================
# SCHEMA PARA ACTUALIZAR (PUT/PATCH)
# ============================================
class AccountUpdate(BaseModel):
    """
    Schema para PUT /api/accounts/{id}
    
    Todos los campos son OPCIONALES (puedes actualizar solo lo que quieras)
    
    Ejemplo:
    {
      "name": "Nueva Cuenta",
      "balance": 1500.00
    }
    """
    name: Optional[str] = None
    type: Optional[str] = None
    balance: Optional[float] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

# ============================================
# SCHEMA PARA RESPONDER (GET)
# ============================================
class AccountResponse(AccountBase):
    """
    Schema para GET /api/accounts
    
    Incluye campos adicionales que vienen de la BBDD
    
    Ejemplo de response:
    {
      "id": "uuid-123",
      "name": "Cuenta Bankinter",
      "type": "checking",
      "balance": 1000.00,
      "created_at": "2025-01-15T10:30:00",
      "transaction_count": 45,
      "calculated_balance": 1023.50
    }
    """
    id: UUID4  # Campo que viene de BBDD
    created_at: datetime
    
    # Campos calculados (opcionales)
    transaction_count: Optional[int] = 0
    calculated_balance: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Convierte datetime a string ISO"""
        return dt.isoformat() if dt else None