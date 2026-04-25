"""
Schemas para Mortgage Capacity - Capacidad Hipotecaria
======================================================

Modelos Pydantic para la validación de entrada y respuestas
de los endpoints de capacidad hipotecaria.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


# ===== ENUMS =====

class RiskLevel(str, Enum):
    """Nivel de riesgo financiero."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HealthStatus(str, Enum):
    """Estado de salud financiera."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    NEEDS_IMPROVEMENT = "needs_improvement"
    CRITICAL = "critical"


# ===== SCHEMAS DE ENTRADA =====

class MortgageConfigRequest(BaseModel):
    """Configuración personalizada para el cálculo de hipoteca."""
    interest_rate: float = Field(
        default=0.03,
        ge=0,
        le=0.20,
        description="Tasa de interés anual (ej: 0.03 = 3%)"
    )
    years: int = Field(
        default=30,
        ge=5,
        le=40,
        description="Plazo de la hipoteca en años"
    )
    down_payment_ratio: float = Field(
        default=0.20,
        ge=0,
        le=0.50,
        description="Porcentaje de entrada (ej: 0.20 = 20%)"
    )
    max_debt_ratio: float = Field(
        default=0.35,
        ge=0.20,
        le=0.50,
        description="Ratio máximo de deuda sobre ingresos"
    )
    safety_margin: float = Field(
        default=0.10,
        ge=0,
        le=0.30,
        description="Margen de seguridad adicional"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "interest_rate": 0.03,
                "years": 30,
                "down_payment_ratio": 0.20,
                "max_debt_ratio": 0.35,
                "safety_margin": 0.10
            }
        }


class TargetPriceRequest(BaseModel):
    """Solicitud de análisis para un precio objetivo."""
    target_price: float = Field(
        ...,
        gt=0,
        description="Precio objetivo de la vivienda"
    )
    config: Optional[MortgageConfigRequest] = Field(
        default=None,
        description="Configuración personalizada (opcional)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "target_price": 200000,
                "config": {
                    "interest_rate": 0.035,
                    "years": 25
                }
            }
        }


# ===== SCHEMAS DE RESPUESTA =====

class ScenarioDetail(BaseModel):
    """Detalle de un escenario de hipoteca."""
    monthly_payment: float = Field(..., description="Cuota mensual")
    loan_amount: float = Field(..., description="Monto del préstamo")
    max_price: float = Field(..., description="Precio máximo de vivienda")
    required_down_payment: float = Field(..., description="Entrada requerida")
    debt_to_income_ratio: float = Field(..., description="Ratio deuda/ingresos")


class CalculationDetails(BaseModel):
    """Detalles del cálculo para auditoría."""
    savings_capacity: float
    max_quota_by_savings: float
    max_quota_by_income: float
    final_max_quota: float
    interest_rate: float
    years: int
    down_payment_ratio: float
    income_stability_score: float
    total_debt_ratio: float


class DataSummary(BaseModel):
    """Resumen de datos utilizados."""
    avg_income: float
    total_expenses: float
    savings_rate: float


class MetadataResponse(BaseModel):
    """Metadatos del cálculo."""
    user_id: str
    calculated_at: str
    months_analyzed: int
    data_summary: DataSummary


class MortgageCapacityResponse(BaseModel):
    """Respuesta completa del cálculo de capacidad hipotecaria."""
    max_price: float = Field(..., description="Precio máximo de vivienda recomendado")
    loan_amount: float = Field(..., description="Monto del préstamo recomendado")
    monthly_payment: float = Field(..., description="Cuota mensual estimada")
    required_down_payment: float = Field(..., description="Entrada requerida")
    risk_score: RiskLevel = Field(..., description="Nivel de riesgo")
    scenarios: Dict[str, ScenarioDetail] = Field(
        ...,
        description="Escenarios alternativos (conservative, balanced, aggressive)"
    )
    calculation_details: CalculationDetails = Field(
        ...,
        description="Detalles del cálculo para auditoría"
    )
    currency: str = Field(default="EUR")
    metadata: MetadataResponse

    class Config:
        json_schema_extra = {
            "example": {
                "max_price": 185000.00,
                "loan_amount": 148000.00,
                "monthly_payment": 620.00,
                "required_down_payment": 37000.00,
                "risk_score": "medium",
                "scenarios": {
                    "conservative": {
                        "monthly_payment": 500.00,
                        "loan_amount": 120000.00,
                        "max_price": 150000.00,
                        "required_down_payment": 30000.00,
                        "debt_to_income_ratio": 0.25
                    },
                    "balanced": {
                        "monthly_payment": 620.00,
                        "loan_amount": 148000.00,
                        "max_price": 185000.00,
                        "required_down_payment": 37000.00,
                        "debt_to_income_ratio": 0.30
                    },
                    "aggressive": {
                        "monthly_payment": 750.00,
                        "loan_amount": 180000.00,
                        "max_price": 225000.00,
                        "required_down_payment": 45000.00,
                        "debt_to_income_ratio": 0.35
                    }
                },
                "calculation_details": {
                    "savings_capacity": 800.00,
                    "max_quota_by_savings": 640.00,
                    "max_quota_by_income": 850.00,
                    "final_max_quota": 620.00,
                    "interest_rate": 0.03,
                    "years": 30,
                    "down_payment_ratio": 0.20,
                    "income_stability_score": 0.92,
                    "total_debt_ratio": 0.07
                },
                "currency": "EUR",
                "metadata": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "calculated_at": "2026-04-10T15:30:00",
                    "months_analyzed": 6,
                    "data_summary": {
                        "avg_income": 3000.00,
                        "total_expenses": 2000.00,
                        "savings_rate": 0.33
                    }
                }
            }
        }


class ComparisonDetail(BaseModel):
    """Comparación con capacidad máxima."""
    max_affordable_price: float
    difference_from_max: float
    percentage_of_max: float


class TargetPriceResponse(BaseModel):
    """Respuesta del análisis para un precio objetivo."""
    target_price: float = Field(..., description="Precio objetivo solicitado")
    loan_needed: float = Field(..., description="Préstamo necesario")
    down_payment_needed: float = Field(..., description="Entrada necesaria")
    monthly_payment_needed: float = Field(..., description="Cuota mensual necesaria")
    is_viable: bool = Field(..., description="Si el objetivo es alcanzable")
    gap: float = Field(..., description="Diferencia con cuota máxima permitida")
    resulting_debt_ratio: float = Field(..., description="Ratio deuda/ingresos resultante")
    recommendation: str = Field(..., description="Recomendación personalizada")
    comparison: ComparisonDetail = Field(
        ...,
        description="Comparación con capacidad máxima"
    )
    currency: str = Field(default="EUR")

    class Config:
        json_schema_extra = {
            "example": {
                "target_price": 200000.00,
                "loan_needed": 160000.00,
                "down_payment_needed": 40000.00,
                "monthly_payment_needed": 675.00,
                "is_viable": True,
                "gap": -55.00,
                "resulting_debt_ratio": 0.32,
                "recommendation": "Viable con ratio de deuda moderado...",
                "comparison": {
                    "max_affordable_price": 185000.00,
                    "difference_from_max": 15000.00,
                    "percentage_of_max": 108.11
                },
                "currency": "EUR"
            }
        }


class FinancialProfileSummary(BaseModel):
    """Resumen del perfil financiero para UI."""
    monthly_income: float = Field(..., description="Ingreso mensual promedio")
    income_stability: float = Field(
        ...,
        ge=0,
        le=100,
        description="Estabilidad de ingresos (%)"
    )
    fixed_expenses: float = Field(..., description="Gastos fijos mensuales")
    variable_expenses: float = Field(..., description="Gastos variables mensuales")
    debt_payments: float = Field(..., description="Pagos de deuda actuales")
    disposable_income: float = Field(..., description="Ingreso disponible")
    savings_rate_percentage: float = Field(..., description="Tasa de ahorro (%)")
    health_status: HealthStatus = Field(..., description="Estado de salud financiera")
    currency: str = Field(default="EUR")
    analysis_period_months: int = Field(..., description="Meses analizados")

    class Config:
        json_schema_extra = {
            "example": {
                "monthly_income": 3000.00,
                "income_stability": 92.5,
                "fixed_expenses": 800.00,
                "variable_expenses": 600.00,
                "debt_payments": 200.00,
                "disposable_income": 1400.00,
                "savings_rate_percentage": 33.3,
                "health_status": "good",
                "currency": "EUR",
                "analysis_period_months": 6
            }
        }
