"""
Servicio de lógica de negocio para Account
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID

from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AccountService:
    """Lógica de negocio para cuentas"""
    
    @staticmethod
    def get_all(
        db: Session, 
        user_id: UUID,
        skip: int = 0, 
        limit: int = 100, 
        is_active: Optional[bool] = None
    ) -> List[Account]:
        """
        Obtener todas las cuentas de un usuario con paginación
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario propietario
            skip: Registros a saltar (offset)
            limit: Número máximo de registros
            is_active: Filtrar por estado activo/inactivo (None = todos)
        
        Returns:
            Lista de cuentas del usuario
        """
        logger.info(f"Obteniendo cuentas: user_id={user_id}, skip={skip}, limit={limit}, is_active={is_active}")
        
        query = db.query(Account).filter(Account.user_id == user_id)
        
        if is_active is not None:
            query = query.filter(Account.is_active == is_active)
        
        accounts = query.offset(skip).limit(limit).all()
        logger.info(f"Se encontraron {len(accounts)} cuentas")
        
        return accounts
    
    @staticmethod
    def get_by_id(db: Session, account_id: UUID, user_id: UUID) -> Optional[Account]:
        """
        Obtener cuenta por ID si pertenece al usuario
        
        Args:
            db: Sesión de base de datos
            account_id: UUID de la cuenta
            user_id: UUID del usuario propietario
        
        Returns:
            Cuenta o None si no existe o no pertenece al usuario
        """
        logger.info(f"Buscando cuenta ID: {account_id} para user_id: {user_id}")
        account = db.query(Account).filter(
            Account.id == account_id,
            Account.user_id == user_id
        ).first()
        
        if account:
            logger.info(f"Cuenta encontrada: {account.name}")
        else:
            logger.warning(f"Cuenta no encontrada: {account_id}")
        
        return account
    
    @staticmethod
    def create(db: Session, account_data: AccountCreate) -> Account:
        """
        Crear nueva cuenta
        
        Args:
            db: Sesión de base de datos
            account_data: Datos de la cuenta a crear
        
        Returns:
            Cuenta creada
        """
        logger.info(f"Creando nueva cuenta: {account_data.name}")
        
        account = Account(**account_data.model_dump())
        
        db.add(account)
        db.commit()
        db.refresh(account)
        
        logger.info(f"Cuenta creada exitosamente: {account.id} - {account.name}")
        return account
    
    @staticmethod
    def update(db: Session, account_id: UUID, user_id: UUID, account_data: AccountUpdate) -> Optional[Account]:
        """
        Actualizar cuenta existente si pertenece al usuario
        
        Args:
            db: Sesión de base de datos
            account_id: UUID de la cuenta
            user_id: UUID del usuario propietario
            account_data: Datos a actualizar
        
        Returns:
            Cuenta actualizada o None si no existe o no pertenece al usuario
        """
        logger.info(f"Actualizando cuenta: {account_id} para user_id: {user_id}")
        
        account = AccountService.get_by_id(db, account_id, user_id)
        if not account:
            return None
        
        # Actualizar solo los campos proporcionados
        update_data = account_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account, field, value)
        
        db.commit()
        db.refresh(account)
        
        logger.info(f"Cuenta actualizada: {account.id} - {account.name}")
        return account
    
    @staticmethod
    def delete(db: Session, account_id: UUID, user_id: UUID) -> bool:
        """
        Eliminar cuenta si pertenece al usuario (hard delete)
        
        Args:
            db: Sesión de base de datos
            account_id: UUID de la cuenta
            user_id: UUID del usuario propietario
        
        Returns:
            True si se eliminó, False si no existe o no pertenece al usuario
        """
        logger.info(f"Eliminando cuenta: {account_id} para user_id: {user_id}")
        
        account = AccountService.get_by_id(db, account_id, user_id)
        if not account:
            return False
        
        db.delete(account)
        db.commit()
        
        logger.info(f"Cuenta eliminada: {account_id}")
        return True
    
    @staticmethod
    def get_total_count(db: Session, user_id: UUID, is_active: Optional[bool] = None) -> int:
        """
        Obtener total de cuentas del usuario (para paginación)
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario propietario
            is_active: Filtrar por estado activo/inactivo
        
        Returns:
            Número total de cuentas del usuario
        """
        query = db.query(func.count(Account.id)).filter(Account.user_id == user_id)
        
        if is_active is not None:
            query = query.filter(Account.is_active == is_active)
        
        return query.scalar()
    
    @staticmethod
    def get_total_balance(db: Session, user_id: UUID, is_active: bool = True) -> float:
        """
        Calcular balance total de las cuentas del usuario
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario propietario
            is_active: Solo cuentas activas
        
        Returns:
            Balance total
        """
        query = db.query(func.sum(Account.balance)).filter(Account.user_id == user_id)
        
        if is_active:
            query = query.filter(Account.is_active == is_active)
        
        total = query.scalar()
        return float(total) if total else 0.0
