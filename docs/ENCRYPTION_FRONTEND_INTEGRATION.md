# Integración de Encriptación con Frontend

## 🎯 Pregunta Clave

**¿Cómo pasar datos encriptados al frontend si borramos los campos originales?**

**Respuesta:** Los campos encriptados **se desencriptan automáticamente** mediante SQLAlchemy `TypeDecorator`. El frontend recibe JSON con valores en claro, sin saber que existe encriptación.

---

## 🔄 Flujo de Datos Completo

### Backend → Frontend (Lectura)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. PostgreSQL (Storage)                                      │
│    amount_encrypted: "v1:A1B2:9x8y7z:tag"  ← ENCRIPTADO     │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. SQLAlchemy TypeDecorator (Auto-desencriptación)          │
│    EncryptedNumeric.process_result_value()                   │
│    → Desencripta: Decimal("150.75")                          │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Modelo ORM Python                                         │
│    transaction.amount_encrypted  → Decimal("150.75")         │
│    ✅ Ya está DESENCRIPTADO                                  │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Pydantic Schema (Serialización)                           │
│    TransactionResponse(amount=150.75)                        │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. FastAPI Response (JSON)                                   │
│    {"amount": 150.75, "description": "Amazon"}               │
│    ✅ Frontend recibe valores en CLARO                       │
└──────────────────────────────────────────────────────────────┘
```

### Frontend → Backend (Escritura)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Frontend envía JSON                                       │
│    POST /api/transactions                                    │
│    {"amount": 150.75, "description": "Amazon"}               │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Pydantic valida y parsea                                  │
│    TransactionCreate(amount=150.75, description="Amazon")    │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Service crea modelo ORM                                   │
│    transaction.amount_encrypted = Decimal("150.75")          │
│    transaction.description_encrypted = "Amazon"              │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. SQLAlchemy TypeDecorator (Auto-encriptación)             │
│    EncryptedNumeric.process_bind_param()                     │
│    → Encripta: "v1:A1B2:9x8y7z:tag"                          │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. PostgreSQL (Storage)                                      │
│    INSERT ... amount_encrypted = 'v1:A1B2:9x8y7z:tag'        │
│    ✅ Datos ENCRIPTADOS en reposo                            │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementación: Migrar de Campos Originales a Encriptados

### Problema

Actualmente el código usa:
```python
# Schemas
class TransactionResponse(BaseModel):
    amount: float
    description: str

# Model validators
obj_data = {
    'amount': data.amount,  # ← Lee campo ORIGINAL
    'description': data.description
}
```

Necesitamos que use `amount_encrypted` y `description_encrypted`.

### Solución 1: @property en Modelos (RECOMENDADO)

Agrega propiedades que hacen que `obj.amount` apunte a `obj.amount_encrypted`:

```python
# app/models/transaction.py
class Transaction(Base):
    # Campos de base de datos
    amount = Column(Numeric(12, 2), comment="[DEPRECATED]")
    amount_encrypted = Column(EncryptedNumeric)
    
    description = Column(String(500), comment="[DEPRECATED]")
    description_encrypted = Column(EncryptedString(500))
    
    # ✅ Properties para compatibilidad
    @property
    def get_amount(self):
        """Devuelve el monto desde el campo encriptado"""
        return self.amount_encrypted if self.amount_encrypted is not None else self.amount
    
    @property
    def get_description(self):
        """Devuelve la descripción desde el campo encriptado"""
        return self.description_encrypted if self.description_encrypted is not None else self.description
```

**Ventajas:**
- ✅ Sin cambios en schemas ni rutas
- ✅ Migración gradual (soporta datos legacy)
- ✅ Código transparente

**Uso:**
```python
# En schemas
obj_data = {
    'amount': data.get_amount,  # ← Usa property
    'description': data.get_description
}
```

### Solución 2: Modificar Model Validators

Cambia los validators para leer directamente de campos `*_encrypted`:

```python
# app/schemas/transaction.py
class TransactionResponse(TransactionBase):
    @model_validator(mode='before')
    @classmethod
    def populate_relationships(cls, data):
        if hasattr(data, 'account'):
            if not isinstance(data, dict):
                obj_data = {
                    'id': data.id,
                    'account_id': data.account_id,
                    'date': data.date,
                    # ✅ Lee de campos encriptados
                    'amount': data.amount_encrypted or data.amount,
                    'description': data.description_encrypted or data.description,
                    'category_id': data.category_id,
                    'type': data.type,
                    'notes': data.notes,
                    'tags': data.tags,
                    'source': data.source,
                    'created_at': data.created_at,
                    'account_name': data.account.name if data.account else None,
                    'category_name': data.category.name if data.category else None,
                    'category_color': data.category.color if data.category else None,
                }
                return obj_data
        return data
