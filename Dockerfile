# =============================================================
# Dockerfile para FastAPI Backend - Optimizado para Cloud Run
# =============================================================
# Imagen: python:3.12-slim (Debian-based, compatible con deps C)
# Puerto: 8080 (obligatorio Cloud Run)
# Servidor: Uvicorn con múltiples workers
# =============================================================

# ---- Etapa única: producción ----
FROM python:3.12-slim

# Metadatos de la imagen
LABEL maintainer="DevOps Team"
LABEL description="FastAPI Backend - Finanzas Personal API"
LABEL version="1.0.0"

# Variables de entorno para optimización de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Puerto obligatorio para Cloud Run
    PORT=8080 \
    # Directorio de trabajo
    APP_HOME=/app

# Establecer directorio de trabajo
WORKDIR ${APP_HOME}

# Instalar dependencias del sistema necesarias
# - libmagic1: requerido por python-magic (detección MIME types)
# - curl: para health checks
# - --no-install-recommends: minimiza el tamaño de la imagen
# - rm -rf /var/lib/apt/lists/*: limpia cache apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar SOLO requirements.txt primero (mejor cache de capas Docker)
# Si requirements.txt no cambia, esta capa se reutiliza
COPY requirements.txt .

# Instalar dependencias de Python
# --no-cache-dir: no guardar cache de pip (imagen más ligera)
# --upgrade pip: asegurar última versión de pip
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fuente de la aplicación
# Esto se hace DESPUÉS de instalar deps para aprovechar cache
COPY app/ ./app/

# Crear usuario no-root primero
RUN useradd --create-home --shell /bin/bash appuser

# Crear directorios necesarios y asignar permisos
RUN mkdir -p logs temp_uploads && \
    chown -R appuser:appuser ${APP_HOME} && \
    chmod -R 755 ${APP_HOME}

# Cambiar a usuario no-root
USER appuser

# Exponer puerto (documentación, Cloud Run usa PORT env var)
EXPOSE 8080

# Health check para Docker (opcional, Cloud Run tiene el suyo)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Comando de inicio: Uvicorn con configuración optimizada
# - host 0.0.0.0: escuchar en todas las interfaces
# - port $PORT: usa variable de entorno (Cloud Run la inyecta)
# - workers 2: múltiples workers para concurrencia
# - timeout-keep-alive 30: timeout conexiones keep-alive
# - access-log: logs de acceso habilitados
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2 --timeout-keep-alive 30 --access-log"]
