# Implementación de Autenticación JWT

## 📋 Resumen de Cambios

Se ha implementado un sistema de autenticación basado en **JSON Web Tokens (JWT)** para reemplazar completamente el sistema anterior de API Key. Esta migración proporciona:

✅ **Autenticación stateless** - Los tokens contienen información del usuario sin necesidad de almacenamiento en servidor  
✅ **Seguridad mejorada** - Tokens firmados con HS256, expiración automática a 30 minutos  
✅ **Aislamiento de datos por usuario** - Cada usuario solo puede acceder a sus propios recursos  
✅ **Control de permisos** - Distinción entre usuarios regulares y administradores  

---

## 🔐 Flujo de Autenticación

```
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│   Cliente   │          │   Backend   │          │  Base Datos │
└──────┬──────┘          └──────┬──────┘          └──────┬──────┘
       │                        │                        │
       │  POST /api/users/login │                        │
       │  {email, password}     │                        │
       ├───────────────────────>│                        │
       │                        │  Verificar credenciales│
       │                        ├───────────────────────>│
       │                        │<───────────────────────┤
       │                        │  Generar JWT Token     │
       │  TokenResponse         │  (sub: user_id)        │
       │  {access_token, ...}   │                        │
       │<───────────────────────┤                        │
       │                        │                        │
       │  GET /api/accounts     │                        │
       │  Authorization: Bearer │                        │
       │  <token>               │                        │
       ├───────────────────────>│                        │
       │                        │  Validar token         │
       │                        │  Extraer user_id       │
       │                        │  Filtrar por user_id   │
       │                        ├───────────────────────>│
       │                        │<───────────────────────┤
       │  Accounts (user only)  │                        │
       │<───────────────────────┤                        │
       │                        │                        │
```

---

## 🛠️ Archivos Modificados

### **1. Nuevos Archivos Creados**

#### `app/utils/jwt.py`
**Propósito:** Generación y validación de tokens JWT

**Funciones principales:**
- `create_access_token(data: dict, expires_delta: timedelta)` - Genera JWT con claim "sub" (user_id) y expiración
- `verify_token(token: str)` - Valida firma y expiración del token, devuelve payload
- `get_user_id_from_token(token: str)` - Extrae user_id del claim "sub"

**Configuración:**
```python
JWT_SECRET_KEY = "your-secret-key-change-in-production-min-32-characters"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

⚠️ **IMPORTANTE:** Cambiar `JWT_SECRET_KEY` en producción por una clave segura de al menos 32 caracteres.

---

### **2. Archivos Modificados**

#### `requirements.txt`
Dependencias añadidas:
```
PyJWT==2.9.0
python-jose[cryptography]==3.3.0
```

**Instalación:**
```bash
pip install PyJWT==2.9.0 python-jose[cryptography]==3.3.0
```

---

#### `app/config.py`
**Cambios:**
- ❌ Eliminado: `API_KEY`, `ENABLE_API_KEY_AUTH`
- ✅ Añadido: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`

---

#### `app/utils/security.py`
**Cambios:**
- ❌ Eliminado: `verify_api_key()` - Dependencia de API Key
- ✅ Añadido: `get_current_user(credentials: HTTPAuthorizationCredentials, db: Session)` 
  - Valida Bearer token
  - Carga usuario desde DB
  - Verifica estado activo (`is_active`)
  - Retorna objeto `User` completo
  
- ✅ Añadido: `get_current_admin_user(current_user: User)`
  - Verifica que el usuario tenga `is_admin=True`
  - Usado en endpoints administrativos
  
- 🔧 Modificado: `check_rate_limit()` - Ahora solo usa IP (eliminada verificación de API Key)

---

#### `app/schemas/user.py`
**Añadido:**
```python
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
```

---

#### `app/routes/users.py`
**Endpoint de Login:**
```python
POST /api/users/login
Request: {"email": "user@example.com", "password": "User123!"}
Response: {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "full_name": "Usuario Normal",
        "is_admin": false,
        ...
    }
}
```

