"""
Schemas para cuota de Gemini API
"""

from pydantic import BaseModel, Field
from datetime import date


class GeminiQuotaResponse(BaseModel):
    """
    Respuesta del endpoint GET /api/users/me/gemini-quota

    Response:
    {
      "used": 5,
      "remaining": 15,
      "limit": 20,
      "reset_date": "2026-04-02",
      "percentage_used": 25.0
    }
    """
    used: int = Field(..., description="Peticiones usadas hoy")
    remaining: int = Field(..., description="Peticiones restantes hoy")
    limit: int = Field(..., description="Límite diario configurado")
    reset_date: date = Field(..., description="Fecha del próximo reset (mañana)")
    percentage_used: float = Field(..., description="Porcentaje de cuota usada")

    model_config = {
        "json_schema_extra": {
            "example": {
                "used": 5,
                "remaining": 15,
                "limit": 20,
                "reset_date": "2026-04-02",
                "percentage_used": 25.0
            }
        }
    }
