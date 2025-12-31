# ============================================
# SCHEMAS PARA UPLOAD
# ============================================

from pydantic import BaseModel, Field
from pydantic.types import UUID4
from typing import List, Optional
from datetime import date


class AccountInfoSchema(BaseModel):
    """
    Información de la cuenta extraída del PDF
    """
    account_name: str
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    statement_month: str  # "2025-01"
    initial_balance: float = 0.0
    final_balance: float = 0.0

class TransactionPreview(BaseModel):
    """
    Transacción parseada por el LLM (para preview)
    """
    date: date
    amount: float
    description: str
    category: str  # Nombre legible
    category_id: Optional[UUID4] = None  # UUID después de mapear
    type: str
    notes: Optional[str] = ""

class PreviewResponse(BaseModel):
    """
    Respuesta de POST /api/upload/extract
    
    El usuario ve esto ANTES de confirmar la importación
    
    Response:
    {
      "filename": "enero25.pdf",
      "account_info": {
        "account_name": "Cuenta Bankinter",
        "statement_month": "2025-01",
        "initial_balance": 11404.20,
        "final_balance": 11799.21
      },
      "transactions": [
        {
          "date": "2025-01-02",
          "amount": -28.00,
          "description": "PAGO BIZUM A MARIA",
          "category": "Bizum",
          "category_id": "uuid-bizum",
          "type": "expense"
        },
        // ... más
      ],
      "total_transactions": 37,
      "message": "Revisa y confirma la importación"
    }
    """
    filename: str
    account_info: AccountInfoSchema
    transactions: List[TransactionPreview]
    total_transactions: int
    message: str

# ============================================
# SCHEMAS PARA IMPORT (confirmación)
# ============================================

class TransactionImport(BaseModel):
    """
    Transacción confirmada para importar
    (viene del preview pero puede estar editada por el usuario)
    """
    date: date
    amount: float
    description: str
    category_id: UUID4
    type: str
    notes: Optional[str] = ""

class ImportRequest(BaseModel):
    """
    Request de POST /api/upload/import
    
    Request:
    {
      "account_id": "uuid-cuenta-destino",
      "transactions": [
        { "date": "2025-01-02", "amount": -28.00, ... },
        { "date": "2025-01-03", "amount": 1200.00, ... }
      ]
    }
    """
    account_id: UUID4
    transactions: List[TransactionImport]

class ImportResponse(BaseModel):
    """
    Response de POST /api/upload/import
    
    Response:
    {
      "success": true,
      "imported_count": 37,
      "skipped_count": 3,    # Duplicados
      "errors": [],
      "new_balance": 11799.21,
      "message": "Importación completada: 37 transacciones añadidas"
    }
    """
    success: bool
    imported_count: int
    skipped_count: int
    errors: List[str] = []
    new_balance: float
    message: str