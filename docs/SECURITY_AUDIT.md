# 🔒 AUDITORÍA DE SEGURIDAD - Backend AppFinanzas

**Fecha:** 2025-01-21 (Actualizado: 2026-02-11)  
**Versión auditada:** Código actual del repositorio  
**Auditor:** Revisión automatizada de seguridad  
**Estado:** Fase 1 de remediación completada

---

## 📊 RESUMEN EJECUTIVO

| Severidad | Cantidad | Remediados | Pendientes |
|-----------|----------|------------|------------|
| 🔴 CRÍTICO | 2 | ✅ 2 | 0 |
| 🟠 ALTO | 4 | ✅ 4 | 0 |
| 🟡 MEDIO | 5 | 0 | 5 |
| 🟢 BAJO | 3 | 0 | 3 |

**Hallazgos totales:** 14  
**Remediados:** 6 (Semana 1 completada)

---

## 📋 HALLAZGOS POR CATEGORÍA

---

### 1. AUTENTICACIÓN Y AUTORIZACIÓN

#### ✅ BIEN IMPLEMENTADO
- **Contraseñas hasheadas con bcrypt** (no MD5/SHA1)
- **JWT con expiración corta** (30 minutos access token)
- **Refresh tokens separados** (7 días, secret independiente)
- **Verificación de usuario activo** en cada request autenticado
- **Rate limiting en login** (5 intentos / 15 minutos)

#### 🟡 MEDIO: Rate limiting en memoria (no persistente)

