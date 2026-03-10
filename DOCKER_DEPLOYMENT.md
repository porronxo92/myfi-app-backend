# 🐳 Guía de Despliegue con Docker

## 📋 Tabla de Contenidos

- [Requisitos](#requisitos)
- [Configuración Inicial](#configuración-inicial)
- [Desarrollo Local](#desarrollo-local)
- [Despliegue en Cloud Run](#despliegue-en-cloud-run)
- [Gestión de Logs](#gestión-de-logs)

---

## Requisitos

- Docker Desktop 24+ (Windows/Mac) o Docker Engine 24+ (Linux)
- Docker Compose 2.0+
- Google Cloud SDK (para despliegue en GCP)
- Python 3.12+ (solo para desarrollo sin Docker)

---

## Configuración Inicial

### 1. Copiar variables de entorno

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux/Mac
cp .env.example .env
```

### 2. Generar secretos de seguridad

```powershell
# JWT Secret Key
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(48))"

# Refresh Token Secret Key
python -c "import secrets; print('REFRESH_TOKEN_SECRET_KEY=' + secrets.token_urlsafe(48))"

# Encryption Master Key
python -c "import secrets; print('ENCRYPTION_MASTER_KEY=' + secrets.token_urlsafe(32))"
```

Copia los valores generados al archivo `.env`.

### 3. Configurar APIs externas

Edita `.env` y añade tus API keys:
- **Gemini AI**: https://makersuite.google.com/app/apikey
- **Finnhub**: https://finnhub.io/register
- **Alpha Vantage**: https://www.alphavantage.co/support/#api-key

---

## Desarrollo Local

### Opción A: Docker Compose (Recomendado)

Incluye PostgreSQL automáticamente:

```powershell
# Construir y levantar servicios
docker-compose up --build

# Ejecutar en segundo plano
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f api

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (⚠️ borra la BD)
docker-compose down -v
```

**URLs disponibles:**
- API: http://localhost:8080/docs
- Health: http://localhost:8080/health
- PostgreSQL: localhost:5433 ← Puerto cambiado para evitar conflictos

> **📋 Schema de BD:** El script `app/bbdd/schema_app_finance.sql` se ejecuta **automáticamente** la primera vez. Ver [DATABASE_INIT.md](DATABASE_INIT.md) para más detalles.

### Opción B: Solo Docker (sin compose)

```powershell
# 1. Construir imagen
docker build -t finanzas-api:latest .

# 2. Ejecutar contenedor
docker run -d --name finanzas-api `
  -p 8080:8080 `
  --env-file .env `
  finanzas-api:latest

# 3. Ver logs
docker logs -f finanzas-api

# 4. Detener y eliminar
docker stop finanzas-api
docker rm finanzas-api
```

### Verificar inicialización de Base de Datos

El schema se aplica **automáticamente** al crear el contenedor. Verifica que se creó correctamente:

```powershell
# Ver tablas creadas
docker-compose exec db psql -U postgres -d app_finance -c "\dt"

# Acceder a PostgreSQL interactivamente
docker-compose exec db psql -U postgres -d app_finance

# Ejecutar migraciones adicionales (si usas Alembic)
docker-compose exec api python -m alembic upgrade head
```

> **📖 Más información:** Ver [DATABASE_INIT.md](DATABASE_INIT.md) para resetear BD, troubleshooting y scripts adicionales.

---

## Despliegue en Cloud Run

### Prerrequisitos

```powershell
# Instalar Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Autenticarse
gcloud auth login

# Configurar proyecto
gcloud config set project TU-PROYECTO-ID
```

### Paso 1: Preparar imagen para Cloud Run

```powershell
# Variables
$PROJECT_ID = "tu-proyecto-gcp"
$REGION = "europe-west1"  # Cambia según tu región
$SERVICE_NAME = "finanzas-api"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Habilitar APIs necesarias
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Construir y subir imagen a Google Container Registry
gcloud builds submit --tag $IMAGE_NAME
```

### Paso 2: Desplegar en Cloud Run

```powershell
# Desplegar servicio
gcloud run deploy $SERVICE_NAME `
  --image $IMAGE_NAME `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --port 8080 `
  --memory 512Mi `
  --cpu 1 `
  --min-instances 0 `
  --max-instances 10 `
  --timeout 300 `
  --set-env-vars "ENVIRONMENT=production" `
  --set-secrets "JWT_SECRET_KEY=jwt-secret:latest,REFRESH_TOKEN_SECRET_KEY=refresh-secret:latest,ENCRYPTION_MASTER_KEY=encryption-key:latest,DATABASE_URL_PROD=db-url:latest"

# Obtener URL del servicio
gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)'
```

### Paso 3: Configurar Secrets en GCP

```powershell
# Crear secrets (ejecutar solo una vez)
echo -n "tu-jwt-secret-aqui" | gcloud secrets create jwt-secret --data-file=-
echo -n "tu-refresh-secret-aqui" | gcloud secrets create refresh-secret --data-file=-
echo -n "tu-encryption-key-aqui" | gcloud secrets create encryption-key --data-file=-
echo -n "postgresql://user:pass@host/db" | gcloud secrets create db-url --data-file=-

# Dar permisos al servicio para acceder a secrets
$PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding jwt-secret `
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

### Paso 4: Configurar dominio personalizado (Cloudflare)

1. **En Cloud Run:**
   ```powershell
   gcloud run domain-mappings create --service $SERVICE_NAME --domain api.tudominio.com --region $REGION
   ```

2. **En Cloudflare DNS:**
   - Tipo: `CNAME`
   - Nombre: `api`
   - Contenido: `ghs.googlehosted.com`
   - Proxy: Activado (naranja)

3. **Configurar SSL full en Cloudflare:**
   - SSL/TLS → Overview → Full (strict)

---

## Gestión de Logs

### En Desarrollo Local (Docker/Compose)

Los logs se guardan en:
- **Archivos**: `./logs/app_finance_YYYYMMDD.log` (rotación diaria, 30 días)
- **Stdout**: Visible con `docker logs` o `docker-compose logs`

```powershell
# Ver logs en tiempo real
docker-compose logs -f api

# Ver últimas 100 líneas
docker logs --tail 100 finanzas-api

# Seguir logs con timestamp
docker logs -f --timestamps finanzas-api
```

### En Cloud Run (Producción)

Los logs van **automáticamente a Google Cloud Logging** (no se usan archivos):

```powershell
# Ver logs en tiempo real desde CLI
gcloud run services logs read $SERVICE_NAME --region $REGION --follow

# Ver logs en Cloud Console
# https://console.cloud.google.com/logs
```

**Filtros útiles en Cloud Logging:**
```
# Ver solo errores
severity >= ERROR

# Filtrar por endpoint
jsonPayload.url="/api/transactions"

# Últimas 24h
timestamp >= "2026-03-09T00:00:00Z"
```

### Arquitectura de Logs

```
┌─────────────────────────┐
│ logger.py (detecta env) │
└───────────┬─────────────┘
            │
     ┌──────▼───────┐
     │ K_SERVICE?   │ (variable de Cloud Run)
     └──────┬───────┘
            │
      ┌─────▼─────┬─────────────┐
      │           │             │
   SI │        NO │             │
      │           │             │
┌─────▼─────┐ ┌──▼──────────┐  │
│  stdout   │ │ archivo +   │  │
│  (Cloud   │ │ stdout      │  │
│  Logging) │ │ (Local Dev) │  │
└───────────┘ └─────────────┘  │
                            stdout siempre
```

---

## Comandos Útiles

```powershell
# Ver tamaño de la imagen
docker images | findstr finanzas-api

# Inspeccionar contenedor
docker inspect finanzas-api

# Ejecutar comando dentro del contenedor
docker exec -it finanzas-api bash

# Limpiar imágenes no usadas
docker system prune -a

# Ver uso de recursos
docker stats finanzas-api

# Reiniciar contenedor
docker restart finanzas-api
```

---

## Troubleshooting

### Error: "Cannot connect to database"

```powershell
# Verificar que PostgreSQL está corriendo
docker-compose ps db

# Ver logs de PostgreSQL
docker-compose logs db

# Probar conexión manual
docker exec -it finanzas-db psql -U postgres -d app_finance
```

### Error: "Port 8080 already in use"

```powershell
# Ver qué proceso usa el puerto
netstat -ano | findstr :8080

# Cambiar puerto en docker-compose.yml
ports:
  - "8081:8080"  # Mapeado a 8081 en local
```

### Logs no aparecen

```powershell
# Verificar nivel de log
docker exec finanzas-api env | findstr LOG_LEVEL

# Forzar logs a stdout
docker run -e LOG_LEVEL=DEBUG finanzas-api:latest
```

---

## Seguridad

✅ **Buenas prácticas implementadas:**
- Usuario no-root en el contenedor
- Secrets via variables de entorno (no hardcoded)
- Certificate pinning para APIs externas (verificar SSL)
- Health checks configurados
- CORS restrictivo por dominio

⚠️ **Antes de producción:**
- [ ] Cambiar todos los secrets del `.env`
- [ ] Configurar Cloud SQL Proxy para PostgreSQL
- [ ] Habilitar Cloud Armor (WAF)
- [ ] Configurar alertas en Cloud Monitoring
- [ ] Revisar permisos IAM del service account

---

## Recursos

- [Cloud Run Docs](https://cloud.google.com/run/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/)