**Protección de endpoints:**
| Endpoint | Autenticación | Autorización |
|----------|--------------|--------------|
| `POST /api/users/login` | ❌ No requerida | - |
| `GET /api/users` | ✅ JWT | 🔒 Solo Admin |
| `GET /api/users/{id}` | ✅ JWT | 🔓 Self o Admin |
| `PUT /api/users/{id}` | ✅ JWT | 🔓 Self o Admin |
| `DELETE /api/users/{id}` | ✅ JWT | 🔒 Solo Admin |
| `POST /api/users/{id}/change-password` | ✅ JWT | 🔓 Solo Self |

---

#### `app/services/account_service.py`
**Todos los métodos actualizados con parámetro `user_id`:**

```python
# Antes
def get_all(db: Session, skip: int, limit: int) -> List[Account]:
    return db.query(Account).offset(skip).limit(limit).all()

# Después
def get_all(db: Session, user_id: UUID, skip: int, limit: int) -> List[Account]:
    return db.query(Account).filter(
        Account.user_id == user_id
    ).offset(skip).limit(limit).all()
```

**Métodos modificados:**
- `get_all(user_id, ...)` - Filtra por `Account.user_id == user_id`
- `get_by_id(account_id, user_id)` - Verifica ownership antes de retornar
- `update(account_id, user_id, ...)` - Verifica ownership antes de actualizar
- `delete(account_id, user_id)` - Verifica ownership antes de eliminar
- `get_total_count(user_id, ...)` - Cuenta solo cuentas del usuario
- `get_total_balance(user_id, ...)` - Suma balance solo del usuario

---

#### `app/routes/accounts.py`
**Cambios en todos los endpoints:**

```python
# Antes
@router.get("")
async def list_accounts(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    accounts = AccountService.get_all(db)
    ...

# Después
@router.get("")
async def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    accounts = AccountService.get_all(db, user_id=current_user.id)
    ...
```

**Endpoints protegidos:**
- `GET /api/accounts` - Lista solo cuentas del usuario
- `GET /api/accounts/{id}` - Verifica ownership
- `POST /api/accounts` - Asigna automáticamente `user_id = current_user.id`
- `PUT /api/accounts/{id}` - Verifica ownership
- `DELETE /api/accounts/{id}` - Verifica ownership
- `GET /api/accounts/stats` - Estadísticas solo del usuario

---

#### `app/services/category_service.py`
**Filtrado por transacciones del usuario:**

Las categorías son **globales** (compartidas entre usuarios), pero cada usuario solo ve las categorías que ha **utilizado en sus transacciones**.

```python
def get_all(db: Session, user_id: UUID, skip: int, limit: int) -> List[Category]:
    return db.query(Category).join(
        Transaction, Transaction.category_id == Category.id
    ).join(
        Account, Transaction.account_id == Account.id
    ).filter(
        Account.user_id == user_id
    ).distinct().offset(skip).limit(limit).all()
```

**Métodos modificados:**
- `get_all(user_id, ...)` - JOIN a Transaction→Account, filtro por `Account.user_id`
- `get_by_id(category_id, user_id)` - Verifica que el usuario haya usado la categoría
- `get_total_count(user_id, ...)` - Cuenta categorías usadas por el usuario
- `_calculate_total_amount(category_id, user_id)` - Suma solo transacciones del usuario

---

#### `app/routes/categories.py`
**Endpoints con JWT:**
- `GET /api/categories` - Categorías usadas por el usuario
- `GET /api/categories/{id}` - Verifica que el usuario la haya usado
- `POST /api/categories` - Crea categoría global (cualquier usuario autenticado)
- `PUT /api/categories/{id}` - Actualiza categoría (cualquier usuario autenticado)
- `DELETE /api/categories/{id}` - Elimina categoría (cualquier usuario autenticado)
- `GET /api/categories/stats/summary` - Resumen de categorías del usuario

---

#### `app/services/transaction_service.py`
**Filtrado por cuentas del usuario:**

```python
def get_all(db: Session, user_id: UUID, skip: int, limit: int, ...) -> List[Transaction]:
    return db.query(Transaction).join(
        Account, Transaction.account_id == Account.id
    ).filter(
        Account.user_id == user_id
    ).offset(skip).limit(limit).all()
```

