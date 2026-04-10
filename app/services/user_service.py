"""
Servicio de lógica de negocio para User
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone, timedelta
import bcrypt
import secrets
import hashlib

from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.schemas.user import UserCreate, UserUpdate, PasswordChange
from app.utils.logger import get_logger
from app.utils.pii_sanitizer import mask_email, mask_username, mask_uuid
from app.config import settings

logger = get_logger(__name__)


class UserService:
    """Lógica de negocio para usuarios"""
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """
        Hashea una contraseña usando bcrypt
        
        Args:
            password: Contraseña en texto plano
        
        Returns:
            Hash de la contraseña
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verifica si una contraseña coincide con su hash
        
        Args:
            plain_password: Contraseña en texto plano
            hashed_password: Hash almacenado
        
        Returns:
            True si coincide, False si no
        """
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None) -> List[User]:
        """
        Obtener todos los usuarios con paginación
        
        Args:
            db: Sesión de base de datos
            skip: Registros a saltar (offset)
            limit: Número máximo de registros
            is_active: Filtrar por estado activo/inactivo
        
        Returns:
            Lista de usuarios
        """
        logger.info(f"Obteniendo usuarios: skip={skip}, limit={limit}, is_active={is_active}")
        
        query = db.query(User)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        users = query.offset(skip).limit(limit).all()
        logger.info(f"Se encontraron {len(users)} usuarios")
        
        return users
    
    @staticmethod
    def get_by_id(db: Session, user_id: UUID) -> Optional[User]:
        """
        Obtener usuario por ID
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
        
        Returns:
            Usuario o None si no existe
        """
        logger.info(f"Buscando usuario con ID: {mask_uuid(str(user_id))}")
        user = db.query(User).filter(User.id == user_id).first()
        
        if user:
            logger.info(f"Usuario encontrado: ID={mask_uuid(str(user.id))}")
        else:
            logger.warning(f"Usuario no encontrado: {mask_uuid(str(user_id))}")
        
        return user
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """
        Obtener usuario por email
        
        Args:
            db: Sesión de base de datos
            email: Email del usuario
        
        Returns:
            Usuario o None si no existe
        """
        logger.info(f"Buscando usuario con email: {mask_email(email)}")
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """
        Obtener usuario por username
        
        Args:
            db: Sesión de base de datos
            username: Username del usuario
        
        Returns:
            Usuario o None si no existe
        """
        logger.info(f"Buscando usuario con username: {mask_username(username)}")
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def create(db: Session, user_data: UserCreate) -> User:
        """
        Crear nuevo usuario
        
        Args:
            db: Sesión de base de datos
            user_data: Datos del usuario a crear
        
        Returns:
            Usuario creado
        
        Raises:
            ValueError: Si el email o username ya existe
        """
        logger.info(f"Creando nuevo usuario: {mask_email(user_data.email)}")
        
        # Verificar que el email no exista
        if UserService.get_by_email(db, user_data.email):
            raise ValueError("El email proporcionado ya está registrado")
        
        # Verificar que el username no exista (si se proporciona)
        if user_data.username and UserService.get_by_username(db, user_data.username):
            raise ValueError("El username proporcionado ya está en uso")
        
        # Hashear la contraseña
        password_hash = UserService._hash_password(user_data.password)
        
        # Crear usuario
        user_dict = user_data.model_dump(exclude={'password'})
        user = User(**user_dict, password_hash=password_hash)
        
        db.add(user)
        db.commit()
        db.refresh(user)

        # Crear categorías por defecto para el nuevo usuario
        UserService._create_default_categories(db, user.id)

        logger.info(f"Usuario creado: {mask_uuid(str(user.id))}")
        return user

    @staticmethod
    def _create_default_categories(db: Session, user_id) -> None:
        """Crea las categorías por defecto al registrar un nuevo usuario."""
        import uuid
        from app.models.category import Category

        default_categories = [
            # Gastos
            ("Alquiler / Hipoteca",   "expense", "#14B8A6"),
            ("Ocio y entretenimiento","expense", "#8B5CF6"),
            ("Restaurantes",          "expense", "#F97316"),
            ("Ropa y calzado",        "expense", "#EC4899"),
            ("Salud",                 "expense", "#10B981"),
            ("Seguros",               "expense", "#6B7280"),
            ("Suministros del hogar", "expense", "#F59E0B"),
            ("Supermercado",          "expense", "#84CC16"),
            ("Suscripciones",         "expense", "#6366F1"),
            ("Transporte",            "expense", "#06B6D4"),
            ("Viajes",                "expense", "#EF4444"),
            # Ingresos
            ("Intereses",             "income",  "#6EE7B7"),
            ("Salario",               "income",  "#059669"),
        ]

        for name, cat_type, color in default_categories:
            category = Category(
                id=uuid.uuid4(),
                name=name,
                type=cat_type,
                color=color,
                user_id=user_id
            )
            db.add(category)

        db.commit()
        logger.info(f"Categorías por defecto creadas para usuario: {mask_uuid(str(user_id))}")
    
    @staticmethod
    def update(db: Session, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        """
        Actualizar usuario existente
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            user_data: Datos a actualizar
        
        Returns:
            Usuario actualizado o None si no existe
        
        Raises:
            ValueError: Si el email o username ya existe
        """
        logger.info(f"Actualizando usuario: {mask_uuid(str(user_id))}")
        
        user = UserService.get_by_id(db, user_id)
        if not user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True, exclude={'password'})
        
        # Verificar email único (si se está cambiando)
        if 'email' in update_data and update_data['email'] != user.email:
            if UserService.get_by_email(db, update_data['email']):
                raise ValueError("El email proporcionado ya está registrado")
        
        # Verificar username único (si se está cambiando)
        if 'username' in update_data and update_data['username'] != user.username:
            if UserService.get_by_username(db, update_data['username']):
                raise ValueError("El username proporcionado ya está en uso")
        
        # Si se proporciona nueva contraseña
        if user_data.password:
            update_data['password_hash'] = UserService._hash_password(user_data.password)
        
        # Actualizar campos
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"Usuario actualizado: {mask_uuid(str(user.id))}")
        return user
    
    @staticmethod
    def delete(db: Session, user_id: UUID) -> bool:
        """
        Eliminar usuario (también elimina sus cuentas por cascade)
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
        
        Returns:
            True si se eliminó, False si no existe
        """
        logger.info(f"Eliminando usuario: {mask_uuid(str(user_id))}")
        
        user = UserService.get_by_id(db, user_id)
        if not user:
            return False
        
        db.delete(user)
        db.commit()
        
        logger.info(f"Usuario eliminado: {mask_uuid(str(user_id))}")
        return True
    
    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Optional[User]:
        """
        Autenticar usuario por email y contraseña
        
        Args:
            db: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano
        
        Returns:
            Usuario si las credenciales son correctas, None si no
        """
        logger.info(f"Intentando autenticar usuario: {mask_email(email)}")
        
        user = UserService.get_by_email(db, email)
        if not user:
            logger.warning(f"Usuario no encontrado para autenticación: {mask_email(email)}")
            return None
        
        if not user.is_active:
            logger.warning(f"Usuario inactivo intenta autenticarse: {mask_uuid(str(user.id))}")
            return None
        
        if not UserService._verify_password(password, user.password_hash):
            logger.warning(f"Contraseña incorrecta para usuario: {mask_uuid(str(user.id))}")
            return None
        
        # Actualizar last_login
        user.last_login = datetime.now()
        db.commit()
        
        logger.info(f"Usuario autenticado: {mask_uuid(str(user.id))}")
        return user
    
    @staticmethod
    def change_password(db: Session, user_id: UUID, password_data: PasswordChange) -> bool:
        """
        Cambiar contraseña de usuario
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            password_data: Contraseñas actual y nueva
        
        Returns:
            True si se cambió, False si la contraseña actual es incorrecta
        
        Raises:
            ValueError: Si el usuario no existe
        """
        logger.info(f"Cambiando contraseña para usuario: {mask_uuid(str(user_id))}")
        
        user = UserService.get_by_id(db, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        
        # Verificar contraseña actual
        if not UserService._verify_password(password_data.current_password, user.password_hash):
            logger.warning(f"Contraseña actual incorrecta para usuario: {mask_uuid(str(user_id))}")
            return False
        
        # Actualizar a nueva contraseña
        user.password_hash = UserService._hash_password(password_data.new_password)
        db.commit()
        
        logger.info(f"Contraseña cambiada para usuario: {mask_uuid(str(user_id))}")
        return True
    
    @staticmethod
    def get_total_count(db: Session, is_active: Optional[bool] = None) -> int:
        """
        Obtener total de usuarios
        
        Args:
            db: Sesión de base de datos
            is_active: Filtrar por estado activo/inactivo
        
        Returns:
            Cantidad total de usuarios
        """
        query = db.query(func.count(User.id))
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        return query.scalar()

    # ============================================
    # MÉTODOS PARA RESET DE CONTRASEÑA
    # ============================================

    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Hashea un token de reset para almacenarlo de forma segura.

        Args:
            token: Token en texto plano

        Returns:
            Hash SHA-256 del token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _mask_email_for_display(email: str) -> str:
        """
        Enmascara un email para mostrar en respuestas.
        Ejemplo: usuario@example.com -> u***@example.com

        Args:
            email: Email completo

        Returns:
            Email parcialmente oculto
        """
        parts = email.split('@')
        if len(parts) != 2:
            return "***@***"

        local = parts[0]
        domain = parts[1]

        if len(local) <= 2:
            masked_local = local[0] + "***"
        else:
            masked_local = local[0] + "***"

        return f"{masked_local}@{domain}"

    @staticmethod
    def create_password_reset_token(db: Session, email: str) -> Optional[Tuple[str, User]]:
        """
        Crea un token de reset de contraseña para un usuario.

        Por seguridad:
        - Invalida tokens anteriores del mismo usuario
        - El token se almacena hasheado
        - Retorna el token en texto plano (solo se puede obtener una vez)

        Args:
            db: Sesión de base de datos
            email: Email del usuario

        Returns:
            Tupla (token_texto_plano, user) si el usuario existe, None si no
        """
        user = UserService.get_by_email(db, email)

        if not user:
            logger.info(f"Reset password solicitado para email inexistente: {mask_email(email)}")
            return None

        if not user.is_active:
            logger.warning(f"Reset password solicitado para usuario inactivo: {mask_uuid(str(user.id))}")
            return None

        # Invalidar tokens anteriores del usuario
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False
        ).update({"used": True})

        # Generar nuevo token (64 caracteres URL-safe)
        plain_token = secrets.token_urlsafe(48)
        hashed_token = UserService._hash_token(plain_token)

        # Calcular expiración
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
        )

        # Crear registro
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=hashed_token,
            expires_at=expires_at,
            used=False
        )

        db.add(reset_token)
        db.commit()

        logger.info(f"Token de reset creado para usuario: {mask_uuid(str(user.id))}")

        return (plain_token, user)

    @staticmethod
    def verify_password_reset_token(db: Session, plain_token: str) -> Optional[Tuple[bool, str, User]]:
        """
        Verifica si un token de reset es válido.

        Args:
            db: Sesión de base de datos
            plain_token: Token en texto plano

        Returns:
            Tupla (valid, masked_email, user) si el token existe, None si no
        """
        hashed_token = UserService._hash_token(plain_token)

        token_record = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == hashed_token
        ).first()

        if not token_record:
            logger.warning("Verificación de token inexistente")
            return None

        user = db.query(User).filter(User.id == token_record.user_id).first()

        if not user:
            logger.warning(f"Token válido pero usuario no existe: {mask_uuid(str(token_record.user_id))}")
            return None

        is_valid = token_record.is_valid
        masked_email = UserService._mask_email_for_display(user.email)

        if not is_valid:
            reason = "expirado" if token_record.is_expired else "ya usado"
            logger.info(f"Token {reason} para usuario: {mask_uuid(str(user.id))}")

        return (is_valid, masked_email, user)

    @staticmethod
    def reset_password_with_token(db: Session, plain_token: str, new_password: str) -> bool:
        """
        Restablece la contraseña usando un token válido.

        Args:
            db: Sesión de base de datos
            plain_token: Token en texto plano
            new_password: Nueva contraseña

        Returns:
            True si se restableció correctamente, False si el token es inválido

        Raises:
            ValueError: Si el token es inválido o expirado
        """
        hashed_token = UserService._hash_token(plain_token)

        token_record = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == hashed_token
        ).first()

        if not token_record:
            logger.warning("Intento de reset con token inexistente")
            raise ValueError("Token inválido o expirado")

        if not token_record.is_valid:
            reason = "expirado" if token_record.is_expired else "ya usado"
            logger.warning(f"Intento de reset con token {reason}")
            raise ValueError("Token inválido o expirado")

        user = db.query(User).filter(User.id == token_record.user_id).first()

        if not user:
            logger.error(f"Token válido pero usuario no existe: {mask_uuid(str(token_record.user_id))}")
            raise ValueError("Usuario no encontrado")

        if not user.is_active:
            logger.warning(f"Intento de reset para usuario inactivo: {mask_uuid(str(user.id))}")
            raise ValueError("Usuario inactivo")

        # Actualizar contraseña
        user.password_hash = UserService._hash_password(new_password)

        # Marcar token como usado
        token_record.used = True

        db.commit()

        logger.info(f"Contraseña restablecida exitosamente para usuario: {mask_uuid(str(user.id))}")

        return True

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> int:
        """
        Elimina tokens expirados de la base de datos.
        Puede ejecutarse periódicamente como tarea de mantenimiento.

        Args:
            db: Sesión de base de datos

        Returns:
            Número de tokens eliminados
        """
        result = db.query(PasswordResetToken).filter(
            PasswordResetToken.expires_at < datetime.now(timezone.utc)
        ).delete()

        db.commit()

        if result > 0:
            logger.info(f"Limpieza: {result} tokens expirados eliminados")

        return result

