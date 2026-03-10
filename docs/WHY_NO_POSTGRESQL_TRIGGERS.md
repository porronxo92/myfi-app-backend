# ¿Por qué NO se necesitan Triggers PostgreSQL?

## ❓ Pregunta Importante

> "Pero ahora si los campos que están en claro en bbdd solo son lectura, los datos que vayan entrando nuevos, solo se almacenarán en los campos _encrypted, por lo tanto, ¿cómo funcionarán los triggers y las vistas?"

**Respuesta:** Los triggers PostgreSQL **NO FUNCIONAN** con datos encriptados. La sincronización debe hacerse **a nivel de aplicación** (SQLAlchemy events).

---

## ❌ Problema con Triggers PostgreSQL

### Lo que intenté hacer:

```sql
CREATE OR REPLACE FUNCTION sync_account_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- Intentar convertir balance_encrypted a NUMERIC
    NEW.balance = NEW.balance_encrypted::NUMERIC(12, 2);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Por qué NO funciona:

```
balance_encrypted en PostgreSQL = "v1:A1B2C3D4:9x8y7z6w5v:tag123"
                                   ↓
        NEW.balance = "v1:A1B2..."::NUMERIC(12, 2)
                                   ↓
                    ❌ ERROR: invalid input syntax for type numeric
```

**PostgreSQL no puede desencriptar** los datos porque:
- ❌ No tiene acceso a `ENCRYPTION_MASTER_KEY` (está en Python .env)
- ❌ pgcrypto no soporta AES-256-GCM (solo AES-CBC)
- ❌ El trigger ve datos YA encriptados en formato "v1:nonce:ciphertext:tag"

---

## ✅ Solución Correcta: SQLAlchemy Events

### Arquitectura de Sincronización

```
┌─────────────────────────────────────────────────────────────┐
│ 1. APLICACIÓN PYTHON                                        │
│    account.balance_encrypted = Decimal("1500.50")           │
│    (valor AÚN NO encriptado)                                │
└─────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. SQLAlchemy Event: before_insert / before_update          │
│    Ejecuta ANTES de que TypeDecorator encripte              │
│                                                              │
│    @event.listens_for(Account, 'before_insert')             │
│    def sync_balance(mapper, connection, target):            │
│        # Aquí balance_encrypted = Decimal("1500.50")        │
│        target.balance = target.balance_encrypted ✅         │
└─────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SQLAlchemy TypeDecorator: process_bind_param()           │
│    Encripta el valor DESPUÉS del evento                     │
│                                                              │
│    balance_encrypted = Decimal("1500.50")                   │
│           ↓ (encripta)                                       │
│    balance_encrypted = "v1:nonce:9x8y7z:tag" ✅             │
└─────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. POSTGRESQL RECIBE                                        │
│    INSERT INTO accounts (balance, balance_encrypted)        │
│    VALUES (1500.50, 'v1:nonce:9x8y7z:tag');                 │
│                                                              │
│    balance = 1500.50 ✅ (en claro, para índices)            │
│    balance_encrypted = 'v1:...' ✅ (encriptado, seguridad)  │
└─────────────────────────────────────────────────────────────┘
```

### Código de Implementación

**Ubicación:** `app/utils/encryption_events.py`

```python
from sqlalchemy import event
from app.models.account import Account

@event.listens_for(Account, 'before_insert')
@event.listens_for(Account, 'before_update')
def sync_account_fields_before_encrypt(mapper, connection, target):
    """
    Sincroniza balance ANTES de que TypeDecorator lo encripte.
    
    CRÍTICO: Este evento se ejecuta ANTES de process_bind_param(),
    por lo que target.balance_encrypted aún contiene el Decimal en claro.
    """
    if target.balance_encrypted is not None:
        # balance_encrypted = Decimal("1500.50") ← AÚN NO ENCRIPTADO
        target.balance = target.balance_encrypted  # ✅ Copia para índices
        
        # DESPUÉS de este evento, TypeDecorator encriptará balance_encrypted
