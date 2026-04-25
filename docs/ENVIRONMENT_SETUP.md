# Guía de Configuración de Entornos

## Descripción General

Esta aplicación backend soporta tres entornos distintos:
- **DEV** (Desarrollo): Desarrollo local con frontend en localhost
- **PRE** (Pre-producción): Entorno de pruebas en Render + Netlify
- **PRO** (Producción): Entorno de producción en GCP Cloud Run

Cada entorno tiene su propia configuración, URLs y ajustes de seguridad.

---

## 📋 Matriz de Configuración

| Configuración | DEV (Desarrollo) | PRE (Pre-producción) | PRO (Producción) |
|--------------|------------------|----------------------|------------------|
| **ENVIRONMENT** | `development` | `pre` | `production` |
| **URL Frontend** | `http://localhost:4200` | `https://myfi-front.netlify.app` | TBD (Cloud Run) |
| **URL Backend** | `http://localhost:8000` | `https://myfi-app-backend.onrender.com` | TBD (Cloud Run) |
| **Base de Datos** | Neon PostgreSQL (compartida) | Neon PostgreSQL (compartida) | TBD (Cloud SQL o Neon) |
| **SSL Requerido** | No (preferido) | Sí (requerido) | Sí (requerido) |
| **TrustedHostMiddleware** | Deshabilitado | Habilitado | Habilitado |
| **Cabecera HSTS** | Deshabilitada | Habilitada | Habilitada |
| **Despliegue** | Manual (local) | Auto (GitHub → Render) | Auto (GitHub → Cloud Run) |
| **Rama Git** | N/A (cambios locales) | `develop` | `main` |
| **Gestión de Secretos** | Fichero `.env` | Panel de Render | GCP Secret Manager |
| **Logging** | Fichero + stdout (DEBUG) | stdout (INFO) | Cloud Logging (INFO) |
| **CORS** | Múltiples orígenes localhost | Solo Netlify | Solo frontend de producción |
| **Tamaño Pool BD** | 5 | 10 | 20 |
| **Rate Limiting** | Estándar | Estándar | Reforzado |

---

## 🚀 Inicio Rápido

### DEV (Entorno de Desarrollo)

1. **Copiar la plantilla de entorno:**
   ```powershell
   cp .env.development.example .env
   ```

2. **Actualizar los secretos requeridos en `.env`:**
   ```bash
   # Generar secretos JWT
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   
   # Generar clave de cifrado
   python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
   ```

3. **Configurar las claves de API:**
   - `GEMINI_API_KEY` - Obtener en https://ai.google.dev/
   - `FINNHUB_API_KEY` - Obtener en https://finnhub.io/
   - `ALPHA_VANTAGE_API_KEY` - Obtener en https://www.alphavantage.co/
   - `BRANDFETCH_CLIENT_ID` - Obtener en https://brandfetch.com/

4. **Verificar la conexión a la base de datos:**
   ```powershell
   python app/database.py  # Debería conectar correctamente
   ```

