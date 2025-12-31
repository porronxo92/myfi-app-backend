from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Schema genérico para respuestas paginadas
    
    Ejemplo de uso:
    
    @router.get("/api/transactions", response_model=PaginatedResponse[TransactionResponse])
    async def list_transactions(page: int = 1, page_size: int = 20):
        ...
        return PaginatedResponse(
            items=transactions,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total_count / page_size)
        )
    """
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