**Métodos modificados:**
- `get_all(user_id, ...)` - JOIN a Account, filtro por `Account.user_id`
- `get_by_id(transaction_id, user_id)` - Verifica que la transacción pertenece al usuario
- `create(transaction_data, user_id)` - Verifica que `account_id` pertenezca al usuario
- `update(transaction_id, user_id, ...)` - Verifica ownership
- `delete(transaction_id, user_id)` - Verifica ownership
- `get_total_count(user_id, ...)` - Cuenta transacciones del usuario
- `get_summary(user_id, ...)` - Resumen financiero del usuario

---

#### `app/routes/transactions.py`
**Endpoints con JWT:**
- `GET /api/transactions` - Lista transacciones del usuario
- `GET /api/transactions/{id}` - Verifica ownership
- `POST /api/transactions` - Verifica que `account_id` pertenezca al usuario
- `PUT /api/transactions/{id}` - Verifica ownership
- `DELETE /api/transactions/{id}` - Verifica ownership
- `GET /api/transactions/stats/summary` - Resumen del usuario

---

#### `app/main.py`
**Cambios en logs de inicio:**
```python
# Antes
logger.info(f"Autenticación API Key: {'HABILITADA' if settings.ENABLE_API_KEY_AUTH else 'DESHABILITADA'}")

# Después
logger.info(f"Autenticación: JWT (HS256) con tokens de {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES} minutos")
```

---

## 📖 Guía de Uso

### **1. Obtener Token JWT**

**Endpoint:** `POST /api/users/login`

```bash
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "User123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5YjFkZWI0ZC03YmY3LTQ0YTMtOWNmNy1hYzk0YjAyZDdlMjYiLCJleHAiOjE3Mzc1NzI0MDB9.r8zK9mN7kV2hF5dP3wQ1xY6tL0jA8cE4bG9sH2fI1mO",
  "token_type": "bearer",
  "user": {
    "id": "9b1deb4d-7bf7-44a3-9cf7-ac94b02d7e26",
    "email": "user@example.com",
    "full_name": "Usuario Normal",
    "is_admin": false,
    "is_active": true,
    "created_at": "2025-01-15T10:00:00"
  }
}
```

---

### **2. Usar Token en Peticiones**

**Todos los endpoints protegidos requieren el header `Authorization`:**

```bash
curl -X GET http://localhost:8000/api/accounts \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**En JavaScript:**
```javascript
fetch('http://localhost:8000/api/accounts', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
})
```

**En Postman:**
1. Ir a la pestaña **Authorization**
2. Seleccionar **Type:** Bearer Token
3. Pegar el `access_token` en el campo **Token**

---

### **3. Renovar Token**

Los tokens expiran en **30 minutos**. Cuando expiran, el servidor responde:

```json
{
  "detail": "Token ha expirado"
}
```

**Solución:** Volver a hacer login para obtener un nuevo token.

---

## 🔒 Modelo de Seguridad

### **Aislamiento de Datos**

Cada usuario **solo puede acceder a sus propios recursos**:

| Recurso | Filtrado | Método |
|---------|----------|--------|
| **Accounts** | `Account.user_id == current_user.id` | FK directo |
| **Transactions** | `Transaction.account.user_id == current_user.id` | JOIN a Account |
| **Categories** | `Category.transactions.account.user_id == current_user.id` | JOIN a Transaction→Account |

---

### **Permisos de Usuario**

#### **Usuario Regular (`is_admin=false`)**
- ✅ Ver/editar/eliminar sus propias cuentas
- ✅ Ver/editar/eliminar sus propias transacciones
- ✅ Ver categorías que ha utilizado
- ✅ Crear/editar/eliminar categorías (globales)
- ✅ Cambiar su propia contraseña
- ❌ Ver otros usuarios
- ❌ Eliminar usuarios

#### **Usuario Administrador (`is_admin=true`)**
- ✅ Todo lo anterior
- ✅ Listar todos los usuarios (`GET /api/users`)
- ✅ Ver/editar cualquier usuario (`GET/PUT /api/users/{id}`)
- ✅ Eliminar usuarios (`DELETE /api/users/{id}`)

---

### **Validaciones de Token**

El token se valida en cada petición:

1. **Formato correcto:** `Authorization: Bearer <token>`
2. **Firma válida:** Verificación con `JWT_SECRET_KEY`
3. **No expirado:** `exp` < tiempo actual
4. **Usuario existe:** `user_id` (claim "sub") existe en BD
5. **Usuario activo:** `is_active = true`

Si alguna validación falla → `401 Unauthorized`

---

## 🧪 Testing

### **Usuarios de Prueba**

Asegúrate de que existan estos usuarios en la BD:

```sql
-- Usuario administrador
INSERT INTO users (email, password_hash, full_name, is_admin, is_active)
VALUES (
  'admin@example.com',
  '$2b$12$LJK8F9xG2hN3pQ4rS5tV6eW7xY8zA1bC2dE3fG4hI5jK6lM7nO8pQ',  -- Admin123!
  'Administrador',
  true,
  true
);