5. **Arrancar el backend:**
   ```powershell
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Probar la API:**
   - Abrir http://localhost:8000/docs (Swagger UI)
   - Comprobar http://localhost:8000/health (debe devolver 200)

---

### PRE (Entorno de Pre-producción)

**Despliegue:** Automático mediante GitHub Actions al hacer push a la rama `develop`.

1. **Configurar variables de entorno en Render:**
   - Ir a Panel de Render → Tu Servicio → Environment
   - Añadir todas las variables de `.env.pre.example`
   - Generar nuevos secretos (distintos a los de DEV)

2. **Configuración requerida en Render:**
   ```
   ENVIRONMENT=pre
   FRONTEND_URL=https://myfi-front.netlify.app
   BACKEND_URL=https://myfi-app-backend.onrender.com
   ALLOWED_HOSTS=myfi-app-backend.onrender.com
   CORS_ORIGINS=https://myfi-front.netlify.app
   DATABASE_URL_PRE=<tu-cadena-de-conexion-neon>
   JWT_SECRET_KEY=<generar-nueva-clave-segura>
   REFRESH_TOKEN_SECRET_KEY=<generar-nueva-clave-segura>
   ENCRYPTION_MASTER_KEY=<generar-nueva-clave-de-cifrado>
   # ... (añadir el resto de variables)
   ```

3. **Habilitar despliegue automático:**
   - Panel de Render → Settings → Build & Deploy
   - Conectar al repositorio de GitHub
   - Establecer rama: `develop`
   - Auto-Deploy: Sí

4. **Verificar el despliegue:**
   ```powershell
   curl https://myfi-app-backend.onrender.com/health
   ```

---

### PRO (Entorno de Producción - GCP Cloud Run)

**Despliegue:** Automático mediante GitHub Actions al hacer push a la rama `main`.

#### Requisitos Previos

1. **Configuración del Proyecto GCP:**
   ```powershell
   # Establecer el proyecto
   gcloud config set project YOUR_PROJECT_ID
   
   # Habilitar las APIs necesarias
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   ```

2. **Crear secretos en GCP Secret Manager:**
   ```powershell
   # Secreto JWT
   echo -n "YOUR_GENERATED_JWT_SECRET" | gcloud secrets create jwt-secret-key --data-file=-
   
   # Secreto Refresh Token
   echo -n "YOUR_GENERATED_REFRESH_SECRET" | gcloud secrets create refresh-token-secret --data-file=-
   
   # Clave de Cifrado
   echo -n "YOUR_GENERATED_ENCRYPTION_KEY" | gcloud secrets create encryption-master-key --data-file=-
   
   # URL de Base de Datos
   echo -n "YOUR_DATABASE_CONNECTION_STRING" | gcloud secrets create database-url-prod --data-file=-
   
   # Claves de API
   echo -n "YOUR_GEMINI_KEY" | gcloud secrets create gemini-api-key --data-file=-
   echo -n "YOUR_FINNHUB_KEY" | gcloud secrets create finnhub-api-key --data-file=-
   echo -n "YOUR_ALPHA_VANTAGE_KEY" | gcloud secrets create alpha-vantage-api-key --data-file=-
   echo -n "YOUR_BRANDFETCH_ID" | gcloud secrets create brandfetch-client-id --data-file=-
   ```

3. **Otorgar acceso de Cloud Run a los secretos:**
   ```powershell
   # Obtener la cuenta de servicio de Cloud Run
   PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
   SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
   
   # Conceder acceso a todos los secretos
   gcloud secrets add-iam-policy-binding jwt-secret-key \
     --member="serviceAccount:${SERVICE_ACCOUNT}" \
     --role="roles/secretmanager.secretAccessor"
   
   # Repetir para el resto de secretos...
   ```

4. **Configurar GitHub Actions:**
   - Añadir el secreto de GitHub `GCP_PROJECT_ID` con el ID de tu proyecto
   - Configurar Workload Identity Federation (ver `.github/workflows/deploy-prod.yml`)

5. **Despliegue manual inicial:**
   ```powershell
   # Construir contenedor
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/finanzas-api
   
   # Desplegar en Cloud Run
   gcloud run deploy finanzas-api \
     --image gcr.io/YOUR_PROJECT_ID/finanzas-api \
     --region europe-west1 \
     --platform managed \
     --allow-unauthenticated \
     --memory 512Mi \
     --cpu 1 \
     --min-instances 0 \
     --max-instances 10 \
     --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO,LLM_PROVIDER=gemini,LLM_MODEL=gemini-2.0-flash" \
     --set-secrets="JWT_SECRET_KEY=jwt-secret-key:latest,REFRESH_TOKEN_SECRET_KEY=refresh-token-secret:latest,ENCRYPTION_MASTER_KEY=encryption-master-key:latest,DATABASE_URL_PROD=database-url-prod:latest,GEMINI_API_KEY=gemini-api-key:latest,FINNHUB_API_KEY=finnhub-api-key:latest,ALPHA_VANTAGE_API_KEY=alpha-vantage-api-key:latest,BRANDFETCH_CLIENT_ID=brandfetch-client-id:latest"
   ```

6. **Actualizar URLs específicas del entorno:**
   - Tras el despliegue, actualizar `FRONTEND_URL`, `BACKEND_URL`, `ALLOWED_HOSTS` en Cloud Run
   - Configurar dominio personalizado si es necesario

---

## 🔐 Buenas Prácticas de Seguridad

### Generación de Secretos

```powershell
# Secretos JWT (se recomiendan 48+ caracteres)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Clave de Cifrado (32 bytes codificados en base64 para AES-256)
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

### Rotación de Secretos

1. **Secretos JWT:** Rotar cada 90 días
2. **Clave de Cifrado:** Usar `ENCRYPTION_KEY_VERSION` para la rotación
   - Generar nueva clave con versión incrementada
   - Actualizar la aplicación para soportar ambas versiones
   - Migrar los datos de forma gradual
   - Deprecar la versión antigua

