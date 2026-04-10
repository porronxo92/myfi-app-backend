"""
Schemas para el Agente Conversacional (Chat)
=============================================

Define los tipos de entrada/salida para el endpoint /api/insights/chat
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """
    Mensaje individual en el historial de conversación.

    Attributes:
        role: "user" para mensajes del usuario, "assistant" para respuestas del agente
        content: Contenido del mensaje (máximo 4000 caracteres)
    """
    role: str = Field(..., pattern="^(user|assistant)$", description="Rol del mensaje")
    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Contenido del mensaje (máx 4000 caracteres)"
    )


class ProposedAction(BaseModel):
    """
    Acción propuesta por el agente que requiere confirmación del usuario.

    El frontend debe mostrar un modal de confirmación antes de ejecutar.
    Si el usuario confirma, el frontend llama directamente al endpoint especificado.

    Attributes:
        type: Tipo de acción CRUD
        description: Descripción legible para mostrar al usuario en el modal
        endpoint: Endpoint a llamar si el usuario confirma (ej: "POST /api/transactions")
        data: Payload listo para enviar al endpoint

    Tipos de acción disponibles:
        - Transacciones: create_transaction, update_transaction, delete_transaction
        - Categorías: create_category, update_category, delete_category
        - Cuentas: create_account, update_account, delete_account
    """
    type: str = Field(
        ...,
        pattern="^(create_transaction|update_transaction|delete_transaction|create_category|update_category|delete_category|create_account|update_account|delete_account|create_accounts_batch|create_categories_batch|create_transactions_batch)$",
        description="Tipo de acción CRUD a ejecutar (incluye opciones batch para múltiples items)"
    )
    description: str = Field(
        ...,
        description="Descripción legible de la acción para mostrar al usuario"
    )
    endpoint: str = Field(
        ...,
        description="Endpoint HTTP a llamar (ej: POST /api/transactions)"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Payload completo para enviar al endpoint"
    )


class ChatRequest(BaseModel):
    """
    Request para enviar un mensaje al agente.

    El frontend debe mantener el historial de conversación en memoria
    y enviarlo completo en cada request.

    Example:
        {
            "message": "¿Cuánto he gastado este mes?",
            "conversation_history": [
                {"role": "user", "content": "Hola"},
                {"role": "assistant", "content": "¡Hola! Soy MyFi..."}
            ]
        }
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Mensaje actual del usuario"
    )
    conversation_history: List[ChatMessage] = Field(
        default=[],
        max_length=50,  # Límite para evitar contextos muy largos
        description="Historial de mensajes previos (mantenido por el frontend)"
    )


class ChatResponse(BaseModel):
    """
    Response del agente conversacional.

    Attributes:
        message: Respuesta textual del agente
        proposed_action: Acción propuesta (null si solo es respuesta informativa)
        suggested_questions: Preguntas sugeridas para continuar la conversación
        timestamp: Timestamp de la respuesta

    Example (respuesta informativa):
        {
            "message": "Este mes has gastado 234,50€ en Supermercado.",
            "proposed_action": null,
            "suggested_questions": ["¿Cuáles son mis mayores gastos?", ...]
        }

    Example (con acción propuesta):
        {
            "message": "Voy a registrar el gasto. Confirma antes de guardar.",
            "proposed_action": {
                "type": "create_transaction",
                "description": "Crear gasto de -45€ en Mercadona",
                "endpoint": "POST /api/transactions",
                "data": { ... }
            },
            "suggested_questions": []
        }
    """
    message: str = Field(..., description="Respuesta del agente")
    proposed_action: Optional[ProposedAction] = Field(
        default=None,
        description="Acción propuesta que requiere confirmación (null si no hay)"
    )
    suggested_questions: List[str] = Field(
        default=[],
        max_length=5,
        description="Preguntas sugeridas para continuar la conversación"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp de la respuesta"
    )


class ChatErrorResponse(BaseModel):
    """
    Estructura de error para el chat.

    Example (quota excedida - HTTP 429):
        {
            "detail": {
                "message": "Has alcanzado tu límite diario de 20 consultas.",
                "used": 20,
                "limit": 20,
                "reset_date": "2026-04-02"
            }
        }
    """
    detail: Dict[str, Any]
