"""
Schemas para Analytics - Respuestas estructuradas
=================================================

Modelos Pydantic para las respuestas de los endpoints de analytics.
Estos schemas definen la estructura de datos que el frontend recibirá.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


# ===== ENUMS =====

class TransactionType(str, Enum):
    """Tipo de transacción."""
    EXPENSE = "expense"
    INCOME = "income"


# ===== SCHEMAS DE RESPUESTA =====

class PeriodRange(BaseModel):
    """Rango de fechas de un período."""
    start: str = Field(..., description="Fecha de inicio (YYYY-MM-DD)")
    end: str = Field(..., description="Fecha de fin (YYYY-MM-DD)")


class MonthlySummaryResponse(BaseModel):
    """Resumen financiero mensual."""
    user_id: str
    period: str = Field(..., description="Ej: 'current_month', 'last_month'")
    period_range: PeriodRange
    total_income: float = Field(..., ge=0, description="Ingresos totales")
    total_expenses: float = Field(..., ge=0, description="Gastos totales")
    net_balance: float = Field(..., description="Balance neto (ingresos - gastos)")
    savings_rate: float = Field(..., description="Tasa de ahorro (%)")
    num_accounts: int = Field(..., ge=0)
    num_transactions: int = Field(..., ge=0)
    currency: str = Field(default="EUR")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "period": "current_month",
                "period_range": {"start": "2025-01-01", "end": "2025-01-31"},
                "total_income": 2500.00,
                "total_expenses": 1800.00,
                "net_balance": 700.00,
                "savings_rate": 28.0,
                "num_accounts": 3,
                "num_transactions": 45,
                "currency": "EUR"
            }
        }


class CategoryBreakdownItem(BaseModel):
    """Item de desglose por categoría."""
    category_id: str
    category_name: str
    color: Optional[str] = Field(None, description="Color hexadecimal para visualización")
    total: float = Field(..., description="Total gastado/ingresado")
    percentage: float = Field(..., ge=0, le=100, description="Porcentaje del total")
    num_transactions: int = Field(..., ge=0)
    avg_transaction: float = Field(..., description="Promedio por transacción")


class CategoryBreakdownResponse(BaseModel):
    """Desglose completo por categorías."""
    period: str
    period_range: PeriodRange
    transaction_type: str = Field(..., description="'income' o 'expense'")
    categories: List[CategoryBreakdownItem]
    total_amount: float = Field(..., description="Suma total de todas las categorías")
    
    class Config:
        json_schema_extra = {
            "example": {
                "period": "current_month",
                "period_range": {"start": "2025-01-01", "end": "2025-01-31"},
                "transaction_type": "expense",
                "categories": [
                    {
                        "category_id": "cat-123",
                        "category_name": "Alimentación",
                        "color": "#10B981",
                        "total": 450.50,
                        "percentage": 25.0,
                        "num_transactions": 12,
                        "avg_transaction": 37.54
                    }
                ],
                "total_amount": 1800.00
            }
        }


class MonthlyDataPoint(BaseModel):
    """Punto de datos para tendencia mensual."""
    month: str = Field(..., description="Formato YYYY-MM")
    income: float
    expenses: float
    balance: float


class TrendAnalysisResponse(BaseModel):
    """Análisis de tendencias temporales."""
    months: int = Field(..., description="Número de meses analizados")
    data_points: List[MonthlyDataPoint]
    avg_income: float = Field(..., description="Promedio de ingresos")
    avg_expenses: float = Field(..., description="Promedio de gastos")
    avg_balance: float = Field(..., description="Promedio de balance")
    trend_direction: str = Field(..., description="'improving', 'declining', 'stable'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "months": 6,
                "data_points": [
                    {"month": "2024-08", "income": 2500, "expenses": 1800, "balance": 700},
                    {"month": "2024-09", "income": 2300, "expenses": 1900, "balance": 400}
                ],
                "avg_income": 2400.00,
                "avg_expenses": 1850.00,
                "avg_balance": 550.00,
                "trend_direction": "improving"
            }
        }


class UnusualTransaction(BaseModel):
    """Transacción inusual detectada."""
    id: str
    date: str
    description: str
    amount: float
    type: str = Field(..., description="'income' o 'expense'")
    category: str
    z_score: float = Field(..., description="Desviación estándar")
    reason: str = Field(..., description="Explicación de por qué es inusual")


class AnomaliesResponse(BaseModel):
    """Respuesta con anomalías detectadas."""
    threshold: float = Field(..., description="Umbral de z-score usado")
    num_anomalies: int
    anomalies: List[UnusualTransaction]
    
    class Config:
        json_schema_extra = {
            "example": {
                "threshold": 2.0,
                "num_anomalies": 3,
                "anomalies": [
                    {
                        "id": "txn-123",
                        "date": "2025-01-15",
                        "description": "Compra excepcional",
                        "amount": 1200.00,
                        "type": "expense",
                        "category": "Electrónica",
                        "z_score": 3.2,
                        "reason": "Alto respecto a tu gasto promedio de €350.00"
                    }
                ]
            }
        }


class RecurringExpense(BaseModel):
    """Gasto recurrente identificado."""
    description: str
    category: str
    avg_amount: float
    frequency: str = Field(..., description="'mensual', 'quincenal', 'semanal', 'irregular'")
    occurrences: int = Field(..., description="Número de veces detectado")
    last_date: str
    annual_cost: float = Field(..., description="Costo anual estimado")


class RecurringExpensesResponse(BaseModel):
    """Lista de gastos recurrentes."""
    num_recurring: int
    total_annual_cost: float
    recurring_expenses: List[RecurringExpense]
    
    class Config:
        json_schema_extra = {
            "example": {
                "num_recurring": 5,
                "total_annual_cost": 1200.00,
                "recurring_expenses": [
                    {
                        "description": "Spotify Premium",
                        "category": "Entretenimiento",
                        "avg_amount": 9.99,
                        "frequency": "mensual",
                        "occurrences": 6,
                        "last_date": "2025-01-15",
                        "annual_cost": 119.88
                    }
                ]
            }
        }


class SavingOpportunity(BaseModel):
    """Oportunidad de ahorro identificada."""
    category: str
    current_spending: float
    historical_avg: float
    excess_amount: float
    potential_savings_monthly: float
    potential_savings_annual: float
    recommendation: str


class SavingsPotentialResponse(BaseModel):
    """Análisis de potencial de ahorro."""
    num_opportunities: int
    total_potential_monthly: float
    total_potential_annual: float
    opportunities: List[SavingOpportunity]
    
    class Config:
        json_schema_extra = {
            "example": {
                "num_opportunities": 3,
                "total_potential_monthly": 150.00,
                "total_potential_annual": 1800.00,
                "opportunities": [
                    {
                        "category": "Restaurantes",
                        "current_spending": 450.00,
                        "historical_avg": 300.00,
                        "excess_amount": 150.00,
                        "potential_savings_monthly": 150.00,
                        "potential_savings_annual": 1800.00,
                        "recommendation": "Reducir Restaurantes al promedio histórico de €300.00"
                    }
                ]
            }
        }


class CategoryChange(BaseModel):
    """Cambio en una categoría entre períodos."""
    category: str
    period1_amount: float
    period2_amount: float
    difference: float
    percentage_change: float


class PeriodComparisonSummary(BaseModel):
    """Resumen de comparación entre períodos."""
    period1: float
    period2: float
    difference: float
    percentage_change: float


class PeriodComparisonResponse(BaseModel):
    """Comparación completa entre dos períodos."""
    period1: PeriodRange
    period2: PeriodRange
    summary_comparison: Dict[str, PeriodComparisonSummary]
    category_changes: List[CategoryChange]
    insights: List[str] = Field(..., description="Insights textuales generados")
    
    class Config:
        json_schema_extra = {
            "example": {
                "period1": {"start": "2025-01-01", "end": "2025-01-31"},
                "period2": {"start": "2024-12-01", "end": "2024-12-31"},
                "summary_comparison": {
                    "income": {
                        "period1": 2500.00,
                        "period2": 2300.00,
                        "difference": 200.00,
                        "percentage_change": 8.7
                    },
                    "expenses": {
                        "period1": 1800.00,
                        "period2": 1900.00,
                        "difference": -100.00,
                        "percentage_change": -5.3
                    }
                },
                "category_changes": [],
                "insights": ["Tus ingresos aumentaron un 8.7%", "Redujiste tus gastos un 5.3%"]
            }
        }


class ChartDataset(BaseModel):
    """Dataset para Chart.js."""
    label: str
    data: List[float]
    backgroundColor: Optional[List[str]] = None
    borderColor: Optional[str] = None
    fill: Optional[bool] = None


class ChartData(BaseModel):
    """Datos formateados para Chart.js."""
    labels: List[str]
    datasets: List[ChartDataset]


class AnalyticsWithChartsResponse(BaseModel):
    """Respuesta combinada con datos y formato para gráficos."""
    analytics_data: Dict[str, Any] = Field(..., description="Datos analíticos crudos")
    chart_data: ChartData = Field(..., description="Datos formateados para Chart.js")
    chart_type: str = Field(..., description="'pie', 'line', 'bar', etc.")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analytics_data": {"total": 1800, "categories": []},
                "chart_data": {
                    "labels": ["Alimentación", "Transporte", "Ocio"],
                    "datasets": [{
                        "label": "Gastos por Categoría",
                        "data": [450, 300, 250],
                        "backgroundColor": ["#10B981", "#3B82F6", "#F59E0B"]
                    }]
                },
                "chart_type": "pie"
            }
        }


# ===== SCHEMAS DE REQUEST =====

class CustomAnalysisRequest(BaseModel):
    """Request para análisis personalizado."""
    question: str = Field(..., min_length=5, max_length=500, description="Pregunta del usuario")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional opcional")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "¿Por qué gasté más este mes en restaurantes?",
                "context": {"category": "Restaurantes"}
            }
        }