### Aislamiento de Entornos

- ✅ **Usar secretos distintos para cada entorno**
- ✅ **Nunca subir ficheros `.env` al repositorio**
- ✅ **Almacenar secretos de producción en GCP Secret Manager**
- ✅ **Restringir el acceso a secretos de producción (roles IAM)**
- ✅ **Auditar el acceso a secretos en Cloud Console**

---

## 🗄️ Configuración de la Base de Datos

### Base de Datos Compartida (Configuración Actual)

DEV y PRE comparten actualmente la misma base de datos Neon PostgreSQL:
```
postgresql://neondb_owner:npg_6kU1KjbCclpY@ep-jolly-river-a93ithgb.gwc.azure.neon.tech/neondb
```

⚠️ **Consideración:** Para un mejor aislamiento de datos, considera:
- Crear una rama de Neon separada para PRE
- Usar esquemas distintos dentro de la misma base de datos
- Configurar una base de datos completamente separada para PRE

### Opciones de Base de Datos para Producción

#### Opción A: Cloud SQL PostgreSQL (Recomendada)

**Ventajas:**
- Integración nativa con GCP
- Conectividad por IP privada
- Copias de seguridad automáticas
- Alta disponibilidad
- Sin exposición a internet público

**Configuración:**
```powershell
# Crear instancia Cloud SQL
gcloud sql instances create finanzas-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=europe-west1

# Crear base de datos
gcloud sql databases create app_finance --instance=finanzas-db

# Importar schema
gcloud sql import sql finanzas-db gs://YOUR_BUCKET/schema_app_finance.sql \
  --database=app_finance
```

#### Opción B: Continuar con Neon PostgreSQL

**Ventajas:**
- Sin necesidad de migración
- Ya configurado
- Escalado serverless
- Nivel gratuito disponible

**Configuración:**
- Crear base de datos de producción en el panel de Neon
- Actualizar el secreto `DATABASE_URL_PROD` en GCP Secret Manager

---

## 🔄 Cambiar de Entorno en Local

Para probar distintas configuraciones de entorno en local:

```powershell
# Probar configuración PRE en local
cp .env.pre.example .env.pre.local
# Editar .env.pre.local con tus valores
$env:ENVIRONMENT="pre"; uvicorn app.main:app --reload --env-file .env.pre.local

# Probar configuración de PRODUCCIÓN en local (contra recursos de producción)
cp .env.production.example .env.production.local
# Editar .env.production.local
$env:ENVIRONMENT="production"; uvicorn app.main:app --reload --env-file .env.production.local
```

⚠️ **Advertencia:** ¡Ten cuidado al probar con la configuración de producción en local!

---

## 📊 Referencia de Variables de Entorno

### Configuración Principal

| Variable | DEV | PRE | PRO | Descripción |
|----------|-----|-----|-----|-------------|
| `ENVIRONMENT` | `development` | `pre` | `production` | Identificador de entorno |
| `FRONTEND_URL` | `http://localhost:4200` | `https://myfi-front.netlify.app` | TBD | URL del frontend |
| `BACKEND_URL` | `http://localhost:8000` | `https://myfi-app-backend.onrender.com` | TBD | URL del backend |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `myfi-app-backend.onrender.com` | TBD | Hosts de confianza |

### Seguridad

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `JWT_SECRET_KEY` | ✅ Sí | Clave de firma JWT (48+ caracteres) |
| `REFRESH_TOKEN_SECRET_KEY` | ✅ Sí | Clave de firma del refresh token |
| `ENCRYPTION_MASTER_KEY` | ✅ Sí | Clave de cifrado AES-256 (base64) |
| `ENCRYPTION_KEY_VERSION` | No | Versión de clave para rotación (por defecto: 1) |
| `JWT_ALGORITHM` | No | Algoritmo JWT (por defecto: HS256) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | Expiración del token (por defecto: 30) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | Expiración del refresh token (por defecto: 7) |

### Base de Datos

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `DATABASE_URL_LOCALHOST` | Para DEV | Cadena de conexión de la base de datos de desarrollo |
| `DATABASE_URL_PRE` | Para PRE | Cadena de conexión de la base de datos de pre-producción |
| `DATABASE_URL_PROD` | Para PRO | Cadena de conexión de la base de datos de producción |
| `DB_POOL_SIZE` | No | Tamaño del pool de conexiones (por defecto: 5) |
| `DB_POOL_OVERFLOW` | No | Conexiones de desbordamiento máximas (por defecto: 10) |

