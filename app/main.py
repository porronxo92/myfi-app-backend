from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.config import settings
from app.routes import upload, accounts, categories, transactions, users, analytics, insights, health, investments, budgets
from app.utils.security import check_rate_limit
from app.utils.logger import app_logger, access_logger, error_logger, get_logger
import time

# Logger para main
logger = get_logger("app.main")

app = FastAPI(
    title="Finanzas Personal API",
    description="API para gestión de finanzas personales con ingesta inteligente",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Log de inicio de aplicación
logger.info("=" * 60)
logger.info("Iniciando Finanzas Personal API v1.0.0")
logger.info(f"Autenticación: JWT (HS256) con tokens de {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES} minutos")
logger.info(f"Rate Limiting: {settings.RATE_LIMIT_REQUESTS} req/{settings.RATE_LIMIT_WINDOW}s")
logger.info(f"Directorio de logs: {settings.LOGS_DIR}")
logger.info(f"CORS Origins: {settings.CORS_ORIGINS}")
logger.info("=" * 60)

# CORS Configuration (debe estar ANTES de otros middlewares)
# CRÍTICO: allow_credentials=True permite enviar/recibir cookies HTTP-only
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,  # ← Permite cookies HTTP-only
    allow_methods=["*"],      # Permitir todos los métodos HTTP
    allow_headers=["*"],      # Permitir todos los headers
    expose_headers=[
        "Set-Cookie",
        "Authorization",
        "X-Process-Time",
        "Access-Control-Allow-Credentials",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Origin",
    ],
    max_age=3600,  # Cache de CORS por 1 hora
)

# Security Middleware - Trusted Host (previene ataques Host Header)
# Temporalmente deshabilitado para debugging CORS
# app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
# )


# Middleware para logging de peticiones
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log de petición entrante (access log)
    access_logger.info(
        f"{request.client.host} - {request.method} {request.url.path} "
        f"UserAgent: {request.headers.get('user-agent', 'Unknown')}"
    )
    
    try:
        response = await call_next(request)
        
        # Log de respuesta
        process_time = time.time() - start_time
        
        log_message = (
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        # Diferentes niveles según status code
        if response.status_code >= 500:
            error_logger.error(log_message)
        elif response.status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Añadir headers de seguridad
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Usar SAMEORIGIN en lugar de DENY para permitir CORS desde origins permitidos
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # No usar Strict-Transport-Security en desarrollo (localhost)
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Process-Time"] = str(process_time)
        
        # Asegurarse de que los headers CORS están presentes
        if "Access-Control-Allow-Origin" not in response.headers:
            origin = request.headers.get("origin")
            if origin and origin in settings.CORS_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        error_logger.error(
            f"ERROR en {request.method} {request.url.path} - "
            f"Time: {process_time:.3f}s - Exception: {str(e)}",
            exc_info=True
        )
        raise


# Routes
app.include_router(users.router, tags=["users"])
app.include_router(accounts.router, tags=["accounts"])
app.include_router(categories.router, tags=["categories"])
app.include_router(transactions.router, tags=["transactions"])
app.include_router(upload.router, tags=["upload & import"])
app.include_router(analytics.router, tags=["analytics"])
app.include_router(insights.router, tags=["insights"])
app.include_router(health.router, tags=["health"])
app.include_router(investments.router, tags=["investments"])
app.include_router(budgets.router, tags=["budgets"])


@app.get("/")
async def root():
    """Endpoint público sin autenticación"""
    logger.info("Acceso al endpoint raíz")
    return {
        "message": "Finanzas Personal API",
        "version": "1.0.0",
        "docs": "/docs",
        "authentication": "JWT (Bearer Token)"
    } 


@app.get("/health")
async def health_check():
    """Endpoint público de salud sin autenticación"""
    return {
        "status": "healthy",
        "database": "connected",
        "llm_provider": settings.LLM_PROVIDER,
        "authentication": "JWT"
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor Uvicorn...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
