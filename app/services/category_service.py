"""
Servicio de lógica de negocio para Category
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
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
        Obtener todas las categorías con paginación (solo las usadas por el usuario en transacciones)

        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            skip: Registros a saltar (offset)
            limit: Número máximo de registros
            category_type: Filtrar por tipo (income/expense)

        Returns:
            Lista de categorías con estadísticas calculadas
        """
        logger.info(f"Obteniendo categorías usadas para user_id: {user_id}, skip={skip}, limit={limit}, type={category_type}")

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

        logger.info(f"Se encontraron {len(categories)} categorías usadas")

        # Calcular estadísticas para cada categoría (solo del usuario)
        for category in categories:
            category.total_amount = CategoryService._calculate_total_amount(db, category.id, user_id)

        return categories

    @staticmethod
    def _calculate_total_amount(db: Session, category_id: UUID, user_id: UUID) -> float:
        """
        Calcula el monto total de transacciones de una categoría para un usuario
        Nota: Cálculos en Python porque amount está encriptado.

        Args:
            db: Sesión de base de datos
            category_id: UUID de la categoría
            user_id: UUID del usuario

        Returns:
            Total amount (suma de todas las transacciones del usuario)
        """
        from app.models.transaction import Transaction

        transactions = db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Transaction.category_id == category_id,
            Account.user_id == user_id
        ).all()

        # Sumar en Python (amount se desencripta automáticamente)
        total = sum([float(t.amount) if t.amount else 0.0 for t in transactions])

        return total

    @staticmethod
    def get_by_id(db: Session, category_id: UUID, user_id: UUID) -> Optional[Category]:
        """
        Obtener categoría por ID (verifica que sea global o del usuario)

        Args:
            db: Sesión de base de datos
            category_id: UUID de la categoría
            user_id: UUID del usuario

        Returns:
            Categoría o None si no existe o no tiene acceso
        """
        logger.info(f"Buscando categoría ID: {category_id} para user_id: {user_id}")

        # Buscar categoría que sea global (user_id=NULL) o del usuario
        category = db.query(Category).filter(
            Category.id == category_id,
            or_(Category.user_id == None, Category.user_id == user_id)
        ).first()

        if category:
            logger.info(f"Categoría encontrada: {category.name}")
            category.total_amount = CategoryService._calculate_total_amount(db, category.id, user_id)
        else:
            logger.warning(f"Categoría no encontrada o sin acceso: {category_id}")

        return category

    @staticmethod
    def get_by_name(db: Session, name: str, user_id: UUID = None) -> Optional[Category]:
        """
        Obtener categoría por nombre (case-insensitive, con trim)
        Si user_id se proporciona, busca en categorías del usuario y globales.

        Args:
            db: Sesión de base de datos
            name: Nombre de la categoría
            user_id: UUID del usuario (opcional)

        Returns:
            Categoría o None si no existe
        """
        logger.info(f"Buscando categoría por nombre: '{name}' para user_id: {user_id}")

        # Normalizar el nombre: trim y case-insensitive
        normalized_name = name.strip()

        # Búsqueda case-insensitive
        query = db.query(Category).filter(
            func.lower(Category.name) == func.lower(normalized_name)
        )

        if user_id:
            # Buscar en categorías del usuario o globales
            query = query.filter(
                or_(Category.user_id == None, Category.user_id == user_id)
            )

        category = query.first()

        if category:
            logger.info(f"Categoría encontrada: {category.name} (ID: {category.id})")
        else:
            logger.warning(f"No se encontró categoría con nombre: '{name}'")

        return category

    @staticmethod
    def create(db: Session, category_data: CategoryCreate, user_id: UUID) -> Category:
        """
        Crear nueva categoría asociada al usuario

        Args:
            db: Sesión de base de datos
            category_data: Datos de la categoría a crear
            user_id: UUID del usuario propietario

        Returns:
            Categoría creada

        Raises:
            ValueError: Si el nombre ya existe para este usuario
        """
        logger.info(f"Creando nueva categoría: {category_data.name} para user_id: {user_id}")

        # Verificar si el nombre ya existe para este usuario o como global
        existing = CategoryService.get_by_name(db, category_data.name, user_id)
        if existing and (existing.user_id == user_id or existing.user_id is None):
            logger.error(f"La categoría '{category_data.name}' ya existe")
            raise ValueError(f"Ya existe una categoría con el nombre '{category_data.name}'")

        category = Category(
            **category_data.model_dump(),
            user_id=user_id
        )

        db.add(category)
        db.commit()
        db.refresh(category)

        logger.info(f"Categoría creada exitosamente: {category.id} - {category.name}")
        return category

    @staticmethod
    def update(db: Session, category_id: UUID, category_data: CategoryUpdate, user_id: UUID) -> Optional[Category]:
        """
        Actualizar categoría existente (solo si es del usuario)

        Args:
            db: Sesión de base de datos
            category_id: UUID de la categoría
            category_data: Datos a actualizar
            user_id: UUID del usuario

        Returns:
            Categoría actualizada o None si no existe o no tiene permiso

        Raises:
            ValueError: Si el nuevo nombre ya existe
        """
        logger.info(f"Actualizando categoría: {category_id}")

        # Solo puede editar sus propias categorías (no las globales)
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.user_id == user_id
        ).first()

        if not category:
            return None

        # Si se está actualizando el nombre, verificar unicidad
        update_data = category_data.model_dump(exclude_unset=True)
        if 'name' in update_data and update_data['name'] != category.name:
            existing = CategoryService.get_by_name(db, update_data['name'], user_id)
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
    def delete(db: Session, category_id: UUID, user_id: UUID) -> bool:
        """
        Eliminar categoría (solo si es del usuario, las transacciones quedan con category_id=NULL)

        Args:
            db: Sesión de base de datos
            category_id: UUID de la categoría
            user_id: UUID del usuario

        Returns:
            True si se eliminó, False si no existe o no tiene permiso
        """
        logger.info(f"Eliminando categoría: {category_id}")

        # Solo puede eliminar sus propias categorías
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.user_id == user_id
        ).first()

        if not category:
            return False

        db.delete(category)
        db.commit()

        logger.info(f"Categoría eliminada: {category_id}")
        return True

    @staticmethod
    def get_total_count(db: Session, user_id: UUID, category_type: Optional[str] = None) -> int:
        """
        Obtener total de categorías usadas por el usuario en transacciones (para paginación)

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
    def get_all_available_categories(db: Session, user_id: UUID, category_type: Optional[str] = None) -> List[Category]:
        """
        Obtener todas las categorías disponibles para un usuario:
        - Categorías globales (user_id = NULL)
        - Categorías propias del usuario

        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            category_type: Filtrar por tipo (income/expense/None=todas)

        Returns:
            Lista de todas las categorías disponibles para el usuario
        """
        logger.info(f"Obteniendo todas las categorías disponibles para user_id: {user_id}, type={category_type}")

        # Categorías globales (user_id=NULL) o del usuario
        query = db.query(Category).filter(
            or_(Category.user_id == None, Category.user_id == user_id)
        )

        if category_type:
            query = query.filter(Category.type == category_type)

        categories = query.order_by(Category.type, Category.name).all()

        logger.info(f"Se encontraron {len(categories)} categorías disponibles")
        return categories
