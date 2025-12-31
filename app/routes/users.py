"""
Endpoints REST para gestión de usuarios
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import math
import os

from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserLogin, PasswordChange, TokenResponse, RefreshTokenRequest
from app.schemas.pagination import PaginatedResponse
from app.services.user_service import UserService
from app.models.user import User
from app.utils.logger import get_logger
from app.utils.security import get_current_user, get_current_admin_user, check_rate_limit
from app.utils.jwt import create_access_token, create_refresh_token, verify_refresh_token
from app.config import settings
from fastapi import Request
from datetime import datetime, timedelta
from typing import Dict

logger = get_logger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])

# Almacenamiento en memoria para intentos de login fallidos
# PRODUCCIÓN: Usar Redis para compartir entre instancias
login_attempts: Dict[str, Dict] = {}


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Crear nuevo usuario (registro público)
    
    Request:
    ```json
    {
      "email": "usuario@example.com",
      "username": "usuario123",
      "password": "Password123!",
      "full_name": "Juan Pérez"
    }
    ```
    
    Response: UserResponse (sin password_hash)
    """
    try:
        logger.info(f"POST /api/users - Creando usuario: {user.email}")
        new_user = UserService.create(db, user)
        return new_user
    except ValueError as e:
        logger.error(f"Error al crear usuario: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error inesperado al crear usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/", response_model=PaginatedResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Listar usuarios con paginación
    
    Query params:
    - page: Número de página (default: 1)
    - page_size: Elementos por página (default: 20)
    - is_active: Filtrar por estado activo (true/false)
    
    Response:
    ```json
    {
      "items": [UserResponse],
      "total": 50,
      "page": 1,
      "page_size": 20,
      "total_pages": 3
    }
    ```
    """
    logger.info(f"GET /api/users - page={page}, page_size={page_size}, is_active={is_active}")
    
    skip = (page - 1) * page_size
    
    users = UserService.get_all(db, skip=skip, limit=page_size, is_active=is_active)
    total = UserService.get_total_count(db, is_active=is_active)
    
    return PaginatedResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener usuario por ID
    
    Response: UserResponse (sin password_hash)
    """
    logger.info(f"GET /api/users/{user_id}")
    
    # Solo admin puede ver otros usuarios, usuarios regulares solo su propio perfil
    if not current_user.is_admin and str(current_user.id) != str(user_id):
        raise HTTPException(status_code=403, detail="No tiene permiso para ver este usuario")
    
    user = UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Actualizar usuario
    
    Request:
    ```json
    {
      "full_name": "Juan Pérez García",
      "is_active": true
    }
    ```
    
    Response: UserResponse actualizado
    """
    try:
        logger.info(f"PUT /api/users/{user_id}")
        
        # Solo admin puede actualizar otros usuarios, usuarios regulares solo su propio perfil
        if not current_user.is_admin and str(current_user.id) != str(user_id):
            raise HTTPException(status_code=403, detail="No tiene permiso para actualizar este usuario")
        
        user = UserService.update(db, user_id, user_data)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return user
    except ValueError as e:
        logger.error(f"Error al actualizar usuario: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error inesperado al actualizar usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Eliminar usuario (también elimina sus cuentas)
    
    Response: 204 No Content
    """
    logger.info(f"DELETE /api/users/{user_id}")
    
    if not UserService.delete(db, user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return None


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Autenticar usuario y obtener token JWT
    
    Protección Brute Force:
    - Máximo 5 intentos fallidos
    - Bloqueo de 15 minutos tras exceder el límite
    
    Request:
    ```json
    {
      "email": "usuario@example.com",
      "password": "Password123!"
    }
    ```
    
    Response:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIs...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
      "token_type": "bearer",
      "expires_in": 1800,
      "user": {...}
    }
    ```
    
    NOTA: Este endpoint NO requiere autenticación
    """
    # Identificador único: IP + Email
    client_id = f"{request.client.host}:{credentials.email}"
    current_time = datetime.now()
    
    # Verificar si el cliente está bloqueado
    if client_id in login_attempts:
        attempt_data = login_attempts[client_id]
        
        # Verificar bloqueo temporal
        if attempt_data.get("locked_until") and current_time < attempt_data["locked_until"]:
            remaining_seconds = int((attempt_data["locked_until"] - current_time).total_seconds())
            logger.warning(f"Login bloqueado para {credentials.email} desde IP {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos fallidos. Bloqueado por {remaining_seconds} segundos.",
                headers={"Retry-After": str(remaining_seconds)}
            )
    
    logger.info(f"POST /api/users/login - email: {credentials.email}")
    
    # Autenticar usuario
    user = UserService.authenticate(db, credentials.email, credentials.password)
    
    if not user:
        # Incrementar contador de intentos fallidos
        if client_id not in login_attempts:
            login_attempts[client_id] = {"count": 0, "locked_until": None}
        
        login_attempts[client_id]["count"] += 1
        attempts_left = settings.LOGIN_RATE_LIMIT_ATTEMPTS - login_attempts[client_id]["count"]
        
        # Bloquear si excede el límite
        if login_attempts[client_id]["count"] >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
            login_attempts[client_id]["locked_until"] = current_time + timedelta(
                minutes=settings.LOGIN_RATE_LIMIT_WINDOW_MINUTES
            )
            logger.warning(
                f"Cliente bloqueado por intentos fallidos: {credentials.email} desde {request.client.host}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos fallidos. Bloqueado por {settings.LOGIN_RATE_LIMIT_WINDOW_MINUTES} minutos."
            )
        
        logger.warning(f"Login fallido para {credentials.email}. Intentos restantes: {attempts_left}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Email o contraseña incorrectos. Intentos restantes: {attempts_left}"
        )
    
    # Login exitoso - resetear contador
    if client_id in login_attempts:
        del login_attempts[client_id]
    
    # Crear tokens JWT
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # NO usar cookies en producción cross-domain (diferentes dominios)
    # Las cookies HTTP-only no funcionan entre dominios diferentes
    # Solo usar cookies en localhost donde frontend y backend están en el mismo dominio
    is_localhost = os.getenv("ENVIRONMENT", "development") != "production"
    
    if is_localhost:
        # Configurar cookies HTTP-only SOLO en localhost
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # HTTP en localhost
            samesite="lax",
            max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
            domain=None
        )
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
            domain=None
        )
        logger.info(f"Login exitoso para {user.email} - Cookies establecidas (localhost)")
    else:
        logger.info(f"Login exitoso para {user.email} - Tokens en body JSON (producción)")
    
    # Devolver tokens en el body JSON para producción cross-domain
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    refresh_data: RefreshTokenRequest = None,
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Renovar access token usando refresh token
    
    Request:
    ```json
    {
      "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
    }
    ```
    
    Response:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIs...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
      "token_type": "bearer",
      "expires_in": 1800,
      "user": {...}
    }
    ```
    
    NOTA: Este endpoint NO requiere autenticación
    """
    logger.info("POST /api/users/refresh - Renovando access token")
    
    # Intentar obtener refresh_token de cookie primero, luego del body
    refresh_token_value = request.cookies.get("refresh_token")
    
    if not refresh_token_value and refresh_data:
        refresh_token_value = refresh_data.refresh_token
    
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar refresh token
    payload = verify_refresh_token(refresh_token_value)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener user_id del payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido"
        )
    
    # Verificar que el usuario existe y está activo
    user = UserService.get_by_id(db, UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    # Crear nuevos tokens
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # NO usar cookies en producción cross-domain
    is_localhost = os.getenv("ENVIRONMENT", "development") != "production"
    
    if is_localhost:
        # Actualizar cookies SOLO en localhost
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
            domain=None
        )
        
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
            domain=None
        )
        logger.info(f"Tokens renovados para usuario: {user.email} - Cookies actualizadas (localhost)")
    else:
        logger.info(f"Tokens renovados para usuario: {user.email} - Tokens en body JSON (producción)")
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Cambiar contraseña de usuario autenticado
    
    Request:
    ```json
    {
      "current_password": "OldPassword123!",
      "new_password": "NewPassword456!"
    }
    ```
    
    Response:
    ```json
    {
      "message": "Contraseña actualizada correctamente"
    }
    ```
    """
    try:
        logger.info(f"POST /api/users/change-password - Usuario: {current_user.email}")
        
        success = UserService.change_password(db, current_user.id, password_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta"
            )
        
        return {"message": "Contraseña actualizada correctamente"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error al cambiar contraseña: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    Cerrar sesión y limpiar cookies HTTP-only
    
    Este endpoint elimina las cookies de autenticación del navegador
    estableciendo su valor vacío y max_age=0
    
    Response:
    ```json
    {
      "message": "Sesión cerrada correctamente"
    }
    ```
    """
    logger.info(f"POST /api/users/logout - Usuario: {current_user.email}")
    
    # Limpiar cookies estableciendo valores vacíos y max_age=0
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=None
    )
    
    response.delete_cookie(
        key="refresh_token",
        path="/",
        domain=None
    )
    
    logger.info(f"Sesión cerrada para {current_user.email} - Cookies eliminadas")
    
    return {"message": "Sesión cerrada correctamente"}
