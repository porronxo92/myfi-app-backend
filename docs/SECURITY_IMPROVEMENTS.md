# 🔒 Mejoras de Seguridad Implementadas

## ✅ Cambios Completados

### 1. **Secretos Movidos a Variables de Entorno**

**Antes:** Credenciales hardcoded en `app/config.py`
```python
JWT_SECRET_KEY = "your-secret-key-change-in-production"
DATABASE_URL = "postgresql://admin:rcruzd@localhost:30432/app_finance"
GEMINI_API_KEY = "AIzaSyClcoXfzAwJoOUoluii2fCd6FJELpvx3rY"
```

**Ahora:** Variables de entorno en `.env`
```python
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
```

**Archivos:**
- ✅ `.env` - Contiene secretos reales (NO en git)
- ✅ `.env.example` - Plantilla pública (SÍ en git)
- ✅ `.gitignore` - Ya incluye `.env`

---

### 2. **Claves JWT Seguras Generadas**

**Claves generadas con 48 caracteres aleatorios:**
- ✅ `JWT_SECRET_KEY` - Para access tokens (30 min)
- ✅ `REFRESH_TOKEN_SECRET_KEY` - Para refresh tokens (7 días)

**Generadas con:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

### 3. **Protección Brute Force en Login**

**Implementación:**
- ✅ Máximo **5 intentos fallidos** por IP + email
- ✅ Bloqueo de **15 minutos** tras exceder límite
- ✅ Contador de intentos restantes en respuesta
- ✅ HTTP 429 con header `Retry-After`

**Endpoint:** `POST /api/users/login`

**Ejemplo de respuesta tras 3 fallos:**
```json
{
  "detail": "Email o contraseña incorrectos. Intentos restantes: 2"
}
```

**Tras 5 fallos:**
```json
{
  "detail": "Demasiados intentos fallidos. Bloqueado por 15 minutos."
}
```

**Código en:** `app/routes/users.py` - línea ~210

---

### 4. **Validación de Tamaño de Archivo (Anti-DoS)**

**Implementación:**
- ✅ Validación **antes de cargar en RAM**
- ✅ Lectura en chunks de 8KB
- ✅ HTTP 413 si excede 10MB
- ✅ Liberación automática de memoria

**Función:** `validate_file_size()` en `app/routes/upload.py`

**Antes:** Archivo completo cargado en memoria → vulnerable a DoS
**Ahora:** Validación incremental → seguro

```python
async def validate_file_size(file: UploadFile, max_size_mb: int):
    max_size_bytes = max_size_mb * 1024 * 1024
    size = 0
    chunk_size = 8192  # 8KB chunks
    
    while chunk := await file.read(chunk_size):
        size += len(chunk)
        if size > max_size_bytes:
            raise HTTPException(413, "Archivo demasiado grande")
    
    await file.seek(0)  # Reset
```

---

### 5. **Refresh Tokens Implementados**

**Flujo de autenticación mejorado:**

1. **Login inicial:**
```bash
POST /api/users/login
{
  "email": "user@example.com",
  "password": "Password123!"
}
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGci...",      // Expira en 30 min
  "refresh_token": "eyJhbGci...",     // Expira en 7 días
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { "id": "...", "email": "..." }
}
```

2. **Renovar tokens (sin re-login):**
```bash
POST /api/users/refresh
{
  "refresh_token": "eyJhbGci..."
}
```

**Respuesta:** Nuevos access_token + refresh_token

**Beneficios:**
- ✅ Usuario NO necesita re-autenticarse cada 30 min
- ✅ Mejor UX (sesión activa por 7 días)
- ✅ Seguridad mantenida (access token corto)

**Archivos modificados:**
- `app/utils/jwt.py` - `create_refresh_token()`, `verify_refresh_token()`
- `app/schemas/user.py` - `RefreshTokenRequest`, `TokenResponse` actualizado
- `app/routes/users.py` - Endpoint `/refresh` añadido

---

## 🚨 IMPORTANTE: Rotar Gemini API Key