**Archivo:** [app/utils/security.py](app/utils/security.py#L23-L30)

**Problema:** El rate limiting usa un diccionario en memoria. En deployments multi-instancia (múltiples workers/pods), cada instancia tiene su propio contador, permitiendo multiplicar los intentos.

**Código actual:**
```python
# Almacenamiento simple para rate limiting
rate_limit_storage: dict = {}
login_attempts: dict = {}
```

**Código corregido:**
```python
# Usar Redis para rate limiting distribuido
from redis import Redis
import os

redis_client = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

def check_rate_limit_redis(key: str, limit: int, window: int) -> bool:
    """Rate limiting distribuido con Redis"""
    pipe = redis_client.pipeline()
    now = int(time.time())
    window_key = f"rate:{key}:{now // window}"
    
    pipe.incr(window_key)
    pipe.expire(window_key, window)
    results = pipe.execute()
    
    return results[0] <= limit
```

**Impacto:** Un atacante puede multiplicar intentos de login usando N instancias.

---

#### 🟡 MEDIO: Falta bloqueo de cuenta temporal

**Archivo:** [app/routes/users.py](app/routes/users.py)

**Problema:** Tras 5 intentos fallidos, solo hay rate limiting temporal. No hay bloqueo de cuenta que notifique al usuario ni requiera verificación adicional.

**Recomendación:**
```python
# En user_service.py
async def check_account_lockout(db: Session, user: User) -> bool:
    """Verifica si la cuenta está bloqueada temporalmente"""
    if user.failed_login_attempts >= 5:
        lockout_until = user.last_failed_login + timedelta(minutes=15)
        if datetime.now(timezone.utc) < lockout_until:
            return True  # Cuenta bloqueada
        # Reset intentos si pasó el tiempo
        user.failed_login_attempts = 0
        db.commit()
    return False

# Agregar columnas al modelo User:
# failed_login_attempts = Column(Integer, default=0)
# last_failed_login = Column(DateTime(timezone=True), nullable=True)
```

---

### 2. ENCRIPTACIÓN

#### ✅ BIEN IMPLEMENTADO
- **AES-256-GCM implementado** (Fase 1 completada)
- **Key management con versionado** para rotación
- **Contraseñas con bcrypt** (salt automático)

#### 🔴 CRÍTICO: Datos sensibles NO encriptados en BD

**Archivos:** [app/models/user.py](app/models/user.py), [app/models/account.py](app/models/account.py)

**Problema:** Campos como `email`, `full_name`, números de cuenta, y montos de transacciones se almacenan en texto plano en PostgreSQL. La infraestructura de encriptación está implementada pero NO aplicada.

**Datos expuestos:**
- `users.email` - PII
- `users.full_name` - PII
- `users.profile_picture` - PII potencial
- `accounts.*` - Información financiera
- `transactions.*` - Información financiera

**Código a implementar (Fase 2):**
```python
# En models/user.py
from app.utils.encryption import encrypt_field, decrypt_field

class User(Base):
    # Campo encriptado
    _email_encrypted = Column("email_encrypted", Text, nullable=True)
    
    @property
    def email(self) -> str:
        if self._email_encrypted:
            return decrypt_field(self._email_encrypted)
        return self._email_plain  # Compatibilidad migración
    
    @email.setter
    def email(self, value: str):
        self._email_encrypted = encrypt_field(value)
```

**Impacto:** Exposición total de PII en caso de brecha de BD.

---

#### 🟠 ALTO: TLS no verificado en conexiones a BD

**Archivo:** [app/database.py](app/database.py)

**Problema:** La conexión a PostgreSQL no especifica `sslmode=verify-full`. Los datos viajan potencialmente sin cifrar.

**Código actual:**
```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)
```

**Código corregido:**
```python
from sqlalchemy import create_engine

def get_engine():
    url = settings.DATABASE_URL
    
    # Forzar SSL para producción
    if settings.ENVIRONMENT == "production":
        connect_args = {
            "sslmode": "verify-full",
            "sslrootcert": "/path/to/ca-certificate.crt"
        }
    else:
        connect_args = {"sslmode": "prefer"}
    
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args=connect_args
    )

engine = get_engine()
```

---

### 3. SEGURIDAD DE BASE DE DATOS

#### ✅ BIEN IMPLEMENTADO
- **SQLAlchemy ORM** previene SQL injection
- **UUIDs como IDs** (no secuenciales)
- **Filtros por user_id** en todas las queries
- **Check constraints** en modelo (ej: email format)

#### 🟢 BAJO: Sin índices en campos de auditoría

**Recomendación:** Agregar índices para mejorar queries de auditoría:
```sql
CREATE INDEX idx_users_last_login ON users(last_login);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
```

---

### 4. VALIDACIÓN DE INPUTS

#### ✅ BIEN IMPLEMENTADO
- **Pydantic schemas** con validaciones
- **min_length/max_length** en campos
- **EmailStr** para validación de email
- **Regex patterns** para tipos de transacción
- **Validators personalizados** (amount != 0, fecha no futura)

#### 🟡 MEDIO: Falta sanitización de campos de texto libre

**Archivos:** [app/schemas/transaction.py](app/schemas/transaction.py), [app/schemas/account.py](app/schemas/account.py)

**Problema:** Campos como `description`, `notes`, `tags` aceptan cualquier contenido sin sanitizar HTML/scripts.

**Código a agregar:**
```python
import bleach
from pydantic import field_validator

class TransactionBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    
    @field_validator('description', 'notes')
    @classmethod
    def sanitize_text(cls, v):
        if v:
            # Eliminar HTML/scripts
            return bleach.clean(v, tags=[], strip=True)
        return v
```

**Dependencia:** `pip install bleach`

---

### 5. SEGURIDAD DE API

#### ✅ BIEN IMPLEMENTADO
- **Rate limiting global** (100 req/60s)
- **CORS configurado** con orígenes específicos (no `*`)
- **Security headers** implementados (X-Content-Type-Options, X-Frame-Options, etc.)
- **HTTP-only cookies** para tokens
- **SameSite=Lax** en cookies

#### 🟠 ALTO: TrustedHostMiddleware comentado

**Archivo:** [app/main.py](app/main.py)

**Problema:** El middleware de hosts confiables está comentado, permitiendo ataques de Host header injection.

**Código actual (comentado):**
```python
# from starlette.middleware.trustedhost import TrustedHostMiddleware
# app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
```

**Código corregido:**
```python
from starlette.middleware.trustedhost import TrustedHostMiddleware

# En producción, especificar hosts permitidos
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=[
            "api.tudominio.com",
            "myfi-app-backend.onrender.com"
        ]
    )
```

---

#### 🟡 MEDIO: Falta HSTS header

**Archivo:** [app/main.py](app/main.py)

**Problema:** No se incluye header `Strict-Transport-Security` para forzar HTTPS.

**Código a agregar en el middleware de security headers:**
```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Headers existentes...
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # AGREGAR HSTS (solo en producción con HTTPS)
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response
```

---

#### 🟢 BAJO: Falta Content-Security-Policy

**Recomendación:** Agregar CSP header para prevenir XSS:
```python
response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
```

---

### 6. GESTIÓN DE SECRETS

#### 🔴 CRÍTICO: API Key potencialmente comprometida

**Archivo:** [.env](.env#L29-L30)

**Problema:** El comentario en `.env` indica que la GEMINI_API_KEY fue expuesta públicamente:
```
# IMPORTANTE: Solicita una nueva API Key en https://ai.google.dev/
# La anterior fue expuesta públicamente y debe rotarse
GEMINI_API_KEY=AIzaSyCHP-2b-FtqTHEMe7T5iBHZpZdv0w13om0
```

**Acción inmediata:**
1. Rotar la GEMINI_API_KEY en Google Cloud Console
2. Rotar TODAS las demás API keys por precaución
3. Revisar logs de acceso de las APIs para uso no autorizado

---

#### ✅ BIEN IMPLEMENTADO
- `.gitignore` incluye `.env`
- `.env.example` sin valores reales
- Secrets cargados desde variables de entorno

#### 🟡 MEDIO: Falta validación de secrets al inicio

**Archivo:** [app/config.py](app/config.py)

**Problema:** Los secrets tienen valores por defecto vacíos. La app puede iniciar sin ellos configurados.

**Código a agregar:**
```python
from pydantic import field_validator

class Settings(BaseSettings):
    JWT_SECRET_KEY: str = ""
    
    @field_validator('JWT_SECRET_KEY', 'REFRESH_TOKEN_SECRET_KEY')
    @classmethod
    def validate_secrets(cls, v, info):
        if not v or len(v) < 32:
            raise ValueError(f"{info.field_name} debe tener al menos 32 caracteres")
        return v
    
    @field_validator('ENCRYPTION_MASTER_KEY')
    @classmethod
    def validate_encryption_key(cls, v):
        if v and len(v) < 32:
            raise ValueError("ENCRYPTION_MASTER_KEY debe tener al menos 32 caracteres")
        return v
```

---

### 7. LOGGING Y AUDITORÍA

#### ✅ BIEN IMPLEMENTADO
- **Logging estructurado** con timestamps
- **Rotación de logs** (diaria, 30 días retención)
- **Niveles de log** configurables
- **Logs por módulo** con contexto

#### 🟠 ALTO: Logs pueden contener datos sensibles

**Archivo:** [app/services/user_service.py](app/services/user_service.py#L61-L62)

**Problema:** Se loguean emails y otros datos PII:
```python
logger.info(f"Buscando usuario con email: {email}")
logger.info(f"Usuario encontrado: {user.email}")
```

**Código corregido:**
```python
import hashlib

def mask_pii(value: str) -> str:
    """Enmascara PII para logs"""
    if '@' in value:  # Email
        local, domain = value.split('@')
        return f"{local[:2]}***@{domain}"
    return f"{value[:2]}***{value[-2:]}" if len(value) > 4 else "***"

# Uso:
logger.info(f"Buscando usuario con email: {mask_pii(email)}")
```

---

#### 🟡 MEDIO: Falta audit trail para operaciones críticas

**Recomendación:** Crear tabla de auditoría:
```python
# app/models/audit_log.py
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)  # LOGIN, LOGOUT, UPDATE_PROFILE, etc.
    resource_type = Column(String(50))  # USER, ACCOUNT, TRANSACTION
    resource_id = Column(UUID(as_uuid=True))
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    details = Column(JSONB)  # Detalles adicionales
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

### 8. CUMPLIMIENTO GDPR

#### ✅ PARCIALMENTE IMPLEMENTADO
- Datos almacenados solo necesarios
- Usuarios pueden ser desactivados

#### 🟠 ALTO: Falta endpoint de eliminación de datos (Right to be forgotten)

**Problema:** No existe endpoint para que usuarios soliciten eliminación de todos sus datos.

**Código a implementar:**
```python
# app/routes/users.py
@router.delete("/me/data", status_code=status.HTTP_202_ACCEPTED)
async def request_data_deletion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Solicita eliminación de todos los datos del usuario (GDPR Art. 17)
    
    Inicia proceso de eliminación que:
    1. Anonimiza datos inmediatamente
    2. Elimina datos completamente en 30 días
    3. Envía confirmación por email
    """
    # Anonimizar inmediatamente
    current_user.email = f"deleted_{current_user.id}@anonymized.local"
    current_user.username = None
    current_user.full_name = "Usuario Eliminado"
    current_user.profile_picture = None
    current_user.is_active = False
    
    # Programar eliminación completa
    # (usar Celery o similar para job asíncrono)
    
    db.commit()
    
    return {"message": "Solicitud de eliminación recibida. Datos anonimizados."}
```

---

#### 🟡 MEDIO: Falta endpoint de exportación de datos (Portabilidad)

**Recomendación:** Implementar `/me/export` para GDPR Art. 20.

---

### 9. VULNERABILIDADES COMUNES

#### ✅ PROTEGIDO
- **SQL Injection:** SQLAlchemy ORM con parámetros
- **XSS:** No renderiza HTML (API JSON pura)
- **CSRF:** SameSite cookies + tokens separados
- **Path Traversal:** Validación de extensiones en upload

#### 🟡 MEDIO: Upload de archivos sin escaneo de malware

**Archivo:** [app/routes/upload.py](app/routes/upload.py)

**Problema:** Se aceptan archivos PDF/Excel sin verificar contenido malicioso.

**Recomendación:**
```python
import clamd  # ClamAV

async def scan_file_for_malware(file_path: str) -> bool:
    """Escanea archivo con ClamAV"""
    try:
        cd = clamd.ClamdUnixSocket()
        result = cd.scan(file_path)
        return result[file_path][0] == 'OK'
    except Exception:
        # Si ClamAV no está disponible, log warning
        logger.warning("ClamAV no disponible, omitiendo escaneo")
        return True
```

---

### 10. MEJORES PRÁCTICAS

#### ✅ IMPLEMENTADO
- Código organizado en capas (routes/services/models)
- Dependency injection con FastAPI
- Tipado con type hints
- Documentación en docstrings

#### 🟢 BAJO: Falta headers de versión de API

**Recomendación:** Agregar versionado de API:
```python
@app.middleware("http")
async def add_api_version(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-API-Version"] = "1.0.0"
    return response
```

---

## 🎯 PLAN DE ACCIÓN PRIORIZADO

### Semana 1 (CRÍTICO + ALTO)

| # | Severidad | Tarea | Archivo | Estado |
|---|-----------|-------|---------|--------|
| 1 | 🔴 CRÍTICO | Rotar TODAS las API keys | .env | ✅ COMPLETADO |
| 2 | 🔴 CRÍTICO | Implementar encriptación BD (Fase 2) | models/*.py | ✅ COMPLETADO |
| 3 | 🟠 ALTO | Habilitar TLS en conexión BD | database.py | ✅ COMPLETADO |
| 4 | 🟠 ALTO | Habilitar TrustedHostMiddleware | main.py | ✅ COMPLETADO |
| 5 | 🟠 ALTO | Sanitizar logs (no PII) | services/*.py | ✅ COMPLETADO |
| 6 | 🟠 ALTO | Endpoint eliminación datos | routes/users.py | ✅ COMPLETADO |

### Semana 2 (MEDIO)

| # | Severidad | Tarea | Archivo | Esfuerzo |
|---|-----------|-------|---------|----------|
| 7 | 🟡 MEDIO | Rate limiting con Redis | utils/security.py | 4h |
| 8 | 🟡 MEDIO | Bloqueo temporal de cuentas | services/user_service.py | 3h |
| 9 | 🟡 MEDIO | Sanitización HTML inputs | schemas/*.py | 2h |
| 10 | 🟡 MEDIO | Header HSTS | main.py | 30m |
| 11 | 🟡 MEDIO | Validación secrets al inicio | config.py | 1h |
| 12 | 🟡 MEDIO | Audit trail tabla | models/audit_log.py | 4h |
| 13 | 🟡 MEDIO | Endpoint exportación datos | routes/users.py | 4h |

### Semana 3 (BAJO + MEJORAS)

| # | Severidad | Tarea | Archivo | Esfuerzo |
|---|-----------|-------|---------|----------|
| 14 | 🟢 BAJO | CSP header | main.py | 30m |
| 15 | 🟢 BAJO | API versioning header | main.py | 30m |
| 16 | 🟢 BAJO | Índices auditoría BD | migrations/ | 1h |
| 17 | MEJORA | Escaneo malware uploads | routes/upload.py | 4h |

---

## 📈 MÉTRICAS DE SEGURIDAD POST-AUDITORÍA

Tras implementar las correcciones, se recomienda:

1. **Penetration testing** externo
2. **Dependency audit** con `pip-audit` o `safety`
3. **SAST** con Bandit: `bandit -r app/`
4. **Monitoreo continuo** de logs de seguridad

---

## 📎 ANEXO: Comandos Útiles

```bash
# Auditar dependencias
pip install pip-audit
pip-audit

# Análisis estático de seguridad
pip install bandit
bandit -r app/ -f json -o security_report.json

# Generar secret seguro
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Verificar conexión SSL a PostgreSQL
openssl s_client -connect your-db-host:5432 -starttls postgres
```

---

**Documento generado automáticamente. Revisar manualmente antes de implementar.**
