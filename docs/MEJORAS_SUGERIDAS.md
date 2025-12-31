# Mejoras Sugeridas para Modelos y Schemas

## 1. Añadir Constraints a Nivel de Base de Datos

### En `account.py` (Modelo):
```python
from sqlalchemy import CheckConstraint

class Account(Base):
    # ... existing code ...
    
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('cash', 'bank', 'savings', 'credit', 'investment')",
            name='valid_account_type'
        ),
        CheckConstraint("balance >= 0", name='positive_balance'),
    )
```

### En `category.py` (Modelo):
```python
from sqlalchemy import CheckConstraint

class Category(Base):
    # ... existing code ...
    
    __table_args__ = (
        CheckConstraint(
            "color ~ '^#[0-9A-Fa-f]{6}$'",
            name='valid_hex_color'
        ),
    )
```

### En `transaction.py` (Modelo):
```python
from sqlalchemy import CheckConstraint

class Transaction(Base):
    # ... existing code ...
    
    __table_args__ = (
        Index('idx_transaction_date', 'date'),  # Ya lo tienes
        CheckConstraint("amount != 0", name='non_zero_amount'),
    )
```

## 2. Validadores Custom en Schemas

### En `transaction.py` (Schema):
```python
from pydantic import field_validator

class TransactionCreate(TransactionBase):
    @field_validator('amount')
    def validate_amount(cls, v):
        if v == 0:
            raise ValueError('El monto no puede ser cero')
        return v
    
    @field_validator('date')
    def validate_date_not_future(cls, v):
        from datetime import date
        if v > date.today():
            raise ValueError('La fecha no puede ser futura')
        return v
```

## 3. Índices Adicionales para Performance

### En `transaction.py` (Modelo):
```python
from sqlalchemy import Index

class Transaction(Base):
    # ... existing code ...
    
    __table_args__ = (
        Index('idx_transaction_date', 'date'),  # Ya existe
        Index('idx_transaction_account_id', 'account_id'),  # Nuevo
        Index('idx_transaction_category_id', 'category_id'),  # Nuevo
        Index('idx_transaction_date_account', 'account_id', 'date'),  # Compuesto
    )
```

## 4. Soft Deletes (Opcional)

Si quieres mantener histórico de elementos eliminados:

```python
from datetime import datetime

class Account(Base):
    # ... existing code ...
    deleted_at = Column(DateTime, nullable=True, default=None)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
```

## 5. Validación de Transferencias

### En `transaction.py` (Schema):
```python
from pydantic import model_validator

class TransactionCreate(TransactionBase):
    @model_validator(mode='after')
    def validate_transfer(self):
        # Si es transferencia, debe tener transfer_account_id
        if self.transaction_type == 'transfer' and not self.transfer_account_id:
            raise ValueError('Las transferencias requieren transfer_account_id')
        
        # Si tiene transfer_account_id, debe ser transferencia
        if self.transfer_account_id and self.transaction_type != 'transfer':
            raise ValueError('Solo las transferencias pueden tener transfer_account_id')
        
        # No puede transferir a la misma cuenta
        if self.transfer_account_id == self.account_id:
            raise ValueError('No se puede transferir a la misma cuenta')
        
        return self
```

## 6. Timestamps Automáticos

Ya tienes `created_at` y `updated_at`. Considera añadir:

```python
from sqlalchemy import event

# En database.py o models/__init__.py
@event.listens_for(Base, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()
```

## 7. Paginación en Schemas

```python
# En schemas/__init__.py o nuevo archivo pagination.py
from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

---

**Nota**: Estas son mejoras opcionales. Tu código actual es funcional y bien estructurado.