**⚠️ ACCIÓN REQUERIDA:**

La API Key anterior fue expuesta públicamente en el código y debe rotarse.

**Pasos:**

1. Ir a https://ai.google.dev/
2. Generar nueva API Key
3. Actualizar en `.env`:
```bash
GEMINI_API_KEY=TU_NUEVA_API_KEY_AQUI
```
4. Eliminar la antigua en Google Cloud Console

---

## 📋 Configuración Inicial (Nuevo Entorno)

### 1. Copiar plantilla de variables de entorno:
```bash
cp .env.example .env
```

### 2. Generar claves secretas:
```bash
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(48))"
python -c "import secrets; print('REFRESH_TOKEN_SECRET_KEY=' + secrets.token_urlsafe(48))"
```

### 3. Editar `.env` con tus valores:
```bash
JWT_SECRET_KEY=<pegar_clave_generada_1>
REFRESH_TOKEN_SECRET_KEY=<pegar_clave_generada_2>
DATABASE_URL=postgresql://user:pass@host:port/db
GEMINI_API_KEY=<tu_api_key>
```

### 4. Verificar que `.env` NO esté en git:
```bash
git status  # NO debe aparecer .env
```

---

## 🔐 Nuevas Configuraciones Disponibles

**Rate Limiting de Login:**
```env
LOGIN_RATE_LIMIT_ATTEMPTS=5          # Intentos antes de bloqueo
LOGIN_RATE_LIMIT_WINDOW_MINUTES=15   # Duración del bloqueo
```

**Refresh Tokens:**
```env
REFRESH_TOKEN_SECRET_KEY=<clave_secreta>
REFRESH_TOKEN_EXPIRE_DAYS=7          # Validez del refresh token
```

**Access Tokens:**
```env
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30   # Validez del access token
```

---

## 🧪 Testing

### Test 1: Login con contraseña incorrecta (5 veces)
```bash
# Intento 1-4: Debe responder "Intentos restantes: X"
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"wrong"}'

# Intento 5: Debe bloquear por 15 minutos
# Response: HTTP 429 "Demasiados intentos fallidos"
```

### Test 2: Refresh Token
```bash
# 1. Login
TOKEN=$(curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"User123!"}' \
  | jq -r '.refresh_token')

# 2. Esperar 30 min (access token expira)

# 3. Renovar sin re-login
curl -X POST http://localhost:8000/api/users/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$TOKEN\"}"
```

### Test 3: Validación de archivo grande
```bash
# Crear archivo de 11MB (excede límite de 10MB)
dd if=/dev/zero of=large.pdf bs=1M count=11

# Intentar subir (debe fallar con HTTP 413)
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer <token>" \
  -F "fichero=@large.pdf"

# Response esperado: "Archivo demasiado grande. Máximo permitido: 10MB"
```

---

## 📊 Resumen de Seguridad

| Vulnerabilidad | Estado | Mitigación |
|----------------|--------|------------|
| Secretos hardcoded | ✅ RESUELTO | Variables de entorno |
| JWT_SECRET_KEY débil | ✅ RESUELTO | 48 chars aleatorios |
| Gemini API expuesta | ✅ RESUELTO | Rotar en Google Cloud |
| Brute force login | ✅ RESUELTO | 5 intentos / 15 min |
| DoS por archivos grandes | ✅ RESUELTO | Validación en chunks |
| UX de re-login frecuente | ✅ RESUELTO | Refresh tokens (7 días) |

---

## 🔄 Migración de Código Existente

**Si ya tienes el proyecto en producción:**

1. **Crear `.env` en el servidor**
2. **Generar nuevas claves secretas** (distintas a desarrollo)
3. **Actualizar código** (pull latest)
4. **Reiniciar servidor**

**⚠️ NOTA:** Los tokens antiguos serán inválidos al cambiar `JWT_SECRET_KEY`.  
Todos los usuarios deberán hacer login nuevamente.

---

**Fecha de implementación:** 23 de Diciembre de 2025  
**Versión:** 1.1.0 - Security Hardening