```

**Ventajas:**
- ✅ Control explícito
- ✅ Fallback a campos originales (migración gradual)

**Desventajas:**
- ⚠️ Requiere modificar cada schema (TransactionResponse, AccountResponse, InvestmentResponse)

### Solución 3: Renombrar Campos en Schemas

```python
# Opción más explícita pero rompe frontend
class TransactionResponse(BaseModel):
    amount_encrypted: float = Field(serialization_alias="amount")
    description_encrypted: str = Field(serialization_alias="description")
```

**NO RECOMENDADO** porque:
- ❌ Requiere cambios en frontend
- ❌ Pierde compatibilidad con código existente

---

## 📊 Campos que SÍ se pueden Eliminar vs. NO

### ✅ SE PUEDEN ELIMINAR (después de migración)

| Tabla | Campo Original | Motivo |
|-------|---------------|--------|
| users | full_name | Solo lectura/escritura |
| users | profile_picture | Solo lectura/escritura |
| accounts | account_number | Solo lectura/escritura |
| accounts | notes | Solo lectura/escritura |

**Plan de eliminación:**
```sql
-- Después de 100% migración
ALTER TABLE users DROP COLUMN full_name;
ALTER TABLE users DROP COLUMN profile_picture;
ALTER TABLE accounts DROP COLUMN account_number;
ALTER TABLE accounts DROP COLUMN notes;
```

### ❌ SE DEBEN MANTENER (uso operacional)

| Tabla | Campo Original | Motivo | Uso |
|-------|----------------|--------|-----|
| accounts | balance | Cálculos | `SUM(balance)`, índices |
| transactions | amount | Agregaciones SQL | `WHERE amount > 100`, `SUM(amount)` |
| transactions | description | Búsquedas | `WHERE description LIKE '%Amazon%'` |
| investments | symbol | API externa | Consultas de cotizaciones |
| investments | shares | Cálculos | P&L, valoración de portafolio |
| investments | average_price | Cálculos | Rentabilidad |

**Estrategia:**
- Campo original → Índices, filtros, cálculos SQL
- Campo encriptado → Display al usuario, storage seguro
- **Sincronización:** Triggers o application-level sync

---

## 🔍 Ejemplo Práctico Completo

### Lectura (GET /api/transactions)

```python
# 1. Route Handler
@router.get("/", response_model=List[TransactionResponse])
async def get_transactions(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).all()
    return transactions  # FastAPI serializa automáticamente

# 2. Lo que sucede internamente:
transaction = db.query(Transaction).first()

# SQLAlchemy desencripta automáticamente:
print(transaction.amount_encrypted)  # Decimal('150.75') ← YA DESENCRIPTADO
print(transaction.description_encrypted)  # "Compra en Amazon"

# 3. Pydantic serializa:
response = TransactionResponse.model_validate(transaction)
# {
#   "amount": 150.75,
#   "description": "Compra en Amazon"
# }

# 4. JSON al frontend:
# {"amount": 150.75, "description": "Compra en Amazon"}
```

### Escritura (POST /api/transactions)

```python
# 1. Frontend envía:
# POST /api/transactions
# {"amount": -50.00, "description": "Uber Eats"}

# 2. Pydantic valida:
@router.post("/", response_model=TransactionResponse)
async def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db)
):
    # 3. Crear modelo ORM
    transaction = Transaction(
        account_id=payload.account_id,
        amount_encrypted=payload.amount,  # Auto-encripta
        description_encrypted=payload.description,  # Auto-encripta
        type=payload.type
    )
    
    # 4. SQLAlchemy encripta al hacer flush:
    db.add(transaction)
    db.commit()
    # INSERT ... amount_encrypted = 'v1:nonce:ciphertext:tag'
    
    return transaction
