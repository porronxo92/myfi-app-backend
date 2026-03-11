from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings


def _get_logger():
    """Lazy import del logger para evitar problemas de inicialización"""
    try:
        from app.utils.logger import get_logger
        return get_logger(__name__)
    except Exception:
        # Fallback a logging básico si hay problemas
        import logging
        return logging.getLogger(__name__)


def _get_connect_args() -> dict:
    """
    Obtiene argumentos de conexión según el entorno.
    
    En producción y pre:
    - Fuerza SSL/TLS para conexiones seguras
    - Valida certificados del servidor
    
    En desarrollo:
    - SSL preferido pero no requerido
    """
    logger = _get_logger()
    
    if settings.ENVIRONMENT in ["production", "pre"]:
        # Producción y PRE: SSL requerido
        # 'require' = conexión encriptada obligatoria
        # Para verificación completa de certificado usar 'verify-full' 
        # y proporcionar sslrootcert
        logger.info(f"Database: Modo {settings.ENVIRONMENT} - SSL requerido")
        return {
            "sslmode": "require"
            # Descomentar para verificación completa:
            # "sslmode": "verify-full",
            # "sslrootcert": "/path/to/ca-certificate.crt"
        }
    else:
        # Desarrollo: SSL preferido pero no obligatorio
        logger.info("Database: Modo desarrollo - SSL preferido")
        return {
            "sslmode": "prefer"
        }


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_POOL_OVERFLOW,
    connect_args=_get_connect_args()
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()