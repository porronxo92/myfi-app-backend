# 🔐 Guía de Encriptación AES-256-GCM

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Conceptos Fundamentales](#conceptos-fundamentales)
3. [Arquitectura del Sistema](#arquitectura-del-sistema)
4. [Uso de las Utilidades](#uso-de-las-utilidades)
5. [Gestión de Claves](#gestión-de-claves)
6. [Ejemplos Prácticos](#ejemplos-prácticos)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Introducción

Este documento describe la implementación de encriptación AES-256-GCM para proteger datos sensibles en cumplimiento con PSD2. El sistema proporciona:

- **Confidencialidad**: Los datos encriptados son ilegibles sin la clave
- **Integridad**: Cualquier modificación de datos es detectada
- **Autenticación**: Garantiza que los datos provienen de una fuente legítima
- **No repudio**: Los datos encriptados incluyen verificación de autenticidad

---

## 📚 Conceptos Fundamentales

### ¿Qué es AES-256-GCM?

**AES (Advanced Encryption Standard)**
- Algoritmo de cifrado simétrico estándar de la industria
- **256 bits**: Tamaño de la clave (extremadamente seguro)
- Aprobado por NIST, NSA, y gobiernos mundiales

**GCM (Galois/Counter Mode)**
- Modo de operación para cifrado autenticado
- Proporciona **confidencialidad + integridad** en una sola operación
- Genera un **tag de autenticación** para verificar integridad
- Alto rendimiento en hardware moderno

### Componentes de un Dato Encriptado

```
Formato: version:nonce:ciphertext:tag

version   = "1"                    # Versión de clave usada
nonce     = "a1b2c3d4e5f6..."     # Número usado una sola vez (12 bytes)
ciphertext = "x9y8z7w6v5..."      # Datos encriptados
tag       = "m4n3o2p1q0..."       # Tag de autenticación (16 bytes)
```

#### **Nonce (Number Used Once)**
- Valor único para cada operación de encriptación
- 12 bytes (96 bits) generados aleatoriamente
- **CRÍTICO**: Nunca reutilizar con la misma clave
- Generado automáticamente por el sistema

#### **Tag de Autenticación**
- 16 bytes (128 bits)
- Permite verificar que los datos no fueron alterados
- Calculado automáticamente durante la encriptación
- Validado automáticamente durante la desencriptación

---

## 🏗️ Arquitectura del Sistema

### Estructura de Módulos

```
app/utils/
├── key_management.py    # Gestión de claves maestras
├── encryption.py        # Utilidades de encriptación/desencriptación
└── crypto_decorators.py # Decoradores para auto-encriptación (Fase 2)

docs/
├── PSD2_COMPLIANCE.md   # Documentación de cumplimiento
└── ENCRYPTION_GUIDE.md  # Esta guía

tests/
└── test_encryption.py   # Tests unitarios
```

### Jerarquía de Claves

```
┌──────────────────────────────────────────┐
│  ENCRYPTION_MASTER_KEY (AES-256)         │
│  - Almacenada en variables de entorno     │
│  - 32 bytes (256 bits)                    │
│  - Nunca en código fuente                 │
│  - Rotación anual recomendada             │
└────────────────┬─────────────────────────┘
                 │ deriva
                 ▼
┌──────────────────────────────────────────┐
│  Data Encryption Keys (DEKs)              │
│  - Derivadas usando HKDF                  │
│  - Una por tipo de dato (opcional)        │
│  - Rotación automática con versioning     │
└────────────────┬─────────────────────────┘
                 │ encripta
                 ▼
┌──────────────────────────────────────────┐
│  Datos en Base de Datos                   │
│  - account_number_encrypted               │
│  - balance_encrypted                      │
│  - full_name_encrypted, etc.              │
└──────────────────────────────────────────┘
```

### Flujo de Encriptación

```python
┌─────────────────────────────────────────────────────────────┐
│  1. ENCRIPTACIÓN (plaintext → ciphertext)                   │
└─────────────────────────────────────────────────────────────┘

Input: "ES91 2100 0418 4502 0005 1332"  (IBAN)

    ↓ [1] Obtener clave maestra del KeyManager
    
KeyManager.get_current_key()
    → version=1, key=b'32_bytes_random_key...'

    ↓ [2] Generar nonce aleatorio único
    
os.urandom(12)
    → nonce=b'a1b2c3d4e5f6...'

    ↓ [3] Inicializar cipher AES-GCM
    
Cipher(AES(key), GCM(nonce))
    
    ↓ [4] Encriptar datos
    
encryptor.update(plaintext.encode()) + encryptor.finalize()
    → ciphertext=b'x9y8z7w6v5...'
    → tag=b'm4n3o2p1q0...'  (autenticación)

    ↓ [5] Formatear resultado
    
f"{version}:{nonce_b64}:{ciphertext_b64}:{tag_b64}"

Output: "1:YTFiMmMz...:eDl5OHo3...:bTRuM28y..."
        └─┘ └────────┘  └────────┘  └────────┘
      version  nonce    ciphertext    tag

┌─────────────────────────────────────────────────────────────┐
│  2. DESENCRIPTACIÓN (ciphertext → plaintext)                │
└─────────────────────────────────────────────────────────────┘

Input: "1:YTFiMmMz...:eDl5OHo3...:bTRuM28y..."

    ↓ [1] Parsear componentes
    
version, nonce_b64, ciphertext_b64, tag_b64 = input.split(':')

    ↓ [2] Decodificar de base64
    
nonce = base64.b64decode(nonce_b64)
ciphertext = base64.b64decode(ciphertext_b64)
tag = base64.b64decode(tag_b64)

    ↓ [3] Obtener clave correspondiente a la versión
    
KeyManager.get_key_by_version(version=1)
    → key=b'32_bytes_random_key...'

    ↓ [4] Inicializar cipher con nonce y tag
    
Cipher(AES(key), GCM(nonce, tag=tag))

    ↓ [5] Desencriptar y verificar integridad
    
decryptor.update(ciphertext) + decryptor.finalize()
    → plaintext=b'ES91 2100 0418 4502 0005 1332'
    → ✅ Tag válido (datos no alterados)

Output: "ES91 2100 0418 4502 0005 1332"
```

---

## 🛠️ Uso de las Utilidades

### 1. Inicialización del Sistema

```python
from app.utils.key_management import KeyManager
from app.utils.encryption import EncryptionService

# Inicializar el gestor de claves (una vez al inicio de la app)
key_manager = KeyManager()

# Crear el servicio de encriptación
encryption_service = EncryptionService(key_manager)
```

### 2. Encriptar Datos

#### Ejemplo Básico

```python
from app.utils.encryption import encrypt_field

# Encriptar un número de cuenta
account_number = "ES91 2100 0418 4502 0005 1332"
encrypted = encrypt_field(account_number)

print(encrypted)
# Output: "1:YTFiMmMz...:eDl5OHo3...:bTRuM28y..."
```

#### Ejemplo con Manejo de Errores

```python
from app.utils.encryption import encrypt_field, EncryptionError

try:
    user_name = "Juan Pérez García"
    encrypted_name = encrypt_field(user_name)
    
    # Guardar en base de datos
    user.full_name_encrypted = encrypted_name
    db.commit()
    
except EncryptionError as e:
    logger.error(f"Error encriptando nombre: {e}")
    # Manejar error apropiadamente
```

#### Encriptar Números (Balances, Importes)

```python
from decimal import Decimal
from app.utils.encryption import encrypt_field

# Convertir a string antes de encriptar
balance = Decimal("1250.75")
encrypted_balance = encrypt_field(str(balance))

# En DB: "1:abc123...:def456...:ghi789..."
```

### 3. Desencriptar Datos

#### Ejemplo Básico

```python
from app.utils.encryption import decrypt_field

# Obtener dato encriptado de la base de datos
encrypted_data = user.full_name_encrypted

# Desencriptar
plaintext = decrypt_field(encrypted_data)

print(plaintext)
# Output: "Juan Pérez García"
```

#### Ejemplo con Validación

```python
from app.utils.encryption import decrypt_field, DecryptionError

try:
    encrypted_account = account.account_number_encrypted
    
    # Desencriptar y validar
    account_number = decrypt_field(encrypted_account)
    
    # Validar formato IBAN
    if not validate_iban(account_number):
        raise ValueError("IBAN inválido después de desencriptar")
    
    return account_number
    
except DecryptionError as e:
    # Datos corruptos o clave incorrecta
    logger.error(f"Error desencriptando cuenta: {e}")
    raise HTTPException(500, "Error accediendo a datos de cuenta")
```

#### Desencriptar y Convertir de Vuelta

```python
from decimal import Decimal
from app.utils.encryption import decrypt_field

# Desencriptar balance
encrypted_balance = account.balance_encrypted
balance_str = decrypt_field(encrypted_balance)

# Convertir de vuelta a Decimal
balance = Decimal(balance_str)

print(f"Balance: €{balance}")
# Output: Balance: €1250.75
```

### 4. Encriptación en Modelos SQLAlchemy (Fase 2)

```python
from sqlalchemy import Column, String, event
from app.utils.encryption import encrypt_field, decrypt_field

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(UUID, primary_key=True)
    
    # Columna encriptada
    account_number_encrypted = Column(String, nullable=True)
    
    # Propiedad virtual para acceso transparente
    @property
    def account_number(self):
        """Desencripta automáticamente al acceder"""
        if self.account_number_encrypted:
            return decrypt_field(self.account_number_encrypted)
        return None
    
    @account_number.setter
    def account_number(self, value):
        """Encripta automáticamente al asignar"""
        if value:
            self.account_number_encrypted = encrypt_field(value)
        else:
            self.account_number_encrypted = None

# Uso transparente
account = Account()
account.account_number = "ES91 2100 0418 4502 0005 1332"  # Auto-encripta
db.add(account)
db.commit()

# Lectura transparente
print(account.account_number)  # Auto-desencripta
# Output: "ES91 2100 0418 4502 0005 1332"
```

### 5. Encriptación en Schemas Pydantic

```python
from pydantic import BaseModel, validator
from app.utils.encryption import encrypt_field, decrypt_field

class AccountResponse(BaseModel):
    id: UUID
    name: str
    account_number: str  # Se devuelve desencriptado
    balance: Decimal
    
    @classmethod
    def from_orm_with_decryption(cls, orm_obj):
        """Constructor que desencripta automáticamente"""
        return cls(
            id=orm_obj.id,
            name=orm_obj.name,
            account_number=decrypt_field(orm_obj.account_number_encrypted),
            balance=Decimal(decrypt_field(orm_obj.balance_encrypted))
        )

# Uso en endpoint
@router.get("/accounts/{account_id}")
def get_account(account_id: UUID, db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(id=account_id).first()
    return AccountResponse.from_orm_with_decryption(account)
```

---

## 🔑 Gestión de Claves

### Configuración Inicial

#### 1. Generar Master Key

```bash
# Generar clave de 32 bytes (256 bits) en base64
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Output: kP8vX2mN9qR4tY6uZ1wA3bC5dE7fG9hJ0kL2mN4oP6qR8sT0u==
```

#### 2. Configurar en .env

```bash
# .env
ENCRYPTION_MASTER_KEY=kP8vX2mN9qR4tY6uZ1wA3bC5dE7fG9hJ0kL2mN4oP6qR8sT0u==
ENCRYPTION_KEY_VERSION=1
```

#### 3. Validar Configuración

```python
from app.utils.key_management import KeyManager

# Al iniciar la app
key_manager = KeyManager()
print(f"✅ Sistema de encriptación inicializado")
print(f"📌 Versión de clave activa: {key_manager.current_version}")
```

### Rotación de Claves

#### ¿Cuándo rotar?

- **Anualmente**: Rotación preventiva de rutina
- **Compromiso**: Si hay sospecha de exposición de clave
- **Cambio de algoritmo**: Migración a nuevo estándar
- **Cambio de personal**: Empleados con acceso a claves

#### Proceso de Rotación

```python
# scripts/rotate_encryption_key.py

from app.utils.key_management import KeyManager
from app.utils.encryption import EncryptionService
from app.database import SessionLocal
from app.models import Account, User, Transaction
import os, base64

def rotate_keys():
    """
    Rota la clave maestra y re-encripta todos los datos
    """
    db = SessionLocal()
    
    try:
        # 1. Generar nueva clave
        new_key = base64.b64encode(os.urandom(32)).decode()
        new_version = 2  # Incrementar versión
        
        print(f"🔑 Nueva clave generada (v{new_version})")
        
        # 2. Configurar nueva clave en KeyManager
        key_manager = KeyManager()
        key_manager.add_key_version(new_version, new_key)
        
        # 3. Re-encriptar datos de usuarios
        users = db.query(User).all()
        for user in users:
            if user.full_name_encrypted:
                # Desencriptar con clave vieja
                plaintext = decrypt_field(user.full_name_encrypted)
                # Re-encriptar con clave nueva
                user.full_name_encrypted = encrypt_field(plaintext)
        
        # 4. Re-encriptar cuentas
        accounts = db.query(Account).all()
        for account in accounts:
            if account.account_number_encrypted:
                plaintext = decrypt_field(account.account_number_encrypted)
                account.account_number_encrypted = encrypt_field(plaintext)
        
        # 5. Commit cambios
        db.commit()
        print(f"✅ Rotación completada. {len(users)} usuarios, {len(accounts)} cuentas")
        
        # 6. Actualizar .env con nueva clave
        print(f"\n⚠️  ACTUALIZAR .env:")
        print(f"ENCRYPTION_MASTER_KEY={new_key}")
        print(f"ENCRYPTION_KEY_VERSION={new_version}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error en rotación: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    rotate_keys()
```

#### Ejecutar Rotación

```bash
# Backup de base de datos ANTES de rotar
pg_dump app_finance > backup_pre_rotation.sql

# Ejecutar rotación
python scripts/rotate_encryption_key.py

# Actualizar .env con nueva clave
# Reiniciar servicios
```

### Backup de Claves

#### Ubicaciones Recomendadas

1. **Backup Primario**: Almacenamiento seguro offline (USB encriptado)
2. **Backup Secundario**: Sistema de gestión de secretos (AWS KMS, Azure Key Vault)
3. **Backup de Emergencia**: Sobre físico sellado en caja fuerte

#### Formato de Backup

```json
{
  "version": 1,
  "created_at": "2026-02-01T10:00:00Z",
  "keys": {
    "1": {
      "key": "kP8vX2mN9qR4tY6uZ1wA3bC5dE7fG9hJ0kL2mN4oP6qR8sT0u==",
      "created_at": "2026-01-01T00:00:00Z",
      "algorithm": "AES-256-GCM"
    },
    "2": {
      "key": "xQ9wY3nO0rS5uZ7vA2cD4eF6gH8iJ1kL3mN5oP7qR9sT1u==",
      "created_at": "2026-02-01T00:00:00Z",
      "algorithm": "AES-256-GCM"
    }
  }
}
```

⚠️ **IMPORTANTE**: Este archivo debe estar **encriptado con contraseña fuerte**

```bash
# Encriptar backup con GPG
gpg --symmetric --cipher-algo AES256 keys_backup.json

# Desencriptar cuando sea necesario
gpg --decrypt keys_backup.json.gpg > keys_backup.json
```

---

## 💡 Ejemplos Prácticos

### Caso 1: Crear Usuario con Datos Encriptados

```python
from app.models import User
from app.utils.encryption import encrypt_field
from app.services.user_service import UserService

def create_user_encrypted(db: Session, email: str, password: str, full_name: str):
    """
    Crea usuario con nombre encriptado
    """
    # Email se puede dejar sin encriptar si se usa para login
    # Contraseña va con bcrypt (hash, no encriptación)
    password_hash = UserService._hash_password(password)
    
    # Nombre completo DEBE estar encriptado (PSD2)
    full_name_encrypted = encrypt_field(full_name)
    
    user = User(
        email=email,
        password_hash=password_hash,
        full_name_encrypted=full_name_encrypted
    )
    
    db.add(user)
    db.commit()
    return user

# Uso
user = create_user_encrypted(
    db,
    email="juan@example.com",
    password="SecurePass123!",
    full_name="Juan Pérez García"
)
```

### Caso 2: Crear Cuenta Bancaria

```python
from app.models import Account
from app.utils.encryption import encrypt_field
from decimal import Decimal

def create_account_encrypted(db: Session, user_id: UUID, name: str, 
                             account_number: str, balance: Decimal):
    """
    Crea cuenta con datos bancarios encriptados
    """
    account = Account(
        user_id=user_id,
        name=name,  # Nombre descriptivo puede quedar sin encriptar
        type="checking",
        currency="EUR",
        # Datos sensibles encriptados
        account_number_encrypted=encrypt_field(account_number),
        balance_encrypted=encrypt_field(str(balance)),
        bank_name_encrypted=encrypt_field("Bankinter")
    )
    
    db.add(account)
    db.commit()
    return account

# Uso
account = create_account_encrypted(
    db,
    user_id=user.id,
    name="Cuenta Principal",
    account_number="ES91 2100 0418 4502 0005 1332",
    balance=Decimal("1500.50")
)
```

### Caso 3: Consultar Transacciones

```python
from app.models import Transaction
from app.utils.encryption import decrypt_field

def get_transactions_decrypted(db: Session, account_id: UUID, limit: int = 50):
    """
    Obtiene transacciones desencriptadas
    """
    transactions = db.query(Transaction)\
        .filter_by(account_id=account_id)\
        .order_by(Transaction.date.desc())\
        .limit(limit)\
        .all()
    
    # Desencriptar datos
    results = []
    for tx in transactions:
        results.append({
            "id": tx.id,
            "date": tx.date,
            "amount": Decimal(decrypt_field(tx.amount_encrypted)),
            "description": decrypt_field(tx.description_encrypted),
            "type": tx.type
        })
    
    return results
```

### Caso 4: Endpoint API con Encriptación

```python
from fastapi import APIRouter, Depends
from app.utils.encryption import decrypt_field
from app.schemas.account import AccountResponse

router = APIRouter()

@router.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint que devuelve cuenta con datos desencriptados
    """
    account = db.query(Account)\
        .filter_by(id=account_id, user_id=current_user.id)\
        .first()
    
    if not account:
        raise HTTPException(404, "Cuenta no encontrada")
    
    # Desencriptar para respuesta
    return AccountResponse(
        id=account.id,
        name=account.name,
        type=account.type,
        account_number=decrypt_field(account.account_number_encrypted),
        balance=Decimal(decrypt_field(account.balance_encrypted)),
        bank_name=decrypt_field(account.bank_name_encrypted),
        created_at=account.created_at
    )
```

---

## ✅ Best Practices

### 1. Nunca Almacenar Claves en Código

❌ **INCORRECTO**:
```python
# ¡NUNCA HACER ESTO!
ENCRYPTION_KEY = "kP8vX2mN9qR4tY6uZ1wA3bC5dE7fG9hJ0kL2mN4oP6qR8sT0u=="
```

✅ **CORRECTO**:
```python
import os
ENCRYPTION_KEY = os.getenv("ENCRYPTION_MASTER_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_MASTER_KEY no configurada")
```

### 2. Validar Integridad Siempre

```python
from app.utils.encryption import decrypt_field, DecryptionError

try:
    data = decrypt_field(encrypted_data)
except DecryptionError as e:
    # Datos corruptos o clave incorrecta
    logger.error(f"Fallo de integridad: {e}")
    # NO ignorar este error - datos comprometidos
    raise
```

### 3. Encriptar ANTES de Almacenar

```python
# ✅ Correcto: Encriptar antes de commit
account.account_number_encrypted = encrypt_field(iban)
db.add(account)
db.commit()

# ❌ Incorrecto: Almacenar plaintext aunque sea temporalmente
account.account_number = iban  # ¡Datos expuestos!
db.add(account)
account.account_number_encrypted = encrypt_field(iban)
db.commit()
```

### 4. Limpiar Datos en Memoria

```python
import gc

def process_sensitive_data(encrypted_data: str):
    # Desencriptar
    plaintext = decrypt_field(encrypted_data)
    
    try:
        # Procesar datos
        result = do_something(plaintext)
        return result
    finally:
        # Limpiar plaintext de memoria
        del plaintext
        gc.collect()
```

### 5. Logs Seguros

❌ **INCORRECTO**:
```python
logger.info(f"Creando cuenta {account_number}")  # ¡Expone IBAN en logs!
```

✅ **CORRECTO**:
```python
# Enmascarar en logs
masked = f"***{account_number[-4:]}" if account_number else "N/A"
logger.info(f"Creando cuenta terminada en {masked}")
```

### 6. Manejo de Errores Apropiado

```python
from app.utils.encryption import EncryptionError, DecryptionError

try:
    encrypted = encrypt_field(data)
except EncryptionError:
    # Error de sistema - algo mal con el KeyManager
    logger.critical("Sistema de encriptación no disponible")
    raise HTTPException(503, "Servicio temporalmente no disponible")

try:
    plaintext = decrypt_field(encrypted)
except DecryptionError:
    # Datos corruptos o clave incorrecta
    logger.error("Datos corruptos o clave incorrecta")
    raise HTTPException(500, "Error accediendo a datos")
```

---

## 🔧 Troubleshooting

### Error: "Invalid tag" al Desencriptar

**Causa**: Datos fueron modificados o clave incorrecta

**Solución**:
1. Verificar que `ENCRYPTION_MASTER_KEY` es la correcta
2. Verificar versión de clave en datos vs. KeyManager
3. Revisar logs de auditoría para cambios no autorizados

```python
# Verificar formato de datos encriptados
parts = encrypted_data.split(':')
if len(parts) != 4:
    logger.error(f"Formato inválido: esperado 4 partes, recibido {len(parts)}")
```

### Error: "Master key not configured"

**Causa**: Variable de entorno no configurada

**Solución**:
```bash
# Verificar que existe en .env
cat .env | grep ENCRYPTION_MASTER_KEY

# Si no existe, generarla
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Añadir a .env
echo "ENCRYPTION_MASTER_KEY=<clave_generada>" >> .env
```

### Error: Performance Degradation

**Síntomas**: Consultas lentas después de implementar encriptación

**Diagnóstico**:
```python
import time

start = time.time()
plaintext = decrypt_field(encrypted_data)
elapsed = time.time() - start

logger.info(f"Desencriptación tomó {elapsed*1000:.2f}ms")
```

**Soluciones**:
1. **Caché a nivel de sesión**:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def decrypt_and_cache(encrypted_data: str) -> str:
    return decrypt_field(encrypted_data)
```

2. **Desencriptar solo cuando sea necesario**:
```python
# ❌ Desencripta todo siempre
accounts = [decrypt_all(a) for a in db.query(Account).all()]

# ✅ Desencripta solo lo que se muestra
accounts = db.query(Account).all()
# Solo desencriptar al renderizar
```

3. **Batch operations**:
```python
# Procesar en lotes
batch_size = 100
for i in range(0, len(data), batch_size):
    batch = data[i:i+batch_size]
    process_batch(batch)
```

### Error: "Nonce reused"

**Causa**: CRÍTICO - Violación de seguridad

**Detección**:
```python
# Verificar unicidad de nonces en DB (desarrollo)
SELECT nonce, COUNT(*) 
FROM (
    SELECT split_part(account_number_encrypted, ':', 2) as nonce 
    FROM accounts
) AS nonces
GROUP BY nonce
HAVING COUNT(*) > 1;
```

**Solución**: Esto NO debe ocurrir. Si ocurre:
1. Re-encriptar TODOS los datos inmediatamente
2. Investigar el bug en generación de nonces
3. Auditar logs para determinar exposición

---

## 📚 Referencias

### Documentación Oficial

- **cryptography library**: https://cryptography.io/
- **NIST SP 800-38D (GCM)**: https://csrc.nist.gov/publications/detail/sp/800-38d/final
- **PSD2 Guidelines**: https://www.eba.europa.eu/regulation-and-policy/payment-services-and-electronic-money/guidelines-on-security-measures-for-operational-and-security-risks-under-psd2

### Herramientas Útiles

- **Generador de claves**: `python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"`
- **Verificar instalación**: `python -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print('✅ OK')"`
- **Test básico**:
```python
from app.utils.encryption import encrypt_field, decrypt_field
encrypted = encrypt_field("test")
decrypted = decrypt_field(encrypted)
assert decrypted == "test"
print("✅ Sistema de encriptación funcionando")
```

---

**Última actualización**: Febrero 1, 2026  
**Versión**: 1.0  
**Mantenedor**: Equipo de Seguridad
