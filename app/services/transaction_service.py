"""
Servicio de lógica de negocio para Transaction
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TransactionService:
    """Lógica de negocio para transacciones"""
    
    @staticmethod
    def get_all(
        db: Session,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        account_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        transaction_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None
    ) -> List[Transaction]:
        """
        Obtener transacciones del usuario con filtros y paginación
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario (solo sus transacciones)
            skip: Registros a saltar (offset)
            limit: Número máximo de registros
            account_id: Filtrar por cuenta
            category_id: Filtrar por categoría
            transaction_type: Filtrar por tipo (income/expense/transfer)
            date_from: Fecha inicio
            date_to: Fecha fin
            min_amount: Monto mínimo
            max_amount: Monto máximo
        
        Returns:
            Lista de transacciones del usuario
        """
        logger.info(f"Obteniendo transacciones para user_id: {user_id}, skip={skip}, limit={limit}")
        
        query = db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id
        ).options(
            joinedload(Transaction.account),
            joinedload(Transaction.category)
        )
        
        # Aplicar filtros
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        
        if transaction_type:
            query = query.filter(Transaction.type == transaction_type)
        
        if date_from:
            query = query.filter(Transaction.date >= date_from)
        
        if date_to:
            query = query.filter(Transaction.date <= date_to)
        
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
        
        # Ordenar por fecha descendente (más recientes primero)
        transactions = query.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()
        
        logger.info(f"Se encontraron {len(transactions)} transacciones")
        return transactions
    
    @staticmethod
    def get_by_id(db: Session, transaction_id: UUID, user_id: UUID) -> Optional[Transaction]:
        """
        Obtener transacción por ID verificando que pertenezca al usuario
        
        Args:
            db: Sesión de base de datos
            transaction_id: UUID de la transacción
            user_id: UUID del usuario (verifica ownership)
        
        Returns:
            Transacción o None si no existe o no pertenece al usuario
        """
        logger.info(f"Buscando transacción {transaction_id} para user_id: {user_id}")
        
        transaction = db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Transaction.id == transaction_id,
            Account.user_id == user_id
        ).options(
            joinedload(Transaction.account),
            joinedload(Transaction.category)
        ).first()
        
        if transaction:
            logger.info(f"Transacción encontrada: {transaction.description}")
        else:
            logger.warning(f"Transacción no encontrada o no pertenece al usuario: {transaction_id}")
        
        return transaction
    
    @staticmethod
    def create(db: Session, transaction_data: TransactionCreate, user_id: UUID) -> Transaction:
        """
        Crear nueva transacción verificando que la cuenta pertenece al usuario
        
        Args:
            db: Sesión de base de datos
            transaction_data: Datos de la transacción a crear
            user_id: UUID del usuario (verifica ownership)
        
        Returns:
            Transacción creada
        
        Raises:
            ValueError: Si la cuenta no existe o no pertenece al usuario
            ValueError: Si category_id es string y no se encuentra la categoría
        """
        logger.info(f"Creando nueva transacción para user_id: {user_id} - {transaction_data.description}")
        
        # Verificar que la cuenta existe y pertenece al usuario
        account = db.query(Account).filter(
            Account.id == transaction_data.account_id,
            Account.user_id == user_id
        ).first()
        if not account:
            raise ValueError(f"La cuenta {transaction_data.account_id} no existe o no pertenece al usuario")
        
        # ============================================
        # RESOLUCIÓN DE CATEGORÍA: ID o NOMBRE
        # ============================================
        resolved_category_id = transaction_data.category_id
        
        # Si category_id es un string, puede ser:
        # 1. Un UUID en formato string (uso normal)
        # 2. Un nombre de categoría (búsqueda por nombre)
        if transaction_data.category_id and isinstance(transaction_data.category_id, str):
            from app.services.category_service import CategoryService
            
            category_value = transaction_data.category_id
            
            # Intentar parsear como UUID primero
            try:
                from uuid import UUID as UUIDType
                # Si se puede parsear como UUID, es un ID válido
                parsed_uuid = UUIDType(category_value)
                resolved_category_id = parsed_uuid
                logger.info(f"category_id parseado como UUID: {resolved_category_id}")
                
                # Verificar que la categoría con ese UUID existe
                category = db.query(Category).filter(Category.id == parsed_uuid).first()
                if not category:
                    raise ValueError(f"Categoría con ID '{category_value}' no encontrada")
                    
            except (ValueError, AttributeError):
                # No es un UUID válido, buscar por nombre
                logger.info(f"Resolviendo categoría por nombre: '{category_value}'")
                
                category = CategoryService.get_by_name(db, category_value)
                if not category:
                    raise ValueError(f"Categoría '{category_value}' no encontrada")
                
                resolved_category_id = category.id
                logger.info(f"Categoría resuelta: '{category.name}' -> ID: {category.id}")
        
        # Crear diccionario de datos con category_id resuelto
        transaction_dict = transaction_data.model_dump()
        transaction_dict['category_id'] = resolved_category_id
        
        # Remover campo 'categoria' si existe (ya procesado)
        if 'categoria' in transaction_dict:
            del transaction_dict['categoria']
        
        # Crear transacción
        transaction = Transaction(**transaction_dict)
        # Nota: El campo 'source' se toma del request o usa el default 'manual'
        
        db.add(transaction)
        
        # Actualizar balance de la cuenta
        account.balance += Decimal(str(transaction.amount))
        
        # Si es transferencia, actualizar cuenta destino
        if transaction.type == 'transfer' and transaction.transfer_account_id:
            transfer_account = db.query(Account).filter(Account.id == transaction.transfer_account_id).first()
            if transfer_account:
                transfer_account.balance -= Decimal(str(transaction.amount))
                logger.info(f"Balance actualizado en cuenta destino: {transfer_account.name}")
        
        db.commit()
        db.refresh(transaction)
        
        logger.info(f"Transacción creada: {transaction.id} - Balance actualizado: {account.balance}")
        return transaction
    
    @staticmethod
    def update(db: Session, transaction_id: UUID, user_id: UUID, transaction_data: TransactionUpdate) -> Optional[Transaction]:
        """
        Actualizar transacción existente verificando ownership
        
        Args:
            db: Sesión de base de datos
            transaction_id: UUID de la transacción
            user_id: UUID del usuario (verifica ownership)
            transaction_data: Datos a actualizar
        
        Returns:
            Transacción actualizada o None si no existe o no pertenece al usuario
        """
        logger.info(f"Actualizando transacción {transaction_id} para user_id: {user_id}")
        
        transaction = TransactionService.get_by_id(db, transaction_id, user_id)
        if not transaction:
            return None
        
        # Guardar monto anterior para ajustar balance
        old_amount = transaction.amount
        
        # Actualizar solo los campos proporcionados
        update_data = transaction_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(transaction, field, value)
        
        # Si cambió el monto, ajustar balance de la cuenta
        if 'amount' in update_data:
            diff = Decimal(str(transaction.amount)) - Decimal(str(old_amount))
            account = transaction.account
            account.balance += diff
            logger.info(f"Balance ajustado en {diff}: nuevo balance={account.balance}")
        
        db.commit()
        db.refresh(transaction)
        
        logger.info(f"Transacción actualizada: {transaction.id}")
        return transaction
    
    @staticmethod
    def delete(db: Session, transaction_id: UUID, user_id: UUID) -> bool:
        """
        Eliminar transacción verificando ownership (ajusta el balance de la cuenta)
        
        Args:
            db: Sesión de base de datos
            transaction_id: UUID de la transacción
            user_id: UUID del usuario (verifica ownership)
        
        Returns:
            True si se eliminó, False si no existe o no pertenece al usuario
        """
        logger.info(f"Eliminando transacción {transaction_id} para user_id: {user_id}")
        
        transaction = TransactionService.get_by_id(db, transaction_id, user_id)
        if not transaction:
            return False
        
        # Ajustar balance de la cuenta (revertir el monto)
        account = transaction.account
        account.balance -= Decimal(str(transaction.amount))
        logger.info(f"Balance ajustado: nuevo balance={account.balance}")
        
        # Si es transferencia, ajustar cuenta destino
        if transaction.type == 'transfer' and transaction.transfer_account_id:
            transfer_account = db.query(Account).filter(Account.id == transaction.transfer_account_id).first()
            if transfer_account:
                transfer_account.balance += Decimal(str(transaction.amount))
        
        db.delete(transaction)
        db.commit()
        
        logger.info(f"Transacción eliminada: {transaction_id}")
        return True
    
    @staticmethod
    def get_total_count(
        db: Session,
        user_id: UUID,
        account_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        transaction_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> int:
        """
        Obtener total de transacciones del usuario (para paginación)
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            account_id: Filtrar por cuenta
            category_id: Filtrar por categoría
            transaction_type: Filtrar por tipo
            date_from: Fecha inicio
            date_to: Fecha fin
        
        Returns:
            Número total de transacciones del usuario
        """
        query = db.query(func.count(Transaction.id)).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id
        )
        
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        
        if transaction_type:
            query = query.filter(Transaction.type == transaction_type)
        
        if date_from:
            query = query.filter(Transaction.date >= date_from)
        
        if date_to:
            query = query.filter(Transaction.date <= date_to)
        
        return query.scalar()
    
    @staticmethod
    def get_summary(
        db: Session,
        user_id: UUID,
        account_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> dict:
        """
        Obtener resumen financiero del usuario (ingresos, gastos, transferencias)
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            account_id: Filtrar por cuenta
            date_from: Fecha inicio
            date_to: Fecha fin
        
        Returns:
            Diccionario con total_income, total_expense, balance
        """
        query = db.query(
            func.sum(Transaction.amount).filter(Transaction.amount > 0).label('income'),
            func.sum(Transaction.amount).filter(Transaction.amount < 0).label('expense')
        ).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id
        )
        
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        
        if date_from:
            query = query.filter(Transaction.date >= date_from)
        
        if date_to:
            query = query.filter(Transaction.date <= date_to)
        
        result = query.first()
        
        income = float(result.income) if result.income else 0.0
        expense = float(result.expense) if result.expense else 0.0
        
        return {
            "total_income": income,
            "total_expense": abs(expense),
            "balance": income + expense  # expense ya es negativo
        }
