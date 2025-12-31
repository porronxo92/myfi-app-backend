"""
Servicio de lógica de negocio para User
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import bcrypt

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, PasswordChange
from app.utils.logger import get_logger

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
        logger.info(f"Buscando usuario con ID: {user_id}")
        user = db.query(User).filter(User.id == user_id).first()
        
        if user:
            logger.info(f"Usuario encontrado: {user.email}")
        else:
            logger.warning(f"Usuario no encontrado: {user_id}")
        
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
        logger.info(f"Buscando usuario con email: {email}")
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
        logger.info(f"Buscando usuario con username: {username}")
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
        logger.info(f"Creando nuevo usuario: {user_data.email}")
        
        # Verificar que el email no exista
        if UserService.get_by_email(db, user_data.email):
            raise ValueError(f"El email {user_data.email} ya está registrado")
        
        # Verificar que el username no exista (si se proporciona)
        if user_data.username and UserService.get_by_username(db, user_data.username):
            raise ValueError(f"El username {user_data.username} ya está en uso")
        
        # Hashear la contraseña
        password_hash = UserService._hash_password(user_data.password)
        
        # Crear usuario
        user_dict = user_data.model_dump(exclude={'password'})
        user = User(**user_dict, password_hash=password_hash)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Usuario creado: {user.id}")
        return user
    
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
        logger.info(f"Actualizando usuario: {user_id}")
        
        user = UserService.get_by_id(db, user_id)
        if not user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True, exclude={'password'})
        
        # Verificar email único (si se está cambiando)
        if 'email' in update_data and update_data['email'] != user.email:
            if UserService.get_by_email(db, update_data['email']):
                raise ValueError(f"El email {update_data['email']} ya está registrado")
        
        # Verificar username único (si se está cambiando)
        if 'username' in update_data and update_data['username'] != user.username:
            if UserService.get_by_username(db, update_data['username']):
                raise ValueError(f"El username {update_data['username']} ya está en uso")
        
        # Si se proporciona nueva contraseña
        if user_data.password:
            update_data['password_hash'] = UserService._hash_password(user_data.password)
        
        # Actualizar campos
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"Usuario actualizado: {user.id}")
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
        logger.info(f"Eliminando usuario: {user_id}")
        
        user = UserService.get_by_id(db, user_id)
        if not user:
            return False
        
        db.delete(user)
        db.commit()
        
        logger.info(f"Usuario eliminado: {user_id}")
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
        logger.info(f"Intentando autenticar usuario: {email}")
        
        user = UserService.get_by_email(db, email)
        if not user:
            logger.warning(f"Usuario no encontrado: {email}")
            return None
        
        if not user.is_active:
            logger.warning(f"Usuario inactivo: {email}")
            return None
        
        if not UserService._verify_password(password, user.password_hash):
            logger.warning(f"Contraseña incorrecta para: {email}")
            return None
        
        # Actualizar last_login
        user.last_login = datetime.now()
        db.commit()
        
        logger.info(f"Usuario autenticado: {email}")
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
        logger.info(f"Cambiando contraseña para usuario: {user_id}")
        
        user = UserService.get_by_id(db, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        
        # Verificar contraseña actual
        if not UserService._verify_password(password_data.current_password, user.password_hash):
            logger.warning(f"Contraseña actual incorrecta para usuario: {user_id}")
            return False
        
        # Actualizar a nueva contraseña
        user.password_hash = UserService._hash_password(password_data.new_password)
        db.commit()
        
        logger.info(f"Contraseña cambiada para usuario: {user_id}")
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
