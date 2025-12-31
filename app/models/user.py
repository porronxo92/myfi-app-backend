from sqlalchemy import Column, String, Boolean, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

class User(Base):
    """
    Modelo ORM para la tabla 'users'
    
    Representa usuarios del sistema
    """
    
    __tablename__ = "users"
    
    __table_args__ = (
        CheckConstraint(
            "email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'",
            name='valid_email_format'
        ),
    )
    
    # ============================================
    # COLUMNAS
    # ============================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del usuario"
    )
    
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Email del usuario (único)"
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
    
    full_name = Column(
        String(100),
        nullable=True,
        comment="Nombre completo del usuario"
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
    # RELACIONES
    # ============================================
    
    accounts = relationship(
        "Account",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    # Un usuario tiene muchas cuentas
    # Si borras el usuario, se borran sus cuentas
    
    # ============================================
    # MÉTODOS
    # ============================================
    
    def __repr__(self):
        return f"<User(email='{self.email}', username='{self.username}')>"
    
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
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def account_count(self):
        """Número de cuentas del usuario"""
        return len(self.accounts)
