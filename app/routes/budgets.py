"""
Endpoints API para Presupuestos (Budgets)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetListResponse,
    BudgetCopyRequest, BudgetProgress, BudgetSummary, OverspentCategory,
    SuggestedBudget, BudgetComparison, BudgetItemUpdate, BudgetItemResponse
)
from app.models.budget import Budget
from app.models.budget_item import BudgetItem
from app.models.category import Category
from app.utils.security import get_current_user, check_rate_limit
from app.models.user import User
from app.utils.logger import get_logger
from app.services.budget_service import (
    calculate_budget_progress, get_budget_summary,
    get_overspent_categories, suggest_budget_from_history,
    compare_budgets
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/budgets",
    tags=["budgets"]
)


@router.get("", response_model=List[BudgetListResponse])
async def list_budgets(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Filtrar por año"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Listar todos los presupuestos del usuario
    
    **Parámetros:**
    - year: Año opcional para filtrar
    
    **Response:**
    ```json
    [
      {
        "id": "uuid",
        "user_id": "uuid",
        "month": 1,
        "year": 2025,
        "name": "Enero 2025 - Plan de ahorro",
        "total_budget": 2500.00,
        "items_count": 5,
        "created_at": "2025-01-01T10:00:00Z",
        "updated_at": "2025-01-01T10:00:00Z"
      }
    ]
    ```
    """
    try:
        query = db.query(Budget).filter(Budget.user_id == current_user.id)
        
        if year:
            query = query.filter(Budget.year == year)
        
        budgets = query.order_by(Budget.year.desc(), Budget.month.desc()).all()
        
        # Agregar count de items
        result = []
        for budget in budgets:
            budget_dict = BudgetListResponse.model_validate(budget)
            budget_dict.items_count = len(budget.items)
            result.append(budget_dict)
        
        logger.info(f"Usuario {current_user.id} listó {len(result)} presupuestos")
        return result
        
    except Exception as e:
        logger.error(f"Error al listar presupuestos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar presupuestos: {str(e)}"
        )


@router.get("/current", response_model=Optional[BudgetResponse])
async def get_current_budget(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener el presupuesto del mes actual
    
    **Response:**
    - Si existe: objeto Budget completo
    - Si no existe: null
    
    ```json
    {
      "id": "uuid",
      "user_id": "uuid",
      "month": 1,
      "year": 2025,
      "name": "Enero 2025",
      "total_budget": 2500.00,
      "items": [
        {
          "id": "uuid",
          "budget_id": "uuid",
          "category_id": "uuid",
          "category_name": "Alimentación",
          "allocated_amount": 500.00,
          "notes": "Incluye supermercado y restaurantes",
          "created_at": "2025-01-01T10:00:00Z",
          "updated_at": "2025-01-01T10:00:00Z"
        }
      ],
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-01T10:00:00Z"
    }
    ```
    """
    try:
        budget = Budget.get_current_budget(db, current_user.id)
        
        if not budget:
            logger.info(f"Usuario {current_user.id} no tiene presupuesto para el mes actual")
            return None
        
        # Enriquecer items con nombre de categoría
        for item in budget.items:
            item.category_name = item.category.name
        
        logger.info(f"Usuario {current_user.id} consultó presupuesto actual")
        return BudgetResponse.model_validate(budget)
        
    except Exception as e:
        logger.error(f"Error al obtener presupuesto actual: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener presupuesto actual: {str(e)}"
        )


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener un presupuesto específico por ID
    """
    try:
        budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == current_user.id
        ).first()
        
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado"
            )
        
        # Enriquecer items con nombre de categoría
        for item in budget.items:
            item.category_name = item.category.name
        
        logger.info(f"Usuario {current_user.id} consultó presupuesto {budget_id}")
        return BudgetResponse.model_validate(budget)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener presupuesto {budget_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener presupuesto: {str(e)}"
        )


