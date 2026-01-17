"""
Health Routes
=============

Endpoints para análisis de salud financiera con IA.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database import get_db
from app.utils.security import get_current_user
from app.models.user import User
from app.services import health_service

router = APIRouter(prefix="/api/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/financial-report")
async def generate_financial_health_report(
    year: int = Query(..., description="Año para analizar"),
    account_id: Optional[str] = Query(None, description="ID de cuenta específica (opcional)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Genera un informe de salud financiera completo usando Gemini AI.
    
    Este endpoint:
    1. Recopila datos financieros del usuario para el año especificado
    2. Genera un prompt estructurado con toda la información
    3. Envía el prompt a Gemini para análisis
    4. Retorna un informe completo con puntuación, fortalezas, debilidades, alertas y recomendaciones
    
    Args:
        year: Año para analizar (ej: 2025)
        account_id: UUID de cuenta específica (opcional, si no se proporciona analiza todas las cuentas)
        current_user: Usuario autenticado
        db: Sesión de base de datos
    
    Returns:
        {
            "health_score": 75,
            "score_category": "buena",
            "summary": {
                "main_insight": "Tu salud financiera es buena con una tasa de ahorro del 23%",
                "period_analyzed": "Año 2025"
            },
            "strengths": ["Tasa de ahorro superior al promedio", ...],
            "weaknesses": ["Gastos en entretenimiento aumentaron 15%", ...],
            "alerts": [...],
            "recommendations": [...],
            "predictions": {...}
        }
    """
    try:
        logger.info(f"Generando informe de salud financiera para user_id={current_user.id}, year={year}, account_id={account_id}")
        
        # Generar informe usando el servicio
        health_report = await health_service.generate_health_report(
            db=db,
            user_id=str(current_user.id),
            year=year,
            account_id=account_id
        )
        
        return health_report
        
    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generando informe de salud: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error al generar el informe de salud financiera"
        )
