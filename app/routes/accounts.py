"""
Endpoints CRUD para Accounts
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import math

from app.database import get_db
from app.schemas import AccountCreate, AccountUpdate, AccountResponse, PaginatedResponse
from app.services import AccountService
from app.utils.security import get_current_user, check_rate_limit
from app.utils.logger import get_logger
from app.models import User

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"]
)


@router.get("", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Listar cuentas del usuario autenticado con paginación
    
    **Parámetros:**
    - page: Número de página (default: 1)
    - page_size: Registros por página (default: 20, max: 100)
    - is_active: Filtrar por estado (true/false/null=todos)
    
    **Response:**
    ```json
    {
      "items": [...],
      "total": 45,
      "page": 1,
      "page_size": 20,
      "total_pages": 3
    }
    ```
    """
    logger.info(f"Listando cuentas para user_id: {current_user.id}, page={page}, page_size={page_size}, is_active={is_active}")
    
    # Calcular offset
    skip = (page - 1) * page_size
    
    # Obtener cuentas del usuario y total
    accounts = AccountService.get_all(db, user_id=current_user.id, skip=skip, limit=page_size, is_active=is_active)
    total = AccountService.get_total_count(db, user_id=current_user.id, is_active=is_active)
    
    return PaginatedResponse(
        items=[AccountResponse.model_validate(acc) for acc in accounts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener cuenta por ID (solo si pertenece al usuario autenticado)
    
    **Parámetros:**
    - account_id: UUID de la cuenta
    
    **Response:**
    ```json
    {
      "id": "uuid",
      "name": "Cuenta Bankinter",
      "type": "checking",
      "balance": 2500.00,
      "currency": "EUR",
      ...
    }
    ```
    """
    logger.info(f"Obteniendo cuenta: {account_id} para user_id: {current_user.id}")
    
    account = AccountService.get_by_id(db, account_id, user_id=current_user.id)
    if not account:
        logger.warning(f"Cuenta no encontrada o no pertenece al usuario: {account_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta {account_id} no encontrada"
        )
    
    return AccountResponse.model_validate(account)


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Crear nueva cuenta para el usuario autenticado
    
    **Request Body:**
    ```json
    {
      "name": "Cuenta ING",
      "type": "checking",
      "balance": 1000.00,
      "currency": "EUR",
      "bank_name": "ING",
      "account_number": "ES12 3456 7890 1234 5678 9012",
      "is_active": true,
      "notes": "Cuenta principal"
    }
    ```
    
    **Response:** 201 Created con los datos de la cuenta creada
    """
    logger.info(f"Creando nueva cuenta: {account_data.name} para user_id: {current_user.id}")
    
    try:
        # Asignar la cuenta al usuario actual
        account_dict = account_data.model_dump()
        account_dict['user_id'] = current_user.id
        account_data_with_user = AccountCreate(**account_dict)
        
        account = AccountService.create(db, account_data_with_user)
        logger.info(f"Cuenta creada exitosamente: {account.id}")
        return AccountResponse.model_validate(account)
    except Exception as e:
        logger.error(f"Error al crear cuenta: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    account_data: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Actualizar cuenta existente (solo si pertenece al usuario autenticado)
    
    **Request Body (todos los campos son opcionales):**
    ```json
    {
      "name": "Cuenta ING Personal",
      "is_active": false,
      "notes": "Cerrada en enero 2025"
    }
    ```
    
    **Response:** 200 OK con los datos actualizados
    """
    logger.info(f"Actualizando cuenta: {account_id} para user_id: {current_user.id}")
    
    try:
        account = AccountService.update(db, account_id, user_id=current_user.id, account_data=account_data)
        if not account:
            logger.warning(f"Cuenta no encontrada para actualizar: {account_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuenta {account_id} no encontrada"
            )
        
        logger.info(f"Cuenta actualizada exitosamente: {account.id}")
        return AccountResponse.model_validate(account)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar cuenta: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Eliminar cuenta (solo si pertenece al usuario autenticado)
    
    **⚠️ ADVERTENCIA:** Esto eliminará también todas las transacciones asociadas (CASCADE)
    
    **Response:** 204 No Content si se eliminó correctamente
    """
    logger.info(f"Eliminando cuenta: {account_id} para user_id: {current_user.id}")
    
    deleted = AccountService.delete(db, account_id, user_id=current_user.id)
    if not deleted:
        logger.warning(f"Cuenta no encontrada para eliminar: {account_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta {account_id} no encontrada"
        )
    
    logger.info(f"Cuenta eliminada exitosamente: {account_id}")
    return None


@router.get("/stats/summary", response_model=dict)
async def get_accounts_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener resumen de cuentas del usuario autenticado
    
    **Response:**
    ```json
    {
      "total_accounts": 5,
      "active_accounts": 4,
      "inactive_accounts": 1,
      "total_balance": 15234.50
    }
    ```
    """
    logger.info(f"Obteniendo resumen de cuentas para user_id: {current_user.id}")
    
    total = AccountService.get_total_count(db, user_id=current_user.id)
    active = AccountService.get_total_count(db, user_id=current_user.id, is_active=True)
    inactive = AccountService.get_total_count(db, user_id=current_user.id, is_active=False)
    total_balance = AccountService.get_total_balance(db, user_id=current_user.id, is_active=True)
    
    return {
        "total_accounts": total,
        "active_accounts": active,
        "inactive_accounts": inactive,
        "total_balance": total_balance
    }