@router.get("/{budget_id}/summary", response_model=BudgetSummary)
async def get_budget_summary_endpoint(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener resumen ejecutivo del presupuesto con análisis
    
    **Response:**
    ```json
    {
      "budget_id": "uuid",
      "month": 1,
      "year": 2025,
      "total_allocated": 2500.00,
      "total_spent": 1800.50,
      "total_remaining": 699.50,
      "percent_used": 72.02,
      "status": "ok",
      "overspent_categories": ["Restaurantes"],
      "categories_at_risk": ["Transporte"],
      "categories_ok": ["Alimentación", "Hogar"]
    }
    ```
    """
    try:
        # Verificar que el presupuesto pertenece al usuario
        budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == current_user.id
        ).first()
        
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado"
            )
        
        summary = get_budget_summary(db, budget_id)
        
        logger.info(f"Usuario {current_user.id} consultó resumen de presupuesto {budget_id}")
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener resumen de presupuesto {budget_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener resumen: {str(e)}"
        )


@router.get("/{budget_id}/progress", response_model=BudgetProgress)
async def get_budget_progress_endpoint(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener el progreso detallado de cada partida del presupuesto
    
    **Response:**
    ```json
    {
      "budget_id": "uuid",
      "month": 1,
      "year": 2025,
      "total_allocated": 2500.00,
      "total_spent": 1800.50,
      "total_remaining": 699.50,
      "percent_used": 72.02,
      "status": "ok",
      "items": [
        {
          "category_id": "uuid",
          "category_name": "Alimentación",
          "allocated": 500.00,
          "spent": 320.50,
          "remaining": 179.50,
          "percent_used": 64.1,
          "status": "ok",
          "transaction_count": 15
        }
      ]
    }
    ```
    """
    try:
        # Verificar que el presupuesto pertenece al usuario
        budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == current_user.id
        ).first()
        
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado"
            )
        
        progress = calculate_budget_progress(db, budget_id)
        
        logger.info(f"Usuario {current_user.id} consultó progreso de presupuesto {budget_id}")
        return progress
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener progreso de presupuesto {budget_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener progreso: {str(e)}"
        )


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget_data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Crear un nuevo presupuesto
    
    **Body:**
    ```json
    {
      "month": 2,
      "year": 2025,
      "name": "Febrero 2025 - Plan de Ahorro",
      "items": [
        {
          "category_id": "uuid",
          "allocated_amount": 500.00,
          "notes": "Incrementar por San Valentín"
        },
        {
          "category_id": "uuid",
          "allocated_amount": 300.00
        }
      ]
    }
    ```
    """
    try:
        # Verificar que no exista presupuesto para ese mes/año
        existing = Budget.get_budget_by_period(db, current_user.id, budget_data.month, budget_data.year)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un presupuesto para {budget_data.month}/{budget_data.year}"
            )
        
        # Verificar que todas las categorías existan
        for item in budget_data.items:
            category = db.query(Category).filter(Category.id == item.category_id).first()
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Categoría {item.category_id} no encontrada"
                )
        
        # Crear presupuesto
        budget = Budget(
            user_id=current_user.id,
            month=budget_data.month,
            year=budget_data.year,
            name=budget_data.name,
            total_budget=0
        )
        
        db.add(budget)
        db.flush()  # Para obtener el ID del presupuesto
        
        # Crear partidas
        for item_data in budget_data.items:
            budget_item = BudgetItem(
                budget_id=budget.id,
                category_id=item_data.category_id,
                allocated_amount=item_data.allocated_amount,
                notes=item_data.notes
            )
            db.add(budget_item)
        
        db.flush()
        
        # Recalcular total
        budget.recalculate_total()
        
        db.commit()
        db.refresh(budget)
        
        # Enriquecer items con nombre de categoría
        for item in budget.items:
            item.category_name = item.category.name
        
        logger.info(f"Usuario {current_user.id} creó presupuesto {budget.id} para {budget_data.month}/{budget_data.year}")
        return BudgetResponse.model_validate(budget)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear presupuesto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear presupuesto: {str(e)}"
        )


@router.post("/copy/{budget_id}", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def copy_budget(
    budget_id: UUID,
    copy_data: BudgetCopyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Copiar un presupuesto existente a un nuevo mes
    
    **Body:**
    ```json
    {
      "target_month": 3,
      "target_year": 2025
    }
    ```
    """
    try:
        # Obtener presupuesto origen
        source_budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == current_user.id
        ).first()
        
        if not source_budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto origen no encontrado"
            )
        
        # Verificar que no exista presupuesto para el mes destino
        existing = Budget.get_budget_by_period(db, current_user.id, copy_data.target_month, copy_data.target_year)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un presupuesto para {copy_data.target_month}/{copy_data.target_year}"
            )
        
        # Crear nuevo presupuesto
        new_budget = Budget(
            user_id=current_user.id,
            month=copy_data.target_month,
            year=copy_data.target_year,
            name=source_budget.name,
            total_budget=source_budget.total_budget
        )
        
        db.add(new_budget)
        db.flush()
        
        # Copiar partidas
        for source_item in source_budget.items:
            new_item = BudgetItem(
                budget_id=new_budget.id,
                category_id=source_item.category_id,
                allocated_amount=source_item.allocated_amount,
                notes=source_item.notes
            )
            db.add(new_item)
        
        db.commit()
        db.refresh(new_budget)
        
        # Enriquecer items con nombre de categoría
        for item in new_budget.items:
            item.category_name = item.category.name
        
        logger.info(f"Usuario {current_user.id} copió presupuesto {budget_id} a {copy_data.target_month}/{copy_data.target_year}")
        return BudgetResponse.model_validate(new_budget)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al copiar presupuesto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al copiar presupuesto: {str(e)}"
        )


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: UUID,
    budget_data: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Actualizar un presupuesto existente
    """
    try:
        budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == current_user.id
        ).first()
        
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado"
            )
        
        # Actualizar campos básicos
        if budget_data.month is not None:
            budget.month = budget_data.month
        if budget_data.year is not None:
            budget.year = budget_data.year
        if budget_data.name is not None:
            budget.name = budget_data.name
        
        # Si se envían items, reemplazar todos
        if budget_data.items is not None:
            # Verificar que todas las categorías existan
            for item in budget_data.items:
                category = db.query(Category).filter(Category.id == item.category_id).first()
                if not category:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Categoría {item.category_id} no encontrada"
                    )
            
            # Eliminar items existentes
            db.query(BudgetItem).filter(BudgetItem.budget_id == budget_id).delete()
            
            # Crear nuevos items
            for item_data in budget_data.items:
                budget_item = BudgetItem(
                    budget_id=budget.id,
                    category_id=item_data.category_id,
                    allocated_amount=item_data.allocated_amount,
                    notes=item_data.notes
                )
                db.add(budget_item)
            
            db.flush()
            budget.recalculate_total()
        
        db.commit()
        db.refresh(budget)
        
        # Enriquecer items con nombre de categoría
        for item in budget.items:
            item.category_name = item.category.name
        
        logger.info(f"Usuario {current_user.id} actualizó presupuesto {budget_id}")
        return BudgetResponse.model_validate(budget)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al actualizar presupuesto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar presupuesto: {str(e)}"
        )


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Eliminar un presupuesto
    
    Las partidas asociadas se eliminarán automáticamente (CASCADE)
    """
    try:
        budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == current_user.id
        ).first()
        
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado"
            )
        
        db.delete(budget)
        db.commit()
        
        logger.info(f"Usuario {current_user.id} eliminó presupuesto {budget_id}")
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar presupuesto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar presupuesto: {str(e)}"
        )