```

---

## 🛡️ Seguridad: ¿El Frontend ve datos encriptados?

**NO.** El frontend **NUNCA** recibe datos encriptados.

### ✅ Correcto (valores desencriptados)
```json
{
  "id": "uuid-123",
  "amount": 150.75,
  "description": "Compra en Amazon",
  "balance": 5000.00
}
```

### ❌ Nunca sucede (valores encriptados)
```json
{
  "amount": "v1:A1B2C3:9x8y7z:tag",  ← NUNCA
  "description": "v1:D4E5F6:3a2b1c:tag"
}
```

**La encriptación es completamente TRANSPARENTE para:**
- 🎨 Frontend (React, Vue, etc.)
- 📱 Apps móviles
- 🔌 Integraciones API externas

---

## 🔄 Sincronización de Campos Duplicados

Para campos que se mantienen duplicados (ej: `amount` + `amount_encrypted`), usa triggers o application-level sync:

### Opción A: Trigger PostgreSQL

```sql
CREATE OR REPLACE FUNCTION sync_transaction_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- Sincronizar amount desde amount_encrypted
    IF NEW.amount_encrypted IS NOT NULL THEN
        NEW.amount = (
            SELECT decrypt_to_numeric(NEW.amount_encrypted)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_transaction_on_insert
BEFORE INSERT OR UPDATE ON transactions
FOR EACH ROW
EXECUTE FUNCTION sync_transaction_fields();
```

### Opción B: Application-Level (SQLAlchemy event)

```python
# app/models/transaction.py
from sqlalchemy import event

@event.listens_for(Transaction, 'before_insert')
@event.listens_for(Transaction, 'before_update')
def sync_fields(mapper, connection, target):
    """Sincroniza campos encriptados → originales"""
    if target.amount_encrypted is not None:
        target.amount = target.amount_encrypted
    
    if target.description_encrypted:
        target.description = target.description_encrypted
```

---

## 📝 Checklist de Migración

### Fase 1: Preparación
- [x] Agregar columnas `*_encrypted` en DB
- [x] Crear tipos `EncryptedString`, `EncryptedNumeric`
- [x] Ejecutar script de migración de datos

### Fase 2: Modificar Código
- [ ] Agregar `@property` en modelos ORM
- [ ] Modificar `model_validator` en schemas para usar `*_encrypted`
- [ ] Actualizar services para escribir en `*_encrypted`

### Fase 3: Testing
- [ ] Probar GET /api/transactions (lectura)
- [ ] Probar POST /api/transactions (escritura)
- [ ] Verificar que frontend recibe datos en claro
- [ ] Verificar encriptación en PostgreSQL

### Fase 4: Limpieza (Opcional)
- [ ] Eliminar columnas sin uso operacional (`full_name`, `account_number`)
- [ ] Mantener columnas para índices/cálculos (`amount`, `balance`)
- [ ] Actualizar documentación

---

## 🔮 Futuro: Búsqueda en Campos Encriptados

**Problema:** No puedes hacer `WHERE description_encrypted LIKE '%Amazon%'` porque está encriptado.

**Soluciones:**

### 1. Mantener campo original solo para búsquedas
```python
# Escribir en ambos
transaction.description = "Amazon"  # Para búsquedas
transaction.description_encrypted = "Amazon"  # Para display seguro
```

### 2. Searchable Encryption (avanzado)
```python
# Hash determinístico para igualdad exacta
description_hash = hashlib.sha256(description.encode()).hexdigest()

# Query:
WHERE description_hash = SHA256('Amazon')
```

### 3. Full-text search separado
- Mantener índice de búsqueda en servicio aparte
- Elasticsearch con tokens anonimizados

---

## 💡 Conclusión

**TL;DR:**
1. ✅ La encriptación es **TRANSPARENTE** gracias a `TypeDecorator`
2. ✅ El frontend recibe JSON con valores **DESENCRIPTADOS**
3. ✅ Se pueden eliminar campos como `full_name`, `account_number`
4. ❌ NO eliminar campos usados en índices/cálculos (`amount`, `balance`)
5. 🔧 Usa `@property` o modifica `model_validator` para leer `*_encrypted`

**La encriptación protege datos en reposo (PostgreSQL) sin complicar la aplicación.**