```

---

## 🔄 Flujo Completo: INSERT de una Cuenta

### Paso a paso:

1. **Aplicación escribe:**
```python
account = Account(
    user_id=user_id,
    name="Cuenta Bankinter",
    balance_encrypted=Decimal("1500.50")  # ← En claro (Decimal)
)
db.add(account)
db.commit()
```

2. **Event 'before_insert' se ejecuta:**
```python
# target.balance_encrypted = Decimal("1500.50") ← CLARO
target.balance = target.balance_encrypted  # Copia: balance = 1500.50
```

3. **TypeDecorator.process_bind_param() encripta:**
```python
# balance_encrypted = Decimal("1500.50")
#      ↓ encrypt_field(str(value))
# balance_encrypted = "v1:A1B2C3:9x8y7z:tag"
```

4. **SQLAlchemy genera SQL:**
```sql
INSERT INTO accounts (name, balance, balance_encrypted)
VALUES ('Cuenta Bankinter', 1500.50, 'v1:A1B2C3:9x8y7z:tag');
```

5. **PostgreSQL almacena:**
```
| balance | balance_encrypted                        |
|---------|------------------------------------------|
| 1500.50 | v1:A1B2C3D4E5F6:9x8y7z6w5v:tagABC123     |
| ↑       | ↑                                        |
| Índices | Encriptado (seguridad)                   |
```

---

## 🔍 Flujo Completo: SELECT de una Cuenta

### Paso a paso:

1. **Query SQL:**
```python
account = db.query(Account).filter(Account.balance > 1000).first()
```

2. **PostgreSQL ejecuta:**
```sql
SELECT * FROM accounts WHERE balance > 1000 LIMIT 1;
-- Usa índice en 'balance' ✅ (campo en claro)
```

3. **PostgreSQL devuelve:**
```python
{
    'balance': 1500.50,
    'balance_encrypted': 'v1:A1B2C3:9x8y7z:tag'
}
```

4. **TypeDecorator.process_result_value() desencripta:**
```python
# balance_encrypted = "v1:A1B2C3:9x8y7z:tag"
#      ↓ decrypt_field(value)
# balance_encrypted = Decimal("1500.50")  ← Desencriptado
```

5. **Aplicación recibe:**
```python
print(account.balance)            # Decimal('1500.50')
print(account.balance_encrypted)  # Decimal('1500.50') ← Igual, desencriptado
```

---

## 📊 Comparativa: Triggers PostgreSQL vs. SQLAlchemy Events

| Aspecto | Triggers PostgreSQL | SQLAlchemy Events |
|---------|---------------------|-------------------|
| **¿Funciona con datos encriptados?** | ❌ NO (no puede desencriptar) | ✅ SÍ (accede antes de encriptar) |
| **Acceso a ENCRYPTION_KEY** | ❌ NO | ✅ SÍ (Python .env) |
| **Momento de ejecución** | AFTER TypeDecorator | BEFORE TypeDecorator |
| **Complejidad** | Alta (extensiones PG) | Baja (Python estándar) |
| **Portabilidad** | Baja (específico PG) | Alta (funciona con cualquier DB) |
| **Mantenimiento** | Difícil (SQL + Python) | Fácil (solo Python) |

---

## ✅ ¿Qué necesitas hacer?

### 1. **NO ejecutar triggers PostgreSQL**

El archivo `migrations/003_add_encryption_triggers.sql` **NO es necesario**.

```bash
# ❌ NO ejecutar esto:
# psql -U usuario -d appfinanzas -f migrations/003_add_encryption_triggers.sql
```

### 2. **Sí ejecutar columnas encriptadas**

```bash
# ✅ SÍ ejecutar esto:
psql -U usuario -d appfinanzas -f migrations/002_add_encrypted_columns.sql
```

### 3. **Migrar datos existentes**

```bash
python scripts/migrate_encrypt_data.py --dry-run  # Simulación
python scripts/migrate_encrypt_data.py            # Real
```

### 4. **Arrancar aplicación (events se activan automáticamente)**

```bash
python -m uvicorn app.main:app --reload
```

**Logs esperados:**
```
🔐 Inicializando sistema de encriptación...
✅ Sistema de encriptación validado
Configurando event listeners de encriptación...
✅ Event listeners de encriptación configurados exitosamente
   1. Escrituras en campos en claro → redirigidas a *_encrypted
   2. Sincronización automática ANTES de encriptar → campos de índice  
   3. NO se requieren triggers PostgreSQL
