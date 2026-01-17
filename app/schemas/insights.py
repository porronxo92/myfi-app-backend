"""
Schemas para Insights - Respuestas de IA
========================================

Modelos Pydantic para las respuestas de Gemini AI.
Estos schemas definen insights, recomendaciones y análisis cualitativos.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class InsightType(str, Enum):
    """Tipos de insights."""
    ALERT = "alert"              # Alerta/advertencia
    POSITIVE = "positive"        # Feedback positivo
    NEUTRAL = "neutral"          # Observación neutral
    RECOMMENDATION = "recommendation"  # Recomendación accionable
    PREDICTION = "prediction"    # Predicción/proyección


class InsightPriority(str, Enum):
    """Prioridad del insight."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InsightAction(BaseModel):
    """Acción sugerida asociada a un insight."""
    label: str = Field(..., description="Texto del botón/enlace")
    route: Optional[str] = Field(None, description="Ruta del frontend (ej: '/transactions?category=Ocio')")
    external_url: Optional[str] = Field(None, description="URL externa si aplica")
    action_type: str = Field(default="navigate", description="'navigate', 'external', 'modal'")


class FinancialInsight(BaseModel):
    """Un insight financiero individual."""
    id: str = Field(..., description="ID único del insight")
    type: InsightType
    priority: InsightPriority
    icon: str = Field(..., description="Emoji o código de icono")
    title: str = Field(..., min_length=5, max_length=100)
    message: str = Field(..., min_length=10, max_length=500, description="Mensaje principal")
    data_point: Optional[Dict[str, Any]] = Field(None, description="Datos relevantes asociados")
    action: Optional[InsightAction] = Field(None, description="Acción sugerida")
    generated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "insight-123",
                "type": "alert",
                "priority": "high",
                "icon": "⚠️",
                "title": "Incremento Significativo en Gastos",
                "message": "Tus gastos en 'Ocio/Deporte' son un 60% superiores este mes (€1,019 vs €637 promedio).",
                "data_point": {
                    "category": "Ocio/Deporte",
                    "current": 1019.00,
                    "average": 637.00,
                    "increase_pct": 60.0
                },
                "action": {
                    "label": "Ver detalle",
                    "route": "/transactions?category=Ocio",
                    "action_type": "navigate"
                },
                "generated_at": "2025-01-09T10:30:00Z"
            }
        }


class FinancialHealthScore(BaseModel):
    """Puntuación de salud financiera."""
    overall_score: int = Field(..., ge=0, le=100, description="Puntuación general (0-100)")
    category_scores: Dict[str, int] = Field(..., description="Puntuaciones por categoría")
    grade: str = Field(..., description="'A', 'B', 'C', 'D', 'F'")
    summary: str = Field(..., description="Resumen de la evaluación")


class FinancialHealthResponse(BaseModel):
    """Respuesta de análisis de salud financiera."""
    user_id: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    health_score: FinancialHealthScore
    insights: List[FinancialInsight] = Field(..., description="3-5 insights principales")
    strengths: List[str] = Field(..., description="Fortalezas identificadas")
    areas_of_improvement: List[str] = Field(..., description="Áreas a mejorar")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "analyzed_at": "2025-01-09T10:30:00Z",
                "health_score": {
                    "overall_score": 75,
                    "category_scores": {
                        "savings_rate": 80,
                        "debt_management": 90,
                        "spending_control": 60,
                        "income_stability": 85
                    },
                    "grade": "B",
                    "summary": "Tu salud financiera es buena, con margen de mejora en control de gastos."
                },
                "insights": [],
                "strengths": ["Excelente tasa de ahorro", "Ingresos estables"],
                "areas_of_improvement": ["Reducir gastos en ocio", "Eliminar suscripciones no usadas"]
            }
        }


class SpendingRecommendation(BaseModel):
    """Recomendación específica de gasto."""
    category: str
    current_spending: float
    recommended_spending: float
    potential_savings: float
    reasoning: str = Field(..., description="Justificación de la recomendación")
    difficulty: str = Field(..., description="'easy', 'moderate', 'hard'")


class RecommendationsResponse(BaseModel):
    """Respuesta con recomendaciones de optimización."""
    user_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    total_potential_savings: float
    recommendations: List[SpendingRecommendation]
    quick_wins: List[str] = Field(..., description="Acciones rápidas y fáciles")
    long_term_strategies: List[str] = Field(..., description="Estrategias a largo plazo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "generated_at": "2025-01-09T10:30:00Z",
                "total_potential_savings": 350.00,
                "recommendations": [
                    {
                        "category": "Suscripciones",
                        "current_spending": 85.00,
                        "recommended_spending": 40.00,
                        "potential_savings": 45.00,
                        "reasoning": "Detectamos 3 suscripciones con bajo uso. Cancela las que no uses.",
                        "difficulty": "easy"
                    }
                ],
                "quick_wins": ["Cancelar Spotify duplicado (€9.99/mes)", "Reducir salidas a restaurantes"],
                "long_term_strategies": ["Establecer presupuesto mensual por categoría", "Automatizar ahorros"]
            }
        }


class MonthlyOutlookPrediction(BaseModel):
    """Predicción de cierre de mes."""
    predicted_income: float
    predicted_expenses: float
    predicted_balance: float
    confidence: str = Field(..., description="'high', 'medium', 'low'")
    assumptions: List[str] = Field(..., description="Supuestos de la predicción")


