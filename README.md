# myfi-app-backend

API de finanzas personales construida con FastAPI y PostgreSQL. Expone autenticación JWT (access + refresh), gestión de usuarios, cuentas, categorías, transacciones y carga de extractos bancarios con procesamiento de PDF/Excel.

## Stack

- FastAPI + Uvicorn
- PostgreSQL + SQLAlchemy
- Pydantic v2
- JWT (HS256) con tokens de acceso y refresh
- Logging con rotación y CORS configurables

## Funcionalidades clave

- Autenticación con refresh tokens y rate limiting de login
- CRUD de usuarios, cuentas, categorías y transacciones
- Ingesta de extractos (PDF, XLSX, CSV, TXT) con validación de tamaño/extensiones
- CORS configurable para frontends web
- Health check público y documentación interactiva en `/docs`

## Requisitos

- Python 3.11+
- PostgreSQL 14+

## Configuración rápida

1) Crear entorno y dependencias

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

2) Variables de entorno `.env`

```
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/app_finance
JWT_SECRET_KEY=changeme
REFRESH_TOKEN_SECRET_KEY=changeme
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:4200,http://localhost:3000
GEMINI_API_KEY=opcional-si-se-usa-LLM
LOG_LEVEL=INFO
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
LOGIN_RATE_LIMIT_ATTEMPTS=5
LOGIN_RATE_LIMIT_WINDOW_MINUTES=15
MAX_FILE_SIZE_MB=10
ALLOWED_EXTENSIONS=pdf,xlsx,csv,txt
```

3) Ejecutar servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentación: `http://localhost:8000/docs`

## 🐳 Docker & Despliegue

### Desarrollo local con Docker Compose

```powershell
# Copiar variables de entorno
Copy-Item .env.example .env

# Generar secretos (ver .env.example)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Levantar API + PostgreSQL
docker-compose up -d

# Verificar que el schema se aplicó correctamente
.\verify_db.ps1  # Windows
# O: ./verify_db.sh en Linux/Mac

# Ver logs
docker-compose logs -f api
```

**URLs:**
- API Docs: http://localhost:8080/docs
- Health Check: http://localhost:8080/health
- PostgreSQL: localhost:5433 (user: postgres, pass: postgres)

### Documentación adicional

- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Guía completa de despliegue (local y Cloud Run)
- **[DATABASE_INIT.md](DATABASE_INIT.md)** - Inicialización y gestión del schema de BD
- **[.env.example](.env.example)** - Plantilla de variables de entorno

## Pruebas

```bash
pytest
```

## Notas de producción

- Define secretos fuertes para JWT y refresh tokens.
- Revisa `CORS_ORIGINS` y `TrustedHostMiddleware` antes de exponer el servicio.
- Configura backups y rotación de logs según tu entorno.