### APIs Externas

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `GEMINI_API_KEY` | ✅ Sí | Clave de API de Google Gemini LLM |
| `FINNHUB_API_KEY` | ✅ Sí | Clave de API de mercado de valores Finnhub |
| `ALPHA_VANTAGE_API_KEY` | ✅ Sí | Clave de API de Alpha Vantage (alternativa) |
| `BRANDFETCH_CLIENT_ID` | No | Client ID de la API de logos Brandfetch |

### CORS y Red

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `CORS_ORIGINS` | ✅ Sí | Orígenes permitidos separados por comas |
| `CORS_MAX_AGE` | No | Segundos de caché del preflight CORS (por defecto: 3600) |

### Logging

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `LOG_LEVEL` | No | Nivel de logging (por defecto: INFO) |
| `LOGS_DIR` | No | Directorio de logs (por defecto: ../logsBackend) |
| `LOG_ROTATION_SIZE_MB` | No | Tamaño máximo del fichero de log (por defecto: 10) |
| `LOG_BACKUP_COUNT` | No | Número de logs de respaldo (por defecto: 5) |

### Rate Limiting

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `RATE_LIMIT_REQUESTS` | No | Máximo de peticiones por ventana (por defecto: 100) |
| `RATE_LIMIT_WINDOW` | No | Ventana de tiempo en segundos (por defecto: 60) |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | No | Máximo de intentos de login (por defecto: 5) |
| `LOGIN_RATE_LIMIT_WINDOW_MINUTES` | No | Ventana de login en minutos (por defecto: 15) |

---

## 🧪 Verificación y Pruebas

### Endpoints de Health Check

```powershell
# DEV
curl http://localhost:8000/health

# PRE
curl https://myfi-app-backend.onrender.com/health

# PRO (cuando esté desplegado)
curl https://YOUR_CLOUD_RUN_URL/health
```

### Verificación de Detección de Entorno

Comprobar los logs de la aplicación al arrancar:
```
INFO:app.main:====================================================
INFO:app.main:Iniciando Finanzas Personal API v1.0.0
INFO:app.main:Autenticación: JWT (HS256) con tokens de 30 minutos
INFO:app.main:Rate Limiting: 100 req/60s
INFO:app.main:Directorio de logs: ../logsBackend
INFO:app.main:CORS Origins: ['http://localhost:4200', ...]
INFO:app.main:====================================================
INFO:app.database:Database: Modo development - SSL preferido
```

Para entornos PRE/PRO:
```
INFO:app.database:Database: Modo pre - SSL requerido
INFO:app.main:TrustedHostMiddleware habilitado para pre: ['myfi-app-backend.onrender.com']
```

### Prueba de Conexión a la Base de Datos

```python
# Script de prueba: test_db_connection.py
from app.config import settings
from app.database import engine

print(f"Entorno: {settings.ENVIRONMENT}")
print(f"URL Base de Datos: {settings.DATABASE_URL[:50]}...")  # Primeros 50 caracteres

try:
    with engine.connect() as conn:
        result = conn.execute("SELECT version();")
        version = result.fetchone()[0]
        print(f"✅ ¡Conexión a la base de datos exitosa!")
        print(f"Versión de PostgreSQL: {version}")
except Exception as e:
    print(f"❌ Fallo en la conexión a la base de datos: {e}")
```

---

## 🐛 Resolución de Problemas

### Problema: Entorno detectado incorrectamente

**Síntoma:** La aplicación usa la base de datos o configuración equivocada

**Solución:**
```powershell
# Comprobar la variable de entorno
echo $env:ENVIRONMENT

# Establecer el entorno explícitamente
$env:ENVIRONMENT="development"

# O usar el fichero .env
# Asegurarse de que ENVIRONMENT=development está en el fichero .env
```

### Problema: Fallo en la conexión a la base de datos

**Síntomas:**
- "SSL connection has been closed unexpectedly"
- "Connection refused"
- "Authentication failed"

**Soluciones:**

1. **Comprobar el modo SSL:**
   - DEV: Debe usar `sslmode=prefer` (los logs muestran "SSL preferido")
   - PRE/PRO: Debe usar `sslmode=require` (los logs muestran "SSL requerido")

