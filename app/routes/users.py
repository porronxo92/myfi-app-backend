"""
Endpoints REST para gestión de usuarios
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import math
import base64

from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserLogin, PasswordChange, TokenResponse, RefreshTokenRequest, UpdateUserProfile, ProfilePictureUpdate, ForgotPasswordRequest, ForgotPasswordResponse, VerifyResetTokenResponse, ResetPasswordRequest, ResetPasswordResponse
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


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener perfil del usuario actual
    
    Response: UserResponse con todos los datos del usuario
    """
    logger.info(f"GET /api/users/me - Usuario: {current_user.email}")
    
    # Refrescar datos desde la BD
    user = UserService.get_by_id(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return user


@router.get("/me/gemini-quota")
async def get_gemini_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene la cuota de Gemini AI del usuario actual.

    Retorna información sobre el uso de la API de Gemini:
    - used: Peticiones usadas hoy
    - remaining: Peticiones restantes hoy
    - limit: Límite diario configurado
    - reset_date: Fecha del próximo reset (mañana)
    - percentage_used: Porcentaje de cuota usada

    Response:
    ```json
    {
      "used": 5,
      "remaining": 15,
      "limit": 20,
      "reset_date": "2026-04-02",
      "percentage_used": 25.0
    }
    ```

    La cuota se restablece automáticamente cada día a medianoche.
    """
    from app.services.gemini_quota_service import GeminiQuotaService
    from app.schemas.gemini_quota import GeminiQuotaResponse
    from datetime import date, timedelta

    logger.info(f"GET /api/users/me/gemini-quota - Usuario: {current_user.email}")

    quota_service = GeminiQuotaService(db)
    used, remaining, limit = quota_service.get_remaining(current_user.id)

    tomorrow = date.today() + timedelta(days=1)
    percentage = (used / limit * 100) if limit > 0 else 0

    return GeminiQuotaResponse(
        used=used,
        remaining=remaining,
        limit=limit,
        reset_date=tomorrow,
        percentage_used=round(percentage, 1)
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    profile_data: UpdateUserProfile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Actualizar perfil del usuario actual
    
    Request:
    ```json
    {
      "email": "nuevo@example.com",
      "username": "nuevo_username",
      "full_name": "Nuevo Nombre"
    }
    ```
    
    Response: UserResponse actualizado
    """
    try:
        logger.info(f"PUT /api/users/me - Usuario: {current_user.email}")
        
        # Convertir UpdateUserProfile a UserUpdate
        user_update = UserUpdate(**profile_data.model_dump(exclude_unset=True))
        
        user = UserService.update(db, current_user.id, user_update)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return user
    except ValueError as e:
        logger.error(f"Error al actualizar perfil: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error inesperado al actualizar perfil: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/me/profile-picture", response_model=UserResponse)
async def update_profile_picture(
    picture_data: ProfilePictureUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Actualizar foto de perfil del usuario actual
    
    ⚠️ IMPORTANTE: La imagen debe enviarse en el body JSON, NO en query parameters.
    Los query parameters tienen límite de tamaño y causan error 431 con imágenes grandes.
    
    Request Body (JSON):
    ```json
    {
      "profile_picture": "data:image/jpeg;base64,/9j/4AAQ..."
    }
    ```
    o solo base64:
    ```json
    {
      "profile_picture": "/9j/4AAQ..."
    }
    ```
    
    El backend extrae el base64 automáticamente y lo almacena encriptado.
    """
    try:
        logger.info(f"PUT /api/users/me/profile-picture - Usuario: {current_user.email}")
        
        base64_data = picture_data.profile_picture.strip()
        logger.info(f"Imagen recibida via body JSON (tamaño: {len(base64_data)} chars)")
        
        # Si viene como data URL (data:image/jpeg;base64,...), extraer solo el base64
        if base64_data.startswith("data:"):
            try:
                # Formato: data:image/jpeg;base64,<base64_string>
                base64_data = base64_data.split(",", 1)[1]
                logger.info("Data URL detectada, extrayendo base64")
            except IndexError:
                raise HTTPException(status_code=400, detail="Formato de data URL inválido")
        
        # Validar que es base64 válido
        try:
            base64.b64decode(base64_data, validate=True)
        except Exception as e:
            logger.error(f"Base64 inválido: {e}")
            raise HTTPException(status_code=400, detail="El campo profile_picture no contiene base64 válido")
        
        # Actualizar usuario con el base64
        user_update = UserUpdate(profile_picture=base64_data)
        user = UserService.update(db, current_user.id, user_update)
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        logger.info(f"Foto de perfil actualizada para usuario {current_user.email}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al actualizar foto de perfil: {e}")
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
    
    NOTA: Los tokens se devuelven en el body JSON para almacenarlos en localStorage
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
    
    logger.info(f"Login exitoso para {user.email} - Tokens en body JSON")
    
    # Devolver tokens en el body JSON para almacenarlos en localStorage
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_data: RefreshTokenRequest,
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
    
    NOTA: El refresh_token se envía en el body del request desde localStorage
    """
    logger.info("POST /api/users/refresh - Renovando access token")
    
    if not refresh_data or not refresh_data.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar refresh token
    payload = verify_refresh_token(refresh_data.refresh_token)
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
    
    logger.info(f"Tokens renovados para usuario: {user.email} - Tokens en body JSON")
    
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
    current_user: User = Depends(get_current_user)
):
    """
    Cerrar sesión
    
    El frontend se encarga de limpiar localStorage.
    Este endpoint solo confirma el cierre de sesión.
    
    Response:
    ```json
    {
      "message": "Sesión cerrada correctamente"
    }
    ```
    """
    logger.info(f"POST /api/users/logout - Usuario: {current_user.id}")
    
    return {"message": "Sesión cerrada correctamente"}


# ============================================
# RECUPERACIÓN DE CONTRASEÑA
# ============================================

@router.post("/forgot-password", response_model=ForgotPasswordResponse, status_code=status.HTTP_200_OK)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Solicitar restablecimiento de contraseña

    Envía un email con un enlace para restablecer la contraseña.
    Por seguridad, siempre retorna 200 OK (no revela si el email existe).

    Request:
    ```json
    {
      "email": "usuario@example.com"
    }
    ```

    Response:
    ```json
    {
      "message": "Si el email existe en nuestro sistema, recibirás un enlace para restablecer tu contraseña."
    }
    ```
    """
    from app.services.email_service import email_service

    logger.info(f"POST /api/users/forgot-password - Email: {data.email[:3]}***")

    # Intentar crear token (solo si el usuario existe)
    result = UserService.create_password_reset_token(db, data.email)

    if result:
        plain_token, user = result
        # Enviar email en background (no bloquear respuesta)
        try:
            await email_service.send_password_reset_email(
                to=user.email,
                reset_token=plain_token,
                user_name=user.full_name
            )
        except Exception as e:
            # Log error pero no falla la respuesta
            logger.error(f"Error al enviar email de reset: {e}")

    # Siempre retornamos el mismo mensaje por seguridad
    return ForgotPasswordResponse()


@router.get("/verify-reset-token", response_model=VerifyResetTokenResponse)
async def verify_reset_token(
    token: str,
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Verificar si un token de reset es válido

    El frontend usa esto para mostrar el formulario de nueva contraseña
    o un mensaje de error si el token es inválido/expirado.

    Query params:
    - token: Token recibido por email

    Response (token válido):
    ```json
    {
      "valid": true,
      "email": "u***@example.com"
    }
    ```

    Response (token inválido):
    ```json
    {
      "valid": false,
      "email": null
    }
    ```
    """
    logger.info(f"GET /api/users/verify-reset-token")

    result = UserService.verify_password_reset_token(db, token)

    if not result:
        return VerifyResetTokenResponse(valid=False, email=None)

    is_valid, masked_email, _ = result

    return VerifyResetTokenResponse(
        valid=is_valid,
        email=masked_email if is_valid else None
    )


@router.post("/reset-password", response_model=ResetPasswordResponse, status_code=status.HTTP_200_OK)
async def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Restablecer contraseña con token válido

    Request:
    ```json
    {
      "token": "abc123...",
      "new_password": "NewPassword456!"
    }
    ```

    Response (éxito):
    ```json
    {
      "message": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."
    }
    ```

    Errores:
    - 400: Token inválido, expirado o ya usado
    - 400: Nueva contraseña no cumple requisitos
    """
    logger.info("POST /api/users/reset-password")

    try:
        UserService.reset_password_with_token(db, data.token, data.new_password)
        return ResetPasswordResponse()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al resetear contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


# ============================================
# GDPR - DERECHO AL OLVIDO (Art. 17)
# ============================================

@router.delete("/me/data", status_code=status.HTTP_202_ACCEPTED)
async def request_data_deletion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Solicitar eliminación de todos los datos del usuario (GDPR Art. 17 - Derecho al Olvido)
    
    Este endpoint:
    1. Anonimiza los datos del usuario inmediatamente
    2. Desactiva la cuenta
    3. Los datos asociados (cuentas, transacciones, inversiones) quedan huérfanos
       y serán eliminados en el proceso de limpieza programado
    
    **IMPORTANTE**: Esta acción es IRREVERSIBLE.
    
    Response:
    ```json
    {
      "message": "Solicitud de eliminación recibida. Datos anonimizados.",
      "anonymized_at": "2026-02-11T10:30:00Z",
      "user_id": "550e8400-****-****-****-4466****"
    }
    ```
    """
    from datetime import datetime, timezone
    import uuid as uuid_module
    
    logger.info(f"DELETE /api/users/me/data - Solicitud GDPR de usuario: {current_user.id}")
    
    try:
        # Generar identificador único para usuario anonimizado
        anon_id = str(uuid_module.uuid4())[:8]
        
        # Anonimizar datos del usuario
        original_user_id = str(current_user.id)
        current_user.email = f"deleted_{anon_id}@anonymized.local"
        current_user.username = None
        current_user.full_name = "Usuario Eliminado"
        current_user.profile_picture = None
        current_user.is_active = False
        
        # Registrar timestamp de anonimización
        anonymized_at = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info(f"GDPR: Datos anonimizados para usuario (ID parcial: {original_user_id[:8]}...)")
        
        return {
            "message": "Solicitud de eliminación recibida. Datos anonimizados.",
            "anonymized_at": anonymized_at.isoformat(),
            "info": "Tu cuenta ha sido desactivada y tus datos personales han sido anonimizados. "
                    "Los datos financieros asociados serán eliminados permanentemente en el próximo ciclo de limpieza."
        }
        
    except Exception as e:
        logger.error(f"Error al procesar solicitud GDPR: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar la solicitud de eliminación. Por favor, contacta soporte."
        )


@router.get("/me/export", status_code=status.HTTP_200_OK)
async def export_user_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Exportar todos los datos del usuario (GDPR Art. 20 - Derecho a la Portabilidad)
    
    Retorna todos los datos del usuario en formato JSON estructurado.
    
    Response: JSON con todos los datos del usuario
    """
    from app.services.account_service import AccountService
    from app.services.transaction_service import TransactionService
    from app.services.investment_service import investment_service
    
    logger.info(f"GET /api/users/me/export - Exportación GDPR para usuario: {current_user.id}")
    
    try:
        # Obtener todas las cuentas del usuario
        accounts = AccountService.get_all(db, user_id=current_user.id, limit=1000)
        
        # Obtener todas las transacciones
        transactions = TransactionService.get_all(db, user_id=current_user.id, limit=10000)
        
        # Obtener inversiones
        investments = investment_service.get_all(db, user_id=current_user.id, limit=1000)
        
        # Construir respuesta
        export_data = {
            "export_info": {
                "generated_at": datetime.now().isoformat(),
                "format_version": "1.0",
                "user_id": str(current_user.id)
            },
            "user_profile": {
                "email": current_user.email,
                "username": current_user.username,
                "full_name": current_user.full_name,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                "last_login": current_user.last_login.isoformat() if current_user.last_login else None
            },
            "accounts": [
                {
                    "id": str(acc.id),
                    "name": acc.name,
                    "type": acc.type,
                    "balance": float(acc.balance) if acc.balance else 0,
                    "currency": acc.currency,
                    "bank_name": acc.bank_name,
                    "created_at": acc.created_at.isoformat() if acc.created_at else None
                }
                for acc in accounts
            ],
            "transactions": [
                {
                    "id": str(tx.id),
                    "date": tx.date.isoformat() if tx.date else None,
                    "amount": float(tx.amount) if tx.amount else 0,
                    "description": tx.description,
                    "type": tx.type,
                    "category": tx.category.name if tx.category else None,
                    "account": tx.account.name if tx.account else None,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None
                }
                for tx in transactions
            ],
            "investments": [
                {
                    "id": str(inv.id),
                    "symbol": inv.symbol,
                    "name": inv.name,
                    "shares": float(inv.shares) if inv.shares else 0,
                    "purchase_price": float(inv.purchase_price) if inv.purchase_price else 0,
                    "purchase_date": inv.purchase_date.isoformat() if inv.purchase_date else None
                }
                for inv in investments
            ],
            "total_records": {
                "accounts": len(accounts),
                "transactions": len(transactions),
                "investments": len(investments)
            }
        }
        
        logger.info(f"GDPR Export completado: {len(accounts)} cuentas, {len(transactions)} transacciones, {len(investments)} inversiones")
        
        return export_data
        
    except Exception as e:
        logger.error(f"Error al exportar datos GDPR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al exportar datos. Por favor, intenta de nuevo."
        )