class MonthlyOutlookResponse(BaseModel):
    """Respuesta con predicción de mes actual."""
    user_id: str
    current_month: str = Field(..., description="Formato YYYY-MM")
    days_remaining: int
    current_status: Dict[str, float] = Field(..., description="Situación actual del mes")
    prediction: MonthlyOutlookPrediction
    alerts: List[str] = Field(..., description="Alertas si se detectan problemas")
    advice: str = Field(..., description="Consejo general para el resto del mes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "current_month": "2025-01",
                "days_remaining": 22,
                "current_status": {
                    "income_so_far": 1200.00,
                    "expenses_so_far": 850.00,
                    "balance_so_far": 350.00
                },
                "prediction": {
                    "predicted_income": 2500.00,
                    "predicted_expenses": 1900.00,
                    "predicted_balance": 600.00,
                    "confidence": "high",
                    "assumptions": ["Ingresos similares a meses anteriores", "Patrón de gasto actual se mantiene"]
                },
                "alerts": ["Gastos en ocio ya alcanzaron el 80% del promedio mensual"],
                "advice": "Mantén el ritmo actual de gastos para cumplir tu objetivo de ahorro."
            }
        }


class SavingsGoal(BaseModel):
    """Meta de ahorro."""
    target_amount: float
    current_savings: float
    months_to_achieve: int
    monthly_savings_needed: float


class SavingsPlanStep(BaseModel):
    """Paso del plan de ahorro."""
    step_number: int
    action: str
    expected_savings: float
    timeframe: str = Field(..., description="'immediate', 'short-term', 'long-term'")


class SavingsPlanResponse(BaseModel):
    """Respuesta con plan de ahorro personalizado."""
    user_id: str
    goal: SavingsGoal
    plan_steps: List[SavingsPlanStep]
    feasibility: str = Field(..., description="'very_feasible', 'feasible', 'challenging', 'unrealistic'")
    alternative_suggestions: List[str] = Field(..., description="Sugerencias alternativas si es muy difícil")
    motivational_message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "goal": {
                    "target_amount": 5000.00,
                    "current_savings": 1200.00,
                    "months_to_achieve": 12,
                    "monthly_savings_needed": 316.67
                },
                "plan_steps": [
                    {
                        "step_number": 1,
                        "action": "Cancelar suscripciones no usadas",
                        "expected_savings": 45.00,
                        "timeframe": "immediate"
                    }
                ],
                "feasibility": "feasible",
                "alternative_suggestions": [],
                "motivational_message": "Con disciplina y estos pequeños ajustes, alcanzarás tu meta en 12 meses."
            }
        }


class CustomAnalysisRequest(BaseModel):
    """Request para análisis personalizado."""
    question: str = Field(..., min_length=5, description="Pregunta del usuario")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional opcional")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "¿En qué categoría puedo reducir más gastos?",
                "context": {
                    "focus_period": "current_month",
                    "target_savings": 200
                }
            }
        }


class CustomAnalysisResponse(BaseModel):
    """Respuesta a análisis personalizado."""
    user_id: str
    question: str = Field(..., description="Pregunta original del usuario")
    answer: str = Field(..., description="Respuesta generada por Gemini")
    supporting_data: Optional[Dict[str, Any]] = Field(None, description="Datos que respaldan la respuesta")
    related_insights: List[FinancialInsight] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(..., description="Preguntas sugeridas para profundizar")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "question": "¿Por qué gasté más este mes?",
                "answer": "Tus gastos aumentaron principalmente por un incremento del 45% en 'Ocio/Deporte' (€1,019 vs €703 promedio). Esto incluye 3 compras grandes en gimnasio y material deportivo.",
                "supporting_data": {
                    "category": "Ocio/Deporte",
                    "increase": 316.00,
                    "key_transactions": ["Renovación gimnasio anual", "Bicicleta nueva", "Ropa deportiva"]
                },
                "related_insights": [],
                "follow_up_questions": [
                    "¿Cómo puedo reducir mis gastos en ocio?",
                    "¿Cuánto ahorro si cancelo alguna suscripción?"
                ]
            }
        }


class CombinedAnalyticsInsightsResponse(BaseModel):
    """Respuesta combinada con analytics + insights para dashboard."""
    analytics: Dict[str, Any] = Field(..., description="Datos cuantitativos (analytics)")
    insights: List[FinancialInsight] = Field(..., description="Insights generados por IA")
    health_score: Optional[FinancialHealthScore] = None
    quick_stats: Dict[str, Any] = Field(..., description="Estadísticas rápidas para hero section")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analytics": {
                    "summary": {"total_income": 2500, "total_expenses": 1800},
                    "categories": [],
                    "trends": []
                },
                "insights": [
                    {
                        "id": "insight-1",
                        "type": "positive",
                        "priority": "medium",
                        "icon": "✅",
                        "title": "Excelente Control",
                        "message": "Has reducido tus gastos un 15% este mes.",
                        "data_point": None,
                        "action": None,
                        "generated_at": "2025-01-09T10:30:00Z"
                    }
                ],
                "health_score": None,
                "quick_stats": {
                    "balance_vs_last_month": "+12.5%",
                    "savings_rate": 28.0,
                    "top_category": "Alimentación"
                }
            }
        }