2. **Verificar la cadena de conexión:**
   ```powershell
   # Probar conexión a Neon
   psql "postgresql://neondb_owner:PASSWORD@ep-jolly-river-a93ithgb.gwc.azure.neon.tech/neondb?sslmode=require"
   ```

3. **Comprobar el tamaño del pool:**
   - Si aparece "too many connections", reducir `DB_POOL_SIZE`
   - Neon nivel gratuito: máximo 100 conexiones compartidas entre todos los clientes

### Problema: Errores CORS en el navegador

**Síntoma:** El frontend no puede conectar con el backend, errores CORS en la consola

**Solución:**

1. **Verificar que `CORS_ORIGINS` coincide exactamente con la URL del frontend:**
   ```bash
   # DEV
   CORS_ORIGINS=http://localhost:4200
   
   # PRE
   CORS_ORIGINS=https://myfi-front.netlify.app
   
   # Nota: ¡Sin barra diagonal al final!
   ```

2. **Comprobar TrustedHostMiddleware:**
   ```bash
   # En PRE/PRO, el dominio del backend debe estar en ALLOWED_HOSTS
   ALLOWED_HOSTS=myfi-app-backend.onrender.com
   ```

3. **Verificar el entorno:**
   - TrustedHostMiddleware solo activo en PRE/PRO
   - Comprobar los logs: "TrustedHostMiddleware habilitado para..."

### Problema: Los secretos no se cargan en Cloud Run

**Síntoma:** La aplicación falla con variables de entorno ausentes

**Solución:**

1. **Verificar que los secretos existen:**
   ```powershell
   gcloud secrets list
   ```

2. **Comprobar los permisos IAM:**
   ```powershell
   gcloud secrets get-iam-policy jwt-secret-key
   # Debe mostrar la cuenta de servicio de Cloud Run con el rol secretAccessor
   ```

3. **Verificar el mapeo de secretos en el despliegue:**
   ```powershell
   gcloud run services describe finanzas-api --region europe-west1
   # Comprobar la sección env para los mapeos de secretos
   ```

### Problema: Rate limiting demasiado agresivo

**Síntoma:** Peticiones legítimas bloqueadas

**Solución:**

Ajustar los límites de tasa en las variables de entorno:
```bash
# Aumentar el rate limit general
RATE_LIMIT_REQUESTS=200
RATE_LIMIT_WINDOW=60

# Aumentar el rate limit de login
LOGIN_RATE_LIMIT_ATTEMPTS=10
LOGIN_RATE_LIMIT_WINDOW_MINUTES=15
```

---

## 📚 Recursos Adicionales

- [Código de Configuración: app/config.py](../app/config.py)
- [Configuración de BD: app/database.py](../app/database.py)
- [Aplicación Principal: app/main.py](../app/main.py)
- [Guía de Despliegue con Docker](DOCKER_DEPLOYMENT.md)
- [Runbook de Render](RUNBOOK_RENDER.md) *(pendiente de crear)*
- [Runbook de GCP Cloud Run](RUNBOOK_GCP.md) *(pendiente de crear)*
- [Auditoría de Seguridad](SECURITY_AUDIT.md)
- [Cumplimiento PSD2](PSD2_COMPLIANCE.md)

---

## 🔄 Lista de Verificación para Migración

Al migrar de la configuración antigua a la nueva:

- [ ] Fase 1: Refactorización de código completada
  - [ ] config.py actualizado con 3 entornos
  - [ ] database.py gestiona el entorno PRE
  - [ ] main.py usa valores configurables
  
- [ ] Fase 2: Ficheros de configuración listos
  - [ ] Plantillas .env creadas
  - [ ] .gitignore actualizado
  - [ ] Documentación completa
  
- [ ] Fase 3: Entorno DEV probado
  - [ ] Backend local arranca correctamente
  - [ ] Conexión a la base de datos funciona
  - [ ] El frontend puede conectar (CORS)
  - [ ] Health check devuelve 200
  
- [ ] Fase 4: Entorno PRE configurado
  - [ ] Variables de entorno de Render establecidas
  - [ ] Auto-despliegue desde `develop` habilitado
  - [ ] Despliegue exitoso
  - [ ] Frontend de Netlify conecta correctamente
  
- [ ] Fase 5: Entorno PRO preparado
  - [ ] Proyecto GCP configurado
  - [ ] Secretos en Secret Manager
  - [ ] Workflows de GitHub Actions listos
  - [ ] Despliegue manual inicial probado

---

**Última Actualización:** 11 de marzo de 2026  
**Mantenido por:** Equipo de Backend