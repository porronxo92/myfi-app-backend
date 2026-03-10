"""
Modelo User - Usuarios del Sistema
===================================

SEGURIDAD (GDPR/PSD2):
- email: EN CLARO (necesario para login con WHERE email = X)
- full_name, profile_picture: Encriptados con AES-256-GCM
- password_hash: Bcrypt (no reversible)
"""

from sqlalchemy import Column, String, Boolean, DateTime, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base
from app.models.encrypted_fields import EncryptedString, EncryptedText


class User(Base):
    """
    Modelo ORM para la tabla 'users'
    
    Representa usuarios del sistema.
    Datos personales (excepto email) están encriptados con AES-256-GCM.
    """
    
    __tablename__ = "users"
    
    __table_args__ = (
        CheckConstraint(
            "email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'",
            name='valid_email_format'
        ),
    )
    
    # ============================================
    # COLUMNAS IDENTIFICADORAS
    # ============================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del usuario"
    )
    
    # Email EN CLARO (necesario para login)
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Email del usuario - EN CLARO para búsqueda de login"
    )
    
    username = Column(
        String(50),
        nullable=True,
        unique=True,
        index=True,
        comment="Nombre de usuario (único, opcional)"
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Hash de la contraseña (bcrypt)"
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Si el usuario está activo"
    )
    
    is_admin = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Si el usuario tiene permisos de administrador"
    )
    
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Última fecha de login"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Fecha de creación"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Fecha de última actualización"
    )
    
    # ============================================
    # COLUMNAS ENCRIPTADAS (AES-256-GCM)
    # ============================================
    
    full_name = Column(
        EncryptedString(100),
        nullable=True,
        comment="Nombre completo - ENCRIPTADO AES-256-GCM"
    )
    
    profile_picture = Column(
        EncryptedText,
        nullable=True,
        comment="Foto de perfil (base64) - ENCRIPTADO AES-256-GCM"
    )
    
    # ============================================
    # RELACIONES
    # ============================================
    
    accounts = relationship(
        "Account",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    investments = relationship(
        "Investment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    budgets = relationship(
        "Budget",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # ============================================
    # MÉTODOS
    # ============================================
    
    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}')>"
    
    def to_dict(self):
        """Convierte el objeto a diccionario (sin password_hash)"""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "has_profile_picture": self.profile_picture is not None
        }
    
    def to_public_dict(self):
        """Diccionario con solo datos públicos"""
        return {
            "id": str(self.id),
            "username": self.username,
            "has_profile_picture": self.profile_picture is not None
        }
    
    @property
    def account_count(self) -> int:
        """Número de cuentas del usuario"""
        return len(self.accounts) if self.accounts else 0
    
    @property
    def investment_count(self) -> int:
        """Número de inversiones del usuario"""
        return len(self.investments) if self.investments else 0