@router.get("/{budget_id}/overspent", response_model=List[OverspentCategory])
async def get_overspent_categories_endpoint(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener categorías que han superado su presupuesto
    """
    try:
        # Verificar que el presupuesto pertenece al usuario
        budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == current_user.id
        ).first()
        
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado"
            )
        
        overspent = get_overspent_categories(db, budget_id)
        
        logger.info(f"Usuario {current_user.id} consultó categorías excedidas de presupuesto {budget_id}")
        return overspent
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener categorías excedidas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener categorías excedidas: {str(e)}"
        )


@router.get("/suggest/{month}/{year}", response_model=SuggestedBudget)
async def suggest_budget(
    month: int = Path(..., ge=1, le=12, description="Mes objetivo"),
    year: int = Path(..., ge=2000, le=2100, description="Año objetivo"),
    months_back: int = Query(3, ge=1, le=12, description="Meses hacia atrás a analizar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Sugerir presupuesto basado en histórico de gastos
    
    **Ejemplo:**
    ```
    GET /api/budgets/suggest/3/2025?months_back=3
    ```
    """
    try:
        suggested = suggest_budget_from_history(db, current_user.id, month, year, months_back)
        
        logger.info(f"Usuario {current_user.id} solicitó sugerencia de presupuesto para {month}/{year}")
        return suggested
        
    except Exception as e:
        logger.error(f"Error al sugerir presupuesto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al sugerir presupuesto: {str(e)}"
        )


@router.get("/compare/{budget_id_1}/{budget_id_2}", response_model=BudgetComparison)
async def compare_budgets_endpoint(
    budget_id_1: UUID,
    budget_id_2: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Comparar dos presupuestos
    """
    try:
        # Verificar que ambos presupuestos pertenecen al usuario
        budget1 = db.query(Budget).filter(
            Budget.id == budget_id_1,
            Budget.user_id == current_user.id
        ).first()
        
        budget2 = db.query(Budget).filter(
            Budget.id == budget_id_2,
            Budget.user_id == current_user.id
        ).first()
        
        if not budget1 or not budget2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uno o ambos presupuestos no encontrados"
            )
        
        comparison = compare_budgets(db, budget_id_1, budget_id_2)
        
        logger.info(f"Usuario {current_user.id} comparó presupuestos {budget_id_1} y {budget_id_2}")
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al comparar presupuestos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al comparar presupuestos: {str(e)}"
        )


@router.put("/items/{item_id}", response_model=BudgetItemResponse)
async def update_budget_item(
    item_id: UUID,
    item_update: BudgetItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Actualizar un item de presupuesto
    
    **Parámetros:**
    - item_id: UUID del item a actualizar
    - item_update: Datos actualizados del item
    
    **Ejemplo Request:**
    ```json
    {
      "category_id": "uuid-categoria",
      "allocated_amount": 500.00,
      "notes": "Presupuesto actualizado para alimentación"
    }
    ```
    
    **Response:**
    ```json
    {
      "id": "uuid",
      "budget_id": "uuid",
      "category_id": "uuid",
      "allocated_amount": 500.00,
      "notes": "Presupuesto actualizado para alimentación",
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-15T14:30:00Z"
    }
    ```
    """
    try:
        # Buscar el item
        budget_item = db.query(BudgetItem).filter(BudgetItem.id == item_id).first()
        
        if not budget_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de presupuesto no encontrado"
            )
        
        # Verificar que el presupuesto pertenece al usuario
        budget = db.query(Budget).filter(
            Budget.id == budget_item.budget_id,
            Budget.user_id == current_user.id
        ).first()
        
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar este item"
            )
        
        # Actualizar campos
        if item_update.category_id is not None:
            budget_item.category_id = item_update.category_id
        if item_update.allocated_amount is not None:
            budget_item.allocated_amount = item_update.allocated_amount
        if item_update.notes is not None:
            budget_item.notes = item_update.notes
        
        budget_item.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(budget_item)
        
        logger.info(f"Usuario {current_user.id} actualizó item de presupuesto {item_id}")
        return budget_item
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al actualizar item de presupuesto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar item de presupuesto: {str(e)}"
        )

