import re
from pydantic import BaseModel, Field, UUID4, EmailStr, ConfigDict, field_serializer, field_validator
from typing import Optional
from datetime import datetime

# ============================================
# SCHEMA BASE
# ============================================
class UserBase(BaseModel):
    """Campos base del usuario"""
    email: EmailStr = Field(..., description="Email del usuario")
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    profile_picture: Optional[str] = Field(None, description="Base64 de la foto de perfil o URL")

# ============================================
# SCHEMA PARA CREAR (POST)
# ============================================
class UserCreate(UserBase):
    """
    POST /api/users
    
    Request:
    {
      "email": "usuario@example.com",
      "username": "usuario123",
      "password": "Password123!",
      "full_name": "Juan Pérez"
    }
    """
    password: str = Field(..., min_length=8, max_length=100, description="Contraseña (mínimo 8 caracteres)")

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial (!@#$%...)')
        return v

# ============================================
# SCHEMA PARA ACTUALIZAR (PUT)
# ============================================
class UserUpdate(BaseModel):
    """
    PUT /api/users/{id}
    
    Todos los campos opcionales
    
    Request:
    {
      "full_name": "Juan Pérez García",
      "is_active": true
    }
    """
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None

# ============================================
# SCHEMA PARA ACTUALIZAR PERFIL (PUT /api/users/me)
# ============================================
class UpdateUserProfile(BaseModel):
    """
    PUT /api/users/me
    
    Request:
    {
      "email": "nuevo@example.com",
      "username": "nuevo_username",
      "full_name": "Nuevo Nombre"
    }
    """
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)

# ============================================
# SCHEMA PARA LOGIN
# ============================================
class UserLogin(BaseModel):
    """
    POST /api/users/login
    
    Request:
    {
      "email": "usuario@example.com",
      "password": "Password123!"
    }
    """
    email: EmailStr
    password: str

# ============================================
# SCHEMA DE RESPUESTA
# ============================================
class UserResponse(UserBase):
    """
    GET /api/users
    
    Response:
    {
      "id": "uuid",
      "email": "usuario@example.com",
      "username": "usuario123",
      "full_name": "Juan Pérez",
      "is_active": true,
      "is_admin": false,
      "last_login": "2025-12-22T10:30:00",
      "created_at": "2025-01-15T08:00:00",
      "account_count": 3
    }
    
    NOTA: password_hash NO se incluye por seguridad
    """
    id: UUID4
    is_active: bool
    is_admin: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    
    # Estadísticas
    account_count: Optional[int] = 0
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('created_at', 'last_login')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """Convierte datetime a string ISO"""
        return dt.isoformat() if dt else None

# ============================================
# SCHEMA PARA CAMBIO DE CONTRASEÑA
# ============================================
class PasswordChange(BaseModel):
    """
    POST /api/users/{id}/change-password
    
    Request:
    {
      "current_password": "OldPassword123!",
      "new_password": "NewPassword456!"
    }
    """
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def validate_new_password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial (!@#$%...)')
        return v
# ============================================
# SCHEMA PARA RESPUESTA DE LOGIN/TOKEN
# ============================================
class TokenResponse(BaseModel):
    """
    POST /api/users/login
    
    Response:
    {
      "access_token": "eyJhbGciOiJIUzI1NiIs...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
      "token_type": "bearer",
      "expires_in": 1800,
      "user": {
        "id": "uuid",
        "email": "user@example.com",
        ...
      }
    }
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutos en segundos
    user: "UserResponse"

# ============================================
# SCHEMA PARA REFRESH TOKEN
# ============================================
class RefreshTokenRequest(BaseModel):
    """
    POST /api/users/refresh
    
    Request:
    {
      "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
    }
    """
    refresh_token: str

# ============================================
# SCHEMA PARA ACTUALIZAR FOTO DE PERFIL
# ============================================
class ProfilePictureUpdate(BaseModel):
    """
    PUT /api/users/me/profile-picture

    Request:
    {
      "profile_picture": "data:image/jpeg;base64,/9j/4AAQ..."
    }
    o
    {
      "profile_picture": "/9j/4AAQ..."  (solo base64)
    }

    El backend acepta data URL o base64 puro y extrae el base64 automáticamente.
    """
    profile_picture: str = Field(..., description="Imagen en base64 o data URL (data:image/...;base64,...)")


# ============================================
# SCHEMAS PARA RECUPERACIÓN DE CONTRASEÑA
# ============================================

class ForgotPasswordRequest(BaseModel):
    """
    POST /api/users/forgot-password

    Request:
    {
      "email": "usuario@example.com"
    }

    Siempre retorna 200 OK por seguridad (no revela si el email existe)
    """
    email: EmailStr = Field(..., description="Email del usuario")


class ForgotPasswordResponse(BaseModel):
    """
    Response para forgot-password

    Siempre devuelve el mismo mensaje por seguridad
    """
    message: str = Field(
        default="Si el email existe en nuestro sistema, recibirás un enlace para restablecer tu contraseña.",
        description="Mensaje de confirmación"
    )


class VerifyResetTokenResponse(BaseModel):
    """
    GET /api/users/verify-reset-token?token=xxx

    Response:
    {
      "valid": true,
      "email": "u***@example.com"
    }
    """
    valid: bool = Field(..., description="Si el token es válido")
    email: Optional[str] = Field(None, description="Email parcialmente oculto (solo si válido)")


class ResetPasswordRequest(BaseModel):
    """
    POST /api/users/reset-password

    Request:
    {
      "token": "abc123...",
      "new_password": "NewPassword456!"
    }
    """
    token: str = Field(..., description="Token de reset recibido por email")
    new_password: str = Field(..., min_length=8, max_length=100, description="Nueva contraseña")

    @field_validator('new_password')
    @classmethod
    def validate_reset_password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial (!@#$%...)')
        return v


class ResetPasswordResponse(BaseModel):
    """
    Response para reset-password exitoso
    """
    message: str = Field(
        default="Contraseña actualizada correctamente. Ya puedes iniciar sesión.",
        description="Mensaje de confirmación"
    )