-- Usuario normal
INSERT INTO users (email, password_hash, full_name, is_admin, is_active)
VALUES (
  'user@example.com',
  '$2b$12$hN3pQ4rS5tV6eW7xY8zA1bC2dE3fG4hI5jK6lM7nO8pQLJK8F9xG2',  -- User123!
  'Usuario Normal',
  false,
  true
);
```

---

### **Escenarios de Prueba**

#### **1. Login Exitoso**
```bash
POST /api/users/login
{"email": "user@example.com", "password": "User123!"}
→ 200 OK, access_token retornado
```

#### **2. Login Fallido (Credenciales Incorrectas)**
```bash
POST /api/users/login
{"email": "user@example.com", "password": "WrongPass"}
→ 401 Unauthorized, "Credenciales inválidas"
```

#### **3. Acceso sin Token**
```bash
GET /api/accounts
(sin header Authorization)
→ 403 Forbidden, "Not authenticated"
```

#### **4. Acceso con Token Expirado**
```bash
GET /api/accounts
Authorization: Bearer <token_expirado>
→ 401 Unauthorized, "Token ha expirado"
```

#### **5. Acceso con Token Inválido**
```bash
GET /api/accounts
Authorization: Bearer invalid.token.here
→ 401 Unauthorized, "Token inválido"
```

#### **6. Usuario Regular intenta listar usuarios**
```bash
GET /api/users
Authorization: Bearer <token_user_regular>
→ 403 Forbidden, "No tienes permisos de administrador"
```

#### **7. Admin lista usuarios**
```bash
GET /api/users
Authorization: Bearer <token_admin>
→ 200 OK, lista de todos los usuarios
```

#### **8. Aislamiento de Datos - Usuario A no ve cuentas de Usuario B**
```bash
# Login como User A
POST /api/users/login {"email": "userA@example.com", ...}
access_token_A = response.access_token

# Login como User B
POST /api/users/login {"email": "userB@example.com", ...}
access_token_B = response.access_token

# User A crea cuenta
POST /api/accounts
Authorization: Bearer <access_token_A>
{"name": "Cuenta A", ...}
→ Cuenta creada con user_id = userA_id

# User B lista cuentas
GET /api/accounts
Authorization: Bearer <access_token_B>
→ Solo ve cuentas de User B, NO ve "Cuenta A"
```

---

## 🔄 Migración desde API Key

### **Para Clientes Existentes**

Si estabas usando el sistema de API Key, debes actualizar tu código:

#### **Antes (API Key):**
```javascript
fetch('http://localhost:8000/api/accounts', {
  headers: {
    'X-API-Key': 'tu-api-key-hardcodeada'
  }
})
```

#### **Después (JWT):**
```javascript
// 1. Login primero
const loginResponse = await fetch('http://localhost:8000/api/users/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'User123!'
  })
});
const { access_token } = await loginResponse.json();

// 2. Guardar token (localStorage, memoria, etc.)
localStorage.setItem('access_token', access_token);

// 3. Usar token en peticiones
fetch('http://localhost:8000/api/accounts', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
})
```

---

## ⚠️ Consideraciones de Seguridad

### **Producción**

1. **Cambiar `JWT_SECRET_KEY`:**
   ```bash
   # Generar clave segura de 32+ caracteres
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   
   Actualizar en `app/config.py`:
   ```python
   JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "clave_generada_aqui")
   ```

