# 🚀 Inicio Rápido - Sistema de Encriptación PSD2

## ⚡ Configuración en 5 Minutos

### Paso 1: Instalar Dependencias

```bash
pip install cryptography==41.0.7
```

### Paso 2: Generar Clave de Encriptación

Ejecuta este comando para generar una clave segura:

```bash
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

**Ejemplo de salida**:
```
/hW509ZvtiUBYI6vfv3QP4qc5Vh5JlSa1BvEmALOnQE=
```

⚠️ **IMPORTANTE**: Esta clave es única y debe ser guardada de forma segura.

### Paso 3: Configurar .env

Crea o actualiza tu archivo `.env` con la clave generada:

```bash
# Encriptación PSD2
ENCRYPTION_MASTER_KEY=/hW509ZvtiUBYI6vfv3QP4qc5Vh5JlSa1BvEmALOnQE=
ENCRYPTION_KEY_VERSION=1
```

### Paso 4: Verificar Instalación

```bash
python -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print('✅ OK')"
```

### Paso 5: Test Básico

```python
# Crear archivo test_encryption_quick.py
from app.utils.encryption import encrypt_field, decrypt_field

# Test rápido
iban = "ES91 2100 0418 4502 0005 1332"
encrypted = encrypt_field(iban)
decrypted = decrypt_field(encrypted)

assert decrypted == iban
print("✅ Sistema de encriptación funcionando correctamente")
print(f"Original: {iban}")
print(f"Encriptado: {encrypted}")
print(f"Desencriptado: {decrypted}")
```

Ejecutar:
```bash
python test_encryption_quick.py
```

---

## 📖 Uso Básico

### Encriptar Datos

```python
from app.utils.encryption import encrypt_field

# Datos sensibles a encriptar
account_number = "ES91 2100 0418 4502 0005 1332"
balance = "1500.75"
user_name = "Juan Pérez García"

# Encriptar
encrypted_account = encrypt_field(account_number)
encrypted_balance = encrypt_field(balance)
encrypted_name = encrypt_field(user_name)

# Guardar en base de datos
account.account_number_encrypted = encrypted_account
account.balance_encrypted = encrypted_balance
user.full_name_encrypted = encrypted_name
db.commit()
```

### Desencriptar Datos

```python
from app.utils.encryption import decrypt_field
from decimal import Decimal

# Obtener de base de datos
account = db.query(Account).first()

# Desencriptar
account_number = decrypt_field(account.account_number_encrypted)
balance = Decimal(decrypt_field(account.balance_encrypted))
user_name = decrypt_field(user.full_name_encrypted)

print(f"Cuenta: {account_number}")
print(f"Saldo: €{balance}")
print(f"Titular: {user_name}")
```

### Campos Opcionales

```python
from app.utils.encryption import encrypt_optional_field, decrypt_optional_field

# Campo que puede ser None
bank_name = "Bankinter"  # o None

# Encriptar (maneja None automáticamente)
encrypted = encrypt_optional_field(bank_name)

# Desencriptar
plaintext = decrypt_optional_field(encrypted)
```

---

## ✅ Checklist de Validación

Asegúrate de que todo está configurado correctamente:

- [ ] Python 3.9+ instalado
- [ ] Librería `cryptography==41.0.7` instalada
- [ ] Archivo `.env` creado
- [ ] `ENCRYPTION_MASTER_KEY` configurada en `.env`
- [ ] `ENCRYPTION_KEY_VERSION=1` en `.env`
- [ ] Test básico ejecutado exitosamente
- [ ] Backup de la clave maestra guardado de forma segura

---

## 🔒 Seguridad - IMPORTANTE

### ⚠️ Hacer ANTES de ir a producción:

1. **Backup de Clave Maestra**
   ```bash
   # Crear backup encriptado
   gpg --symmetric --cipher-algo AES256 .env
   # Guardar .env.gpg en ubicación segura OFFLINE
   ```

2. **Cambiar Claves de Desarrollo**
   - Generar nuevas claves para producción
   - NUNCA usar las mismas claves en desarrollo y producción

3. **Variables de Entorno Seguras**
   - Usar gestor de secretos (AWS Secrets Manager, Azure Key Vault)
   - NUNCA commitear `.env` a git
   - Verificar que `.env` está en `.gitignore`

4. **HTTPS Obligatorio**
   - Configurar certificados TLS 1.3
   - Forzar redirección HTTP → HTTPS

---

## 📚 Documentación Completa

Para más detalles, consulta:

- **[PSD2 Compliance](./PSD2_COMPLIANCE.md)** - Requisitos normativos y cumplimiento
- **[Encryption Guide](./ENCRYPTION_GUIDE.md)** - Guía técnica completa
- **[Fase 1 Completada](./FASE_1_COMPLETADA.md)** - Resumen de implementación

---

## 🆘 Solución de Problemas

### Error: "ENCRYPTION_MASTER_KEY no configurada"

**Solución**: Añadir la clave al archivo `.env`

```bash
# Generar nueva clave
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Añadir a .env
echo "ENCRYPTION_MASTER_KEY=<clave_generada>" >> .env
```

### Error: "cryptography no instalada"

**Solución**: Instalar la librería

```bash
pip install cryptography==41.0.7
```

### Error: "Invalid tag" al desencriptar

**Causa**: Datos corruptos o clave incorrecta

**Solución**:
1. Verificar que `ENCRYPTION_MASTER_KEY` es la correcta
2. Verificar que los datos no han sido modificados
3. Revisar logs de auditoría

---

## 💡 Ejemplos Prácticos

### Ejemplo 1: Crear Usuario con Datos Encriptados

```python
from app.models import User
from app.utils.encryption import encrypt_field
from app.services.user_service import UserService

def create_secure_user(db, email, password, full_name):
    # Contraseña con bcrypt (hash, no encriptación)
    password_hash = UserService._hash_password(password)
    
    # Nombre completo encriptado
    full_name_encrypted = encrypt_field(full_name)
    
    user = User(
        email=email,
        password_hash=password_hash,
        full_name_encrypted=full_name_encrypted
    )
    
    db.add(user)
    db.commit()
    return user
```

### Ejemplo 2: Endpoint API con Desencriptación

```python
from fastapi import APIRouter
from app.utils.encryption import decrypt_field

@router.get("/accounts/{account_id}")
def get_account(account_id: UUID, db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(id=account_id).first()
    
    return {
        "id": account.id,
        "name": account.name,
        "account_number": decrypt_field(account.account_number_encrypted),
        "balance": float(decrypt_field(account.balance_encrypted))
    }
```

### Ejemplo 3: Migrar Datos Existentes

```python
from app.utils.encryption import encrypt_field

def migrate_accounts_to_encrypted(db):
    """Migra cuentas existentes a formato encriptado"""
    accounts = db.query(Account).all()
    
    for account in accounts:
        # Encriptar datos si aún no están encriptados
        if account.account_number and not account.account_number_encrypted:
            account.account_number_encrypted = encrypt_field(account.account_number)
        
        if account.balance and not account.balance_encrypted:
            account.balance_encrypted = encrypt_field(str(account.balance))
    
    db.commit()
    print(f"✅ {len(accounts)} cuentas migradas")
```

---

## 📞 Contacto

Para soporte técnico o dudas:
- **Documentación**: `/docs/`
- **Tests**: `/tests/test_encryption.py`
- **Ejemplos**: Esta guía

---

**Última actualización**: 1 de Febrero de 2026  
**Versión**: 1.0
