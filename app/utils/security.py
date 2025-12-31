from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.utils.logger import security_logger, get_logger
from app.utils.jwt import verify_token
from app.database import get_db
from app.models import User
from typing import Dict, Optional
from datetime import datetime, timedelta
import hashlib

logger = get_logger("app.utils.security")

# Bearer token para JWT (opcional, ahora también soportamos cookies)
security = HTTPBearer(auto_error=False)

# Almacenamiento en memoria para rate limiting (en producción usar Redis)
rate_limit_storage: Dict[str, Dict] = {}


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency que valida el token JWT y retorna el usuario autenticado
    
    MIGRACIÓN A COOKIES HTTP-ONLY:
    - Prioridad 1: Buscar token en cookie 'access_token'
    - Prioridad 2: Buscar token en header Authorization (compatibilidad)
    
    Args:
        request: Request object para acceder a cookies
        credentials: Credenciales con el token Bearer (opcional)
        db: Sesión de base de datos
        
    Returns:
        User: Usuario autenticado
        
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    token = None
    
    # Prioridad 1: Intentar obtener token de cookie HTTP-only
    token = request.cookies.get("access_token")
    if token:
        logger.debug("🍪 Token obtenido de cookie HTTP-only")
    
    # Prioridad 2: Intentar obtener token de header Authorization (compatibilidad)
    if not token and credentials:
        token = credentials.credentials
        logger.debug("📋 Token obtenido de header Authorization (legacy)")
    
    # Si no hay token en ningún lado, rechazar
    if not token:
        logger.warning("❌ No se encontró token en cookie ni en header Authorization")
        security_logger.warning("Petición sin token de autenticación")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar y decodificar el token
    payload = verify_token(token)
    if not payload:
        logger.warning(f"❌ Token JWT inválido o expirado. Token (primeros 20 chars): {token[:20]}...")
        security_logger.warning("Token JWT inválido o expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extraer user_id del payload
    user_id: str = payload.get("sub")
    if not user_id:
        security_logger.warning("Token JWT sin user_id")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Buscar el usuario en la base de datos
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        security_logger.warning(f"Usuario no encontrado para user_id: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar que el usuario esté activo
    if not user.is_active:
        security_logger.warning(f"Usuario inactivo intentó acceder: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    logger.debug(f"Usuario autenticado: {user.email}")
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency que verifica que el usuario actual esté activo
    (redundante con get_current_user pero útil para claridad)
    """
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency que verifica que el usuario actual sea administrador
    
    Args:
        current_user: Usuario autenticado
        
    Returns:
        User: Usuario administrador
        
    Raises:
        HTTPException: Si el usuario no es administrador
    """
    if not current_user.is_admin:
        security_logger.warning(f"Usuario no admin intentó acceso restringido: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Se requiere rol de administrador"
        )
    return current_user


def check_rate_limit(request: Request) -> None:
    """
    Implementa rate limiting basado en IP del cliente
    
    Args:
        request: Request de FastAPI
        
    Raises:
        HTTPException: Si se excede el límite de peticiones
    """
    # Identificador único: IP del cliente
    client_id = request.client.host
    current_time = datetime.now()
    
    # Limpiar entradas antiguas
    cleanup_old_entries()
    
    # Inicializar si es la primera petición
    if client_id not in rate_limit_storage:
        rate_limit_storage[client_id] = {
            "requests": [],
            "blocked_until": None
        }
    
    client_data = rate_limit_storage[client_id]
    
    # Verificar si el cliente está bloqueado temporalmente
    if client_data["blocked_until"] and current_time < client_data["blocked_until"]:
        remaining_seconds = (client_data["blocked_until"] - current_time).seconds
        security_logger.warning(f"Cliente bloqueado por rate limit: {client_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiadas peticiones. Reintente en {remaining_seconds} segundos.",
            headers={"Retry-After": str(remaining_seconds)}
        )
    
    # Limpiar peticiones fuera de la ventana de tiempo
    window_start = current_time - timedelta(seconds=settings.RATE_LIMIT_WINDOW)
    client_data["requests"] = [
        req_time for req_time in client_data["requests"] 
        if req_time > window_start
    ]
    
    # Verificar límite
    if len(client_data["requests"]) >= settings.RATE_LIMIT_REQUESTS:
        # Bloquear por 1 minuto
        client_data["blocked_until"] = current_time + timedelta(minutes=1)
        security_logger.warning(
            f"Rate limit excedido para cliente {client_id[:16]}... - "
            f"{len(client_data['requests'])} peticiones en {settings.RATE_LIMIT_WINDOW}s"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Límite de {settings.RATE_LIMIT_REQUESTS} peticiones por {settings.RATE_LIMIT_WINDOW}s excedido.",
            headers={"Retry-After": "60"}
        )
    
    # Registrar petición actual
    client_data["requests"].append(current_time)


def cleanup_old_entries(max_age_minutes: int = 10):
    """
    Limpia entradas antiguas del almacenamiento de rate limiting.
    
    Args:
        max_age_minutes: Edad máxima en minutos para mantener entradas
    """
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(minutes=max_age_minutes)
    
    # Eliminar clientes sin actividad reciente
    clients_to_remove = []
    for client_id, data in rate_limit_storage.items():
        if data["requests"]:
            last_request = max(data["requests"])
            if last_request < cutoff_time:
                clients_to_remove.append(client_id)
        elif not data["blocked_until"] or data["blocked_until"] < current_time:
            clients_to_remove.append(client_id)
    
    for client_id in clients_to_remove:
        del rate_limit_storage[client_id]


def get_client_identifier(request: Request, api_key: str = None) -> str:
    """
    Genera un identificador único para el cliente basado en API Key o IP.
    
    Args:
        request: Request de FastAPI
        api_key: API Key si está disponible
        
    Returns:
        str: Hash del identificador del cliente
    """
    if api_key:
        identifier = f"key:{api_key}"
    else:
        # Usar IP y User-Agent para mejor identificación
        ip = request.client.host
        user_agent = request.headers.get("user-agent", "unknown")
        identifier = f"ip:{ip}:{user_agent}"
    
    # Generar hash para proteger información sensible
    return hashlib.sha256(identifier.encode()).hexdigest()[:16]