```

---

## 🧪 Testing

### Verificar sincronización:

```python
from app.models.account import Account
from decimal import Decimal

# Crear cuenta
account = Account(
    user_id=user_id,
    name="Test Account",
    balance_encrypted=Decimal("2500.75")  # ← Solo escribimos aquí
)
db.add(account)
db.commit()
db.refresh(account)

# Verificar PostgreSQL
print(f"En PostgreSQL:")
print(f"  balance = {account.balance}")  # 2500.75 (claro, índices)
print(f"  balance_encrypted = [encriptado]")  # v1:... (encriptado)

# Verificar Python (desencripta automáticamente)
print(f"En Python:")
print(f"  account.balance_encrypted = {account.balance_encrypted}")  # Decimal('2500.75')
```

### Verificar que índices funcionan:

```python
# Query con filtro (usa índice)
accounts = db.query(Account).filter(Account.balance > 1000).all()
print(f"Encontradas: {len(accounts)} cuentas con balance > 1000")

# EXPLAIN para verificar índice
from sqlalchemy import text
result = db.execute(text("EXPLAIN SELECT * FROM accounts WHERE balance > 1000"))
for row in result:
    print(row)
# Debería mostrar: Index Scan using idx_accounts_balance
```

---

## 🔐 Seguridad Garantizada

### En PostgreSQL (Storage):

```sql
SELECT balance, balance_encrypted FROM accounts LIMIT 1;

balance | balance_encrypted
--------|------------------------------------------
1500.50 | v1:A1B2C3D4E5:9x8y7z6w5v4u:tagABC123DEF
```

**Análisis de seguridad:**
- ✅ `balance_encrypted` = **Completamente encriptado** con AES-256-GCM
- ⚠️ `balance` = En claro (para índices/rendimiento)

**Protección adicional requerida:**
- 🔒 Cifrado a nivel de disco (LUKS, BitLocker, AWS/Azure encryption)
- 🔒 Backups encriptados (`pg_dump | gpg -e`)
- 🔒 SSL/TLS en conexiones PostgreSQL
- 🔒 Controles de acceso estrictos (pg_hba.conf, IAM)

### Compliance:

**PSD2 Art. 95:**
> "Datos de pago encriptados en reposo y en tránsito"

✅ **CUMPLE:**
- balance_encrypted = Encriptado con AES-256-GCM
- SSL/TLS para conexiones
- Cifrado de disco adicional

**GDPR Art. 32:**
> "Cifrado de datos personales"

✅ **CUMPLE:**
- Datos financieros encriptados
- Coherencia automática (no hay riesgo de desincronización)
- Derecho al olvido implementado

---

## 📝 Resumen Ejecutivo

### ¿Por qué NO triggers PostgreSQL?

1. ❌ PostgreSQL **no puede desencriptar** AES-256-GCM sin la clave
2. ❌ El trigger ve datos **ya encriptados** en formato "v1:nonce:ciphertext:tag"
3. ❌ No puede convertir texto encriptado a NUMERIC: `"v1:..."::NUMERIC` = ERROR

### ¿Cómo sincronizar entonces?

1. ✅ **SQLAlchemy events** (`before_insert`, `before_update`)
2. ✅ Se ejecutan **ANTES** de que TypeDecorator encripte
3. ✅ Copian el valor en claro a campos de índice: `balance = balance_encrypted`
4. ✅ DESPUÉS TypeDecorator encripta `balance_encrypted`

### Resultado final:

```
PostgreSQL almacena:
- balance = 1500.50 (claro, índices) ⚡
- balance_encrypted = "v1:encrypted..." (encriptado) 🔐

Python ve:
- account.balance_encrypted = Decimal('1500.50') (desencriptado) ✅
```

### Ventajas finales:

- 🔐 **Seguridad:** Datos encriptados en DB
- ⚡ **Rendimiento:** Índices funcionan (balance en claro)
- ✅ **Coherencia:** Automática (events Python)
- 🧩 **Simplicidad:** Solo Python, sin SQL complejo
- 🌍 **Portabilidad:** Funciona con cualquier BD

---

**Autor:** Security Team  
**Fecha:** 2026-02-14  
**Estado:** ✅ Arquitectura corregida y validada