2. **Usar HTTPS:**
   - Los tokens se envían en headers HTTP
   - Sin HTTPS, pueden ser interceptados (Man-in-the-Middle)
   - Configurar certificado SSL/TLS en servidor

3. **Configurar CORS correctamente:**
   ```python
   # app/config.py
   CORS_ORIGINS = ["https://tudominio.com"]  # NO usar "*" en producción
   ```

4. **Configurar expiración de tokens:**
   - Producción: 15-30 minutos (valor actual)
   - Desarrollo: puede extenderse a 60 minutos
   ```python
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Más seguro
   ```

5. **Almacenamiento seguro en cliente:**
   - ❌ **NO usar `localStorage`** si tu app es vulnerable a XSS
   - ✅ Mejor: memoria (variable JS), httpOnly cookies
   - ✅ Para móviles: Keychain (iOS), KeyStore (Android)

6. **Refresh Tokens (futuro):**
   - Implementar tokens de refresco con expiración larga (7-30 días)
   - Access token corto (15 min) + Refresh token largo
   - Endpoint `POST /api/users/refresh` para renovar sin re-login

---

## 📊 Estructura de Token JWT

### **Payload del Token**

```json
{
  "sub": "9b1deb4d-7bf7-44a3-9cf7-ac94b02d7e26",  // UUID del usuario
  "exp": 1737572400  // Timestamp de expiración (Unix epoch)
}
```

- **`sub` (Subject):** Identificador único del usuario (UUID)
- **`exp` (Expiration Time):** Timestamp Unix de expiración

### **Decodificar Token (para debug)**

```python
import jwt

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
payload = jwt.decode(token, options={"verify_signature": False})
print(payload)
# {'sub': '9b1deb4d...', 'exp': 1737572400}
```

---

## 🆘 Troubleshooting

### **Error: "Token ha expirado"**
**Causa:** Token tiene más de 30 minutos  
**Solución:** Hacer login nuevamente para obtener nuevo token

---

### **Error: "Token inválido"**
**Causa:** Token corrupto, mal formado o firmado con otra clave  
**Solución:**
- Verificar que copias el token completo (sin espacios)
- Verificar que `JWT_SECRET_KEY` no haya cambiado
- Hacer login nuevamente

---

### **Error: "Usuario no encontrado"**
**Causa:** El `user_id` en el token no existe en la BD  
**Solución:**
- Usuario fue eliminado → hacer login con usuario válido
- Base de datos reseteada → recrear usuarios

---

### **Error: "No tienes permisos de administrador"**
**Causa:** Intentas acceder a endpoint admin con usuario regular  
**Solución:**
- Login con usuario admin (`admin@example.com`)
- Verificar que `is_admin=true` en BD

---

### **Error: "Not authenticated" (403)**
**Causa:** Falta header `Authorization` o formato incorrecto  
**Solución:**
- Verificar formato: `Authorization: Bearer <token>`
- Verificar que el header se envíe en la petición

---

## 📚 Referencias

- **JWT Spec (RFC 7519):** https://datatracker.ietf.org/doc/html/rfc7519
- **python-jose:** https://python-jose.readthedocs.io/
- **PyJWT:** https://pyjwt.readthedocs.io/
- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/

---

## ✅ Checklist de Implementación

- [x] PyJWT y python-jose instalados
- [x] `app/utils/jwt.py` creado
- [x] `app/config.py` actualizado con JWT settings
- [x] `app/utils/security.py` actualizado (get_current_user, get_current_admin_user)
- [x] `app/schemas/user.py` con TokenResponse
- [x] Login endpoint retorna JWT token
- [x] Todos los endpoints de users protegidos con JWT
- [x] AccountService filtra por user_id
- [x] Todos los endpoints de accounts protegidos con JWT
- [x] CategoryService filtra por user_id (via transacciones)
- [x] Todos los endpoints de categories protegidos con JWT
- [x] TransactionService filtra por user_id (via accounts)
- [x] Todos los endpoints de transactions protegidos con JWT
- [x] main.py actualizado (eliminadas referencias API Key)
- [x] Documentación creada (`docs/JWT_AUTHENTICATION.md`)

---

**Fecha de Implementación:** 23 de Enero de 2025  
**Versión API:** 1.0.0  
**Autor:** Sistema de Autenticación JWT
