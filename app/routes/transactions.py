"""
Endpoints CRUD para Transactions
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date
import math

from app.database import get_db
from app.schemas import TransactionCreate, TransactionUpdate, TransactionResponse, PaginatedResponse
from app.services import TransactionService
from app.utils.security import get_current_user, check_rate_limit
from app.models import User
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/transactions",
    tags=["transactions"]
)


@router.get("", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    account_id: Optional[UUID] = Query(None, description="Filtrar por cuenta"),
    category_id: Optional[UUID] = Query(None, description="Filtrar por categoría"),
    type: Optional[str] = Query(None, pattern="^(income|expense|transfer)$", description="Filtrar por tipo"),
    date_from: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    min_amount: Optional[float] = Query(None, description="Monto mínimo"),
    max_amount: Optional[float] = Query(None, description="Monto máximo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Listar transacciones del usuario autenticado con filtros y paginación
    
    **Parámetros:**
    - page: Número de página
    - page_size: Registros por página (max: 100)
    - account_id: UUID de la cuenta
    - category_id: UUID de la categoría
    - type: Tipo de transacción (income/expense/transfer)
    - date_from: Fecha inicio (formato: YYYY-MM-DD)
    - date_to: Fecha fin (formato: YYYY-MM-DD)
    - min_amount: Monto mínimo
    - max_amount: Monto máximo
    
    **Ejemplo:**
    ```
    GET /api/transactions?page=1&page_size=20&type=expense&date_from=2025-01-01&date_to=2025-01-31
    ```
    
    **Response:**
    ```json
    {
      "items": [
        {
          "id": "uuid",
          "account_id": "uuid-cuenta",
          "date": "2025-01-15",
          "amount": -50.00,
          "description": "Mercadona",
          "type": "expense",
          "account_name": "Cuenta Bankinter",
          "category_name": "Supermercado",
          "category_color": "#EF4444"
        }
      ],
      "total": 150,
      "page": 1,
      "page_size": 20,
      "total_pages": 8
    }
    ```
    """
    logger.info(f"Listando transacciones para user {current_user.email}: page={page}, filtros aplicados")
    
    skip = (page - 1) * page_size
    
    transactions = TransactionService.get_all(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=page_size,
        account_id=account_id,
        category_id=category_id,
        transaction_type=type,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount
    )
    
    total = TransactionService.get_total_count(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        transaction_type=type,
        date_from=date_from,
        date_to=date_to
    )
    
    return PaginatedResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener transacción del usuario por ID
    
    **Response:**
    ```json
    {
      "id": "uuid",
      "account_id": "uuid-cuenta",
      "date": "2025-01-15",
      "amount": -50.00,
      "description": "Mercadona - Compra mensual",
      "category_id": "uuid-categoria",
      "type": "expense",
      "notes": "Incluye productos de limpieza",
      "tags": ["alimentación", "hogar"],
      "source": "manual",
      "account_name": "Cuenta Bankinter",
      "category_name": "Supermercado",
      "category_color": "#EF4444"
    }
    ```
    """
    logger.info(f"Obteniendo transacción {transaction_id} para user {current_user.email}")
    
    transaction = TransactionService.get_by_id(db, transaction_id, current_user.id)
    if not transaction:
        logger.warning(f"Transacción no encontrada o no pertenece al usuario: {transaction_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transacción {transaction_id} no encontrada"
        )
    
    return TransactionResponse.model_validate(transaction)


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Crear nueva transacción para el usuario autenticado
    
    **El campo de categoría acepta DOS FORMATOS:**
    
    **Opción 1: Envío por UUID (comportamiento original)**
    ```json
    {
      "account_id": "uuid-cuenta",
      "date": "2025-01-15",
      "amount": -50.00,
      "description": "Mercadona",
      "category_id": "uuid-supermercado",
      "type": "expense",
      "notes": "Compra semanal",
      "tags": ["alimentación", "hogar"],
      "source": "manual"
    }
    ```
    
    **Opción 2: Envío por NOMBRE de categoría (nuevo)**
    ```json
    {
      "account_id": "uuid-cuenta",
      "date": "2025-01-15",
      "amount": -50.00,
      "description": "Mercadona",
      "category_id": "Alimentación",
      "type": "expense",
      "source": "automatico"
    }
    ```
    
    **Opción 3: Campo alternativo 'categoria'**
    ```json
    {
      "account_id": "uuid-cuenta",
      "categoria": "Alimentación",
      "date": "2025-01-15",
      "amount": -50.00,
      "description": "Mercadona",
      "type": "expense"
    }
    ```
    
    **Para transferencias:**
    ```json
    {
      "account_id": "uuid-cuenta-origen",
      "transfer_account_id": "uuid-cuenta-destino",
      "date": "2025-01-15",
      "amount": 100.00,
      "description": "Transferencia entre cuentas",
      "type": "transfer"
    }
    ```
    
    **Validaciones:**
    - amount != 0
    - date no puede ser futura
    - Si type=transfer, requiere transfer_account_id
    - transfer_account_id != account_id
    - **Si category_id es string**: Búsqueda case-insensitive, con trim automático
    - **Si categoría no existe**: Error 400 con mensaje descriptivo
    - **source**: Valores permitidos: "manual", "automatico", "import", "api" (default: "manual")
    
    **Códigos de Error:**
    - **400**: `{"detail": "Categoría 'NombreInexistente' no encontrada"}`
    - **400**: `{"detail": "La cuenta no existe o no pertenece al usuario"}`
    - **400**: `{"detail": "El monto no puede ser cero"}`
    
    **Response:** 201 Created con los datos de la transacción creada
    
    **Nota:** 
    - El balance de la cuenta se actualiza automáticamente
    - La búsqueda por nombre ignora mayúsculas/minúsculas
    - Se aplica trim automático a los nombres de categoría
    """
    logger.info(f"Creando nueva transacción para user {current_user.email}: {transaction_data.description}")
    
    try:
        transaction = TransactionService.create(db, transaction_data, current_user.id)
        logger.info(f"Transacción creada exitosamente: {transaction.id}")
        return TransactionResponse.model_validate(transaction)
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al crear transacción: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    transaction_data: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Actualizar transacción del usuario
    
    **Request Body (todos los campos son opcionales):**
    ```json
    {
      "amount": -55.00,
      "category_id": "uuid-otra-categoria",
      "notes": "Actualizado: incluye productos extras"
    }
    ```
    
    **Response:** 200 OK con los datos actualizados
    
    **Nota:** Si cambias el amount, el balance de la cuenta se ajusta automáticamente
    """
    logger.info(f"Actualizando transacción {transaction_id} para user {current_user.email}")
    
    try:
        transaction = TransactionService.update(db, transaction_id, current_user.id, transaction_data)
        if not transaction:
            logger.warning(f"Transacción no encontrada o no pertenece al usuario: {transaction_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transacción {transaction_id} no encontrada"
            )
        
        logger.info(f"Transacción actualizada exitosamente: {transaction.id}")
        return TransactionResponse.model_validate(transaction)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar transacción: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Eliminar transacción del usuario
    
    **Response:** 204 No Content si se eliminó correctamente
    
    **Nota:** El balance de la cuenta se ajusta automáticamente (revierte el monto)
    """
    logger.info(f"Eliminando transacción {transaction_id} para user {current_user.email}")
    
    deleted = TransactionService.delete(db, transaction_id, current_user.id)
    if not deleted:
        logger.warning(f"Transacción no encontrada o no pertenece al usuario: {transaction_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transacción {transaction_id} no encontrada"
        )
    
    logger.info(f"Transacción eliminada exitosamente: {transaction_id}")
    return None


@router.get("/stats/summary", response_model=dict)
async def get_transactions_summary(
    account_id: Optional[UUID] = Query(None, description="Filtrar por cuenta"),
    date_from: Optional[date] = Query(None, description="Fecha inicio"),
    date_to: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener resumen de transacciones del usuario (ingresos, gastos, balance)
    
    **Parámetros:**
    - account_id: Filtrar por cuenta específica
    - date_from: Fecha inicio (YYYY-MM-DD)
    - date_to: Fecha fin (YYYY-MM-DD)
    
    **Ejemplo:**
    ```
    GET /api/transactions/stats/summary?date_from=2025-01-01&date_to=2025-01-31
    ```
    
    **Response:**
    ```json
    {
      "total_income": 3500.00,
      "total_expense": 2150.50,
      "balance": 1349.50
    }
    ```
    """
    logger.info(f"Obteniendo resumen de transacciones para user {current_user.email}: account={account_id}, desde={date_from}, hasta={date_to}")
    
    summary = TransactionService.get_summary(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to
    )
    
    return summary
