"""
Servicio de lógica de negocio para Category
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.account import Account
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CategoryService:
    """Lógica de negocio para categorías"""
    
    @staticmethod
    def get_all(db: Session, user_id: UUID, skip: int = 0, limit: int = 100, category_type: Optional[str] = None) -> List[Category]:
        """
        Obtener todas las categorías con paginación (solo las usadas por el usuario)
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            skip: Registros a saltar (offset)
            limit: Número máximo de registros
            category_type: Filtrar por tipo (income/expense)
        
        Returns:
            Lista de categorías con estadísticas calculadas
        """
        logger.info(f"Obteniendo categorías para user_id: {user_id}, skip={skip}, limit={limit}, type={category_type}")
        
        # Obtener IDs de categorías usadas por el usuario (a través de sus transacciones)
        category_ids_query = db.query(Category.id).join(
            Transaction, Transaction.category_id == Category.id
        ).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id
        )
        
        if category_type:
            category_ids_query = category_ids_query.filter(Category.type == category_type)
        
        category_ids_query = category_ids_query.distinct()
        
        # Obtener las categorías completas
        query = db.query(Category).filter(Category.id.in_(category_ids_query))
        categories = query.offset(skip).limit(limit).all()
        
        logger.info(f"Se encontraron {len(categories)} categorías")
        
        # Calcular estadísticas para cada categoría (solo del usuario)
        for category in categories:
            category.total_amount = CategoryService._calculate_total_amount(db, category.id, user_id)
        
        return categories
    
    @staticmethod
    def _calculate_total_amount(db: Session, category_id: UUID, user_id: UUID) -> float:
        """
        Calcula el monto total de transacciones de una categoría para un usuario
        
        Args:
            db: Sesión de base de datos
            category_id: UUID de la categoría
            user_id: UUID del usuario
        
        Returns:
            Total amount (suma de todas las transacciones del usuario)
        """
        from app.models.transaction import Transaction
        
        result = db.query(func.sum(Transaction.amount)).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Transaction.category_id == category_id,
            Account.user_id == user_id
        ).scalar()
        
        return float(result) if result else 0.0
    
    @staticmethod
    def get_by_id(db: Session, category_id: UUID, user_id: UUID) -> Optional[Category]:
        """
        Obtener categoría por ID (solo si el usuario la ha usado)
        
        Args:
            db: Sesión de base de datos
            category_id: UUID de la categoría
            user_id: UUID del usuario
        
        Returns:
            Categoría o None si no existe o el usuario no la ha usado
        """
        logger.info(f"Buscando categoría ID: {category_id} para user_id: {user_id}")
        
        # Verificar que el usuario haya usado esta categoría
        category = db.query(Category).join(
            Transaction, Transaction.category_id == Category.id
        ).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Category.id == category_id,
            Account.user_id == user_id
        ).first()
        
        if category:
            logger.info(f"Categoría encontrada: {category.name}")
            category.total_amount = CategoryService._calculate_total_amount(db, category.id, user_id)
        else:
            logger.warning(f"Categoría no encontrada o no usada por el usuario: {category_id}")
        
        return category
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Category]:
        """
        Obtener categoría por nombre (case-insensitive, con trim)
        
        Args:
            db: Sesión de base de datos
            name: Nombre de la categoría
        
        Returns:
            Categoría o None si no existe
        """
        logger.info(f"Buscando categoría por nombre: '{name}'")
        
        # Normalizar el nombre: trim y case-insensitive
        normalized_name = name.strip()
        
        # Búsqueda case-insensitive usando func.lower
        category = db.query(Category).filter(
            func.lower(Category.name) == func.lower(normalized_name)
        ).first()
        
        if category:
            logger.info(f"Categoría encontrada: {category.name} (ID: {category.id})")
        else:
            logger.warning(f"No se encontró categoría con nombre: '{name}'")
        
        return category
    
    @staticmethod
    def create(db: Session, category_data: CategoryCreate) -> Category:
        """
        Crear nueva categoría
        
        Args:
            db: Sesión de base de datos
            category_data: Datos de la categoría a crear
        
        Returns:
            Categoría creada
        
        Raises:
            ValueError: Si el nombre ya existe
        """
        logger.info(f"Creando nueva categoría: {category_data.name}")
        
        # Verificar si el nombre ya existe
        existing = CategoryService.get_by_name(db, category_data.name)
        if existing:
            logger.error(f"La categoría '{category_data.name}' ya existe")
            raise ValueError(f"Ya existe una categoría con el nombre '{category_data.name}'")
        
        category = Category(**category_data.model_dump())
        
        db.add(category)
        db.commit()
        db.refresh(category)
        
        logger.info(f"Categoría creada exitosamente: {category.id} - {category.name}")
        return category
    
    @staticmethod
    def update(db: Session, category_id: UUID, category_data: CategoryUpdate) -> Optional[Category]:
        """
        Actualizar categoría existente
        
        Args:
            db: Sesión de base de datos
            category_id: UUID de la categoría
            category_data: Datos a actualizar
        
        Returns:
            Categoría actualizada o None si no existe
        
        Raises:
            ValueError: Si el nuevo nombre ya existe
        """
        logger.info(f"Actualizando categoría: {category_id}")
        
        category = CategoryService.get_by_id(db, category_id)
        if not category:
            return None
        
        # Si se está actualizando el nombre, verificar unicidad
        update_data = category_data.model_dump(exclude_unset=True)
        if 'name' in update_data and update_data['name'] != category.name:
            existing = CategoryService.get_by_name(db, update_data['name'])
            if existing:
                logger.error(f"La categoría '{update_data['name']}' ya existe")
                raise ValueError(f"Ya existe una categoría con el nombre '{update_data['name']}'")
        
        for field, value in update_data.items():
            setattr(category, field, value)
        
        db.commit()
        db.refresh(category)
        
        logger.info(f"Categoría actualizada: {category.id} - {category.name}")
        return category
    
    @staticmethod
    def delete(db: Session, category_id: UUID) -> bool:
        """
        Eliminar categoría (las transacciones quedan con category_id=NULL)
        
        Args:
            db: Sesión de base de datos
            category_id: UUID de la categoría
        
        Returns:
            True si se eliminó, False si no existe
        """
        logger.info(f"Eliminando categoría: {category_id}")
        
        category = CategoryService.get_by_id(db, category_id)
        if not category:
            return False
        
        db.delete(category)
        db.commit()
        
        logger.info(f"Categoría eliminada: {category_id}")
        return True
    
    @staticmethod
    def get_total_count(db: Session, user_id: UUID, category_type: Optional[str] = None) -> int:
        """
        Obtener total de categorías usadas por el usuario (para paginación)
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            category_type: Filtrar por tipo (income/expense)
        
        Returns:
            Número total de categorías usadas por el usuario
        """
        query = db.query(func.count(func.distinct(Category.id))).join(
            Transaction, Transaction.category_id == Category.id
        ).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id
        )
        
        if category_type:
            query = query.filter(Category.type == category_type)
        
        return query.scalar()
    
    @staticmethod
    def get_all_available_categories(db: Session, category_type: Optional[str] = None) -> List[Category]:
        """
        Obtener todas las categorías disponibles en la base de datos,
        independientemente de si están asociadas a transacciones
        
        Args:
            db: Sesión de base de datos
            category_type: Filtrar por tipo (income/expense/None=todas)
        
        Returns:
            Lista de todas las categorías disponibles
        """
        logger.info(f"Obteniendo todas las categorías disponibles, type={category_type}")
        
        query = db.query(Category)
        
        if category_type:
            query = query.filter(Category.type == category_type)
        
        categories = query.order_by(Category.type, Category.name).all()
        
        logger.info(f"Se encontraron {len(categories)} categorías disponibles")
        return categories
