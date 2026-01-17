"""
Endpoints CRUD para Categories
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import math

from app.database import get_db
from app.schemas import CategoryCreate, CategoryUpdate, CategoryResponse, PaginatedResponse
from app.services import CategoryService
from app.utils.security import get_current_user, check_rate_limit
from app.models import User
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/categories",
    tags=["categories"]
)


@router.get("", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    type: Optional[str] = Query(None, pattern="^(income|expense)$", description="Filtrar por tipo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Listar categorías usadas por el usuario con paginación
    
    **Parámetros:**
    - page: Número de página (default: 1)
    - page_size: Registros por página (default: 20, max: 100)
    - type: Filtrar por tipo (income/expense/null=todos)
    
    **Response:**
    ```json
    {
      "items": [
        {
          "id": "uuid",
          "name": "Supermercado",
          "type": "expense",
          "color": "#EF4444"
        }
      ],
      "total": 15,
      "page": 1,
      "page_size": 20,
      "total_pages": 1
    }
    ```
    """
    logger.info(f"Listando categorías para user {current_user.email}: page={page}, page_size={page_size}, type={type}")
    
    skip = (page - 1) * page_size
    
    categories = CategoryService.get_all(db, user_id=current_user.id, skip=skip, limit=page_size, category_type=type)
    total = CategoryService.get_total_count(db, user_id=current_user.id, category_type=type)
    
    return PaginatedResponse(
        items=[CategoryResponse.model_validate(cat) for cat in categories],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/available/all", response_model=List[CategoryResponse])
async def get_all_available_categories(
    type: Optional[str] = Query(None, pattern="^(income|expense)$", description="Filtrar por tipo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener todas las categorías disponibles en la base de datos
    
    Devuelve todas las categorías (id, nombre, tipo, color) independientemente
    de si tienen transacciones asociadas o no.
    
    **Parámetros:**
    - type: Filtrar por tipo (income/expense/null=todas)
    
    **Response:**
    ```json
    [
      {
        "id": "uuid",
        "name": "Supermercado",
        "type": "expense",
        "color": "#EF4444",
        "created_at": "2025-01-15T10:30:00",
        "transaction_count": 0,
        "total_amount": 0.0
      },
      {
        "id": "uuid",
        "name": "Salario",
        "type": "income",
        "color": "#10B981",
        "created_at": "2025-01-10T08:00:00",
        "transaction_count": 0,
        "total_amount": 0.0
      }
    ]
    ```
    """
    logger.info(f"Obteniendo todas las categorías disponibles para user {current_user.email}, type={type}")
    
    categories = CategoryService.get_all_available_categories(db, category_type=type)
    
    logger.info(f"Devolviendo {len(categories)} categorías disponibles")
    
    # Construir respuesta manualmente para evitar conflictos con propiedades read-only del modelo
    return [
        CategoryResponse(
            id=cat.id,
            name=cat.name,
            type=cat.type,
            color=cat.color,
            created_at=cat.created_at,
            transaction_count=0,
            total_amount=0.0
        ) 
        for cat in categories
    ]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener categoría por ID (verificando que el usuario la haya usado)
    
    **Response:**
    ```json
    {
      "id": "uuid",
      "name": "Supermercado",
      "type": "expense",
      "color": "#EF4444",
      "created_at": "2025-01-15T10:30:00"
    }
    ```
    """
    logger.info(f"Obteniendo categoría {category_id} para user {current_user.email}")
    
    category = CategoryService.get_by_id(db, category_id, current_user.id)
    if not category:
        logger.warning(f"Categoría no encontrada o no usada por el usuario: {category_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoría {category_id} no encontrada"
        )
    
    return CategoryResponse.model_validate(category)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Crear nueva categoría (disponible globalmente)
    
    **Request Body:**
    ```json
    {
      "name": "Transporte",
      "type": "expense",
      "color": "#3B82F6"
    }
    ```
    
    **Response:** 201 Created con los datos de la categoría creada
    
    **Error:** 400 Bad Request si el nombre ya existe
    """
    logger.info(f"Creando nueva categoría: {category_data.name}")
    
    try:
        category = CategoryService.create(db, category_data)
        logger.info(f"Categoría creada exitosamente: {category.id}")
        return CategoryResponse.model_validate(category)
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al crear categoría: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Actualizar categoría existente
    
    **Request Body (todos los campos son opcionales):**
    ```json
    {
      "name": "Transporte Público",
      "color": "#1E40AF"
    }
    ```
    
    **Response:** 200 OK con los datos actualizados
    
    **Error:** 400 Bad Request si el nuevo nombre ya existe
    """
    logger.info(f"Actualizando categoría: {category_id}")
    
    try:
        category = CategoryService.update(db, category_id, category_data, current_user.id)
        if not category:
            logger.warning(f"Categoría no encontrada para actualizar: {category_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoría {category_id} no encontrada"
            )
        
        logger.info(f"Categoría actualizada exitosamente: {category.id}")
        return CategoryResponse.model_validate(category)
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al actualizar categoría: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Eliminar categoría
    
    **ℹ️ NOTA:** Las transacciones asociadas quedarán con category_id=NULL (SET NULL)
    
    **Response:** 204 No Content si se eliminó correctamente
    """
    logger.info(f"Eliminando categoría {category_id} (user: {current_user.email})")
    
    deleted = CategoryService.delete(db, category_id)
    if not deleted:
        logger.warning(f"Categoría no encontrada para eliminar: {category_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoría {category_id} no encontrada"
        )
    
    logger.info(f"Categoría eliminada exitosamente: {category_id}")
    return None


@router.get("/stats/summary", response_model=dict)
async def get_categories_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener resumen de categorías usadas por el usuario
    
    **Response:**
    ```json
    {
      "total_categories": 20,
      "income_categories": 5,
      "expense_categories": 15
    }
    ```
    """
    logger.info(f"Obteniendo resumen de categorías para user {current_user.email}")
    
    total = CategoryService.get_total_count(db, user_id=current_user.id)
    income = CategoryService.get_total_count(db, user_id=current_user.id, category_type="income")
    expense = CategoryService.get_total_count(db, user_id=current_user.id, category_type="expense")
    
    return {
        "total_categories": total,
        "income_categories": income,
        "expense_categories": expense
    }
