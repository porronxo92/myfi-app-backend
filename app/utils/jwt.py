"""
Utilidades para manejo de tokens JWT (Access y Refresh)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from uuid import UUID

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Configuración JWT Access Tokens
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

# Configuración Refresh Tokens
REFRESH_SECRET_KEY = settings.REFRESH_TOKEN_SECRET_KEY
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crear un token JWT de acceso (corta duración)
    
    Args:
        data: Datos a incluir en el token (debe contener 'sub' con el user_id)
        expires_delta: Tiempo de expiración personalizado
    
    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()
    
    # CRÍTICO: Usar datetime.now(timezone.utc) para evitar problemas de timezone
    # Sin timezone.utc, el token nace expirado en zonas horarias diferentes a UTC
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    # Convertir UUID a string si existe
    if "sub" in to_encode and isinstance(to_encode["sub"], UUID):
        to_encode["sub"] = str(to_encode["sub"])
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Access token creado. Expira en: {expire}")
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Crear un refresh token JWT (larga duración)
    
    Args:
        data: Datos a incluir (debe contener 'sub' con el user_id)
    
    Returns:
        Refresh token JWT codificado
    """
    to_encode = data.copy()
    # Usar datetime con timezone UTC (aware datetime)
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    # Convertir UUID a string si existe
    if "sub" in to_encode and isinstance(to_encode["sub"], UUID):
        to_encode["sub"] = str(to_encode["sub"])
    
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Refresh token creado. Expira en: {expire}")
    
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verificar y decodificar un access token JWT
    
    Args:
        token: Token JWT a verificar
    
    Returns:
        Payload del token si es válido, None si no es válido
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None:
            logger.warning("Token JWT no contiene 'sub' (user_id)")
            return None
        
        if token_type != "access":
            logger.warning(f"Token no es de tipo access: {token_type}")
            return None
        
        logger.info(f"✅ Access token válido para user_id: {user_id}")
        return payload
        
    except JWTError as e:
        logger.warning(f"❌ Error al verificar token JWT: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al verificar token: {e}")
        return None


def verify_refresh_token(token: str) -> Optional[dict]:
    """
    Verificar y decodificar un refresh token JWT
    
    Args:
        token: Refresh token JWT a verificar
    
    Returns:
        Payload del token si es válido, None si no es válido
    """
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None:
            logger.warning("Refresh token no contiene 'sub' (user_id)")
            return None
        
        if token_type != "refresh":
            logger.warning(f"Token no es de tipo refresh: {token_type}")
            return None
        
        logger.debug(f"Refresh token válido para user_id: {user_id}")
        return payload
        
    except JWTError as e:
        logger.warning(f"Error al verificar refresh token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al verificar refresh token: {e}")
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extraer el user_id de un token JWT
    
    Args:
        token: Token JWT
    
    Returns:
        user_id como string si el token es válido, None si no
    """
    payload = verify_token(token)
    if payload:
        return payload.get("sub")
    return None
