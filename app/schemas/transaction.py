from pydantic import BaseModel, Field, UUID4, ConfigDict, field_validator, model_validator, field_serializer
from typing import Optional, List, Union
from datetime import date as date_type, datetime

# ============================================
# SCHEMA BASE
# ============================================
class TransactionBase(BaseModel):
    date: date_type = Field(..., description="Fecha de la transacción")
    amount: float = Field(..., description="Importe (positivo=ingreso, negativo=gasto)")
    description: str = Field(..., min_length=1, max_length=500)
    category_id: Optional[Union[UUID4, str]] = None  # Acepta UUID o nombre de categoría
    type: str = Field(..., pattern="^(income|expense|transfer)$")
    notes: Optional[str] = ""
    tags: Optional[List[str]] = []  # Array de etiquetas
    source: Optional[str] = Field(default="manual", max_length=50, description="Origen: manual, automatico, import, api")

# ============================================
# SCHEMA PARA CREAR
# ============================================
class TransactionCreate(TransactionBase):
    """
    POST /api/transactions
    
    El campo category_id acepta tanto UUID como nombre de categoría:
    
    Request con UUID:
    {
      "account_id": "uuid-cuenta",
      "date": "2025-01-15",
      "amount": -50.00,
      "description": "Mercadona",
      "category_id": "uuid-supermercado",
      "type": "expense"
    }
    
    Request con nombre de categoría:
    {
      "account_id": "uuid-cuenta",
      "date": "2025-01-15",
      "amount": -50.00,
      "description": "Mercadona",
      "category_id": "Alimentación",
      "type": "expense"
    }
    
    Alternativamente, puedes usar el campo 'categoria':
    {
      "account_id": "uuid-cuenta",
      "categoria": "Alimentación",
      ...
    }
    """
    account_id: UUID4  # Requerido en creación
    transfer_account_id: Optional[UUID4] = None
    categoria: Optional[str] = None  # Campo alternativo para nombre de categoría
    
    @field_validator('transfer_account_id', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convierte string vacío a None"""
        if v == "" or v is None:
            return None
        return v
    
    @field_validator('category_id', mode='before')
    @classmethod
    def normalize_category_id(cls, v):
        """Normaliza category_id: convierte string vacío a None y aplica trim a strings"""
        if v == "" or v is None:
            return None
        # Si es string (nombre de categoría), aplicar trim
        if isinstance(v, str):
            return v.strip()
        return v
    
    @field_validator('categoria', mode='before')
    @classmethod
    def normalize_categoria(cls, v):
        """Normaliza campo 'categoria': aplica trim"""
        if v == "" or v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v == 0:
            raise ValueError('El monto no puede ser cero')
        return v
    
    @field_validator('date')
    @classmethod
    def validate_date_not_future(cls, v):
        from datetime import date as dt_date
        if v > dt_date.today():
            raise ValueError('La fecha no puede ser futura')
        return v
    
    @model_validator(mode='after')
    def validate_categoria_priority(self):
        """Si se proporciona 'categoria', tiene prioridad sobre 'category_id'"""
        if self.categoria:
            self.category_id = self.categoria
            self.categoria = None  # Limpiar para evitar confusión
        return self
    
    @model_validator(mode='after')
    def validate_transfer(self):
        # Si es transferencia (tipo legacy), debe tener transfer_account_id
        if self.type == 'transfer' and not self.transfer_account_id:
            raise ValueError('Las transferencias requieren transfer_account_id')
        
        # No puede transferir a la misma cuenta
        if self.transfer_account_id and self.transfer_account_id == self.account_id:
            raise ValueError('No se puede transferir a la misma cuenta')
        
        # NOTA: Permitimos transfer_account_id en transacciones income/expense
        # para permitir transferencias entre cuentas mediante dos transacciones vinculadas:
        # - Transacción expense en cuenta origen (salida)
        # - Transacción income en cuenta destino (entrada)
        
        return self

# ============================================
# SCHEMA PARA ACTUALIZAR
# ============================================
class TransactionUpdate(BaseModel):
    """
    PUT /api/transactions/{id}
    
    Puedes actualizar solo los campos que necesites
    
    Request:
    {
      "category_id": "uuid-otra-categoria",
      "notes": "Compra mensual"
    }
    """
    date: Optional[date_type] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    category_id: Optional[UUID4] = None
    type: Optional[str] = None
    notes: Optional[str] = None

# ============================================
# SCHEMA DE RESPUESTA
# ============================================
class TransactionResponse(TransactionBase):
    """
    GET /api/transactions
    
    Response incluye relaciones:
    {
      "id": "uuid",
      "account_id": "uuid-cuenta",
      "date": "2025-01-15",
      "amount": -50.00,
      "description": "Mercadona",
      "type": "expense",
      "account_name": "Cuenta Bankinter",  # ⭐ JOIN
      "category_name": "Supermercado",     # ⭐ JOIN
      "category_color": "#10B981",
      "source": "import",
      "created_at": "2025-01-15T10:30:00"
    }
    """
    id: UUID4
    account_id: UUID4
    source: str  # manual, import, api
    created_at: datetime
    
    # Campos de relaciones (JOINs)
    account_name: Optional[str] = None
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @model_validator(mode='before')
    @classmethod
    def populate_relationships(cls, data):
        """
        Popula los campos de relaciones desde el ORM.
        
        Extrae account_name, category_name y category_color desde las relaciones
        cargadas por joinedload() en el servicio, evitando el problema N+1.
        """
        # Si data es un objeto ORM (Transaction), extraemos las relaciones
        if hasattr(data, 'account'):
            if not isinstance(data, dict):
                obj_data = {
                    'id': data.id,
                    'account_id': data.account_id,
                    'date': data.date,
                    'amount': data.amount,
                    'description': data.description,
                    'category_id': data.category_id,
                    'type': data.type,
                    'notes': data.notes,
                    'tags': data.tags,
                    'source': data.source,
                    'created_at': data.created_at,
                    # Relaciones
                    'account_name': data.account.name if data.account else None,
                    'category_name': data.category.name if data.category else None,
                    'category_color': data.category.color if data.category else None,
                }
                return obj_data
        return data
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Convierte datetime a string ISO"""
        return dt.isoformat() if dt else None