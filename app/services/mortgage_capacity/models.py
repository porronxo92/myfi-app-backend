"""
Mortgage Capacity Models
========================

Modelos de datos para el cálculo de capacidad hipotecaria.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FinancialProfile:
    """
    Representa el estado financiero agregado del usuario.

    Todos los valores son mensuales y están en la moneda local del usuario.

    Attributes:
        avg_income: Ingreso medio mensual (promedio de los últimos 6-12 meses)
        income_std: Desviación estándar de ingresos (mide estabilidad)
        fixed_expenses: Gastos fijos mensuales (alquiler, servicios, etc.)
        variable_expenses: Gastos variables mensuales (alimentación, ocio, etc.)
        debt_payments: Cuotas de deuda actuales (préstamos, créditos)
        savings_rate: Ratio de ahorro (0-1), calculado como ahorro/ingresos
        currency: Moneda de los valores
    """
    avg_income: float
    income_std: float
    fixed_expenses: float
    variable_expenses: float
    debt_payments: float
    savings_rate: float
    currency: str = "EUR"

    def __post_init__(self):
        """Validaciones básicas al crear el perfil."""
        if self.avg_income < 0:
            raise ValueError("avg_income no puede ser negativo")
        if self.income_std < 0:
            raise ValueError("income_std no puede ser negativo")
        if self.fixed_expenses < 0:
            raise ValueError("fixed_expenses no puede ser negativo")
        if self.variable_expenses < 0:
            raise ValueError("variable_expenses no puede ser negativo")
        if self.debt_payments < 0:
            raise ValueError("debt_payments no puede ser negativo")
        if not 0 <= self.savings_rate <= 1:
            # Normalizar si viene como porcentaje
            if 0 < self.savings_rate <= 100:
                self.savings_rate = self.savings_rate / 100
            elif self.savings_rate < 0:
                self.savings_rate = 0
            elif self.savings_rate > 100:
                self.savings_rate = 1

    @property
    def total_expenses(self) -> float:
        """Total de gastos mensuales."""
        return self.fixed_expenses + self.variable_expenses

    @property
    def total_debt_ratio(self) -> float:
        """Ratio de deuda sobre ingresos."""
        if self.avg_income == 0:
            return 0
        return self.debt_payments / self.avg_income

    @property
    def disposable_income(self) -> float:
        """Ingreso disponible después de gastos y deudas."""
        return max(self.avg_income - self.total_expenses - self.debt_payments, 0)

    @property
    def income_stability_score(self) -> float:
        """
        Score de estabilidad de ingresos (0-1).
        1 = muy estable, 0 = muy variable.
        """
        if self.avg_income == 0:
            return 0
        coefficient_variation = self.income_std / self.avg_income
        # Invertir: menor variación = mayor estabilidad
        return max(1 - coefficient_variation, 0)


@dataclass
class CalculationConfig:
    """
    Configuración para el cálculo de capacidad hipotecaria.

    Attributes:
        interest_rate: Tasa de interés anual (ej: 0.03 = 3%)
        years: Plazo de la hipoteca en años
        down_payment_ratio: Porcentaje de entrada (ej: 0.20 = 20%)
        max_debt_ratio: Ratio máximo de deuda sobre ingresos permitido
        safety_margin: Margen de seguridad para cálculos (0-1)
    """
    interest_rate: float = 0.03
    years: int = 30
    down_payment_ratio: float = 0.20
    max_debt_ratio: float = 0.35
    safety_margin: float = 0.1

    def __post_init__(self):
        """Validaciones de configuración."""
        if not 0 <= self.interest_rate <= 0.20:
            raise ValueError("interest_rate debe estar entre 0% y 20%")
        if not 5 <= self.years <= 40:
            raise ValueError("years debe estar entre 5 y 40")
        if not 0 <= self.down_payment_ratio <= 0.50:
            raise ValueError("down_payment_ratio debe estar entre 0% y 50%")
        if not 0.20 <= self.max_debt_ratio <= 0.50:
            raise ValueError("max_debt_ratio debe estar entre 20% y 50%")
        if not 0 <= self.safety_margin <= 0.30:
            raise ValueError("safety_margin debe estar entre 0% y 30%")

    @property
    def monthly_rate(self) -> float:
        """Tasa de interés mensual."""
        return self.interest_rate / 12

    @property
    def total_payments(self) -> int:
        """Número total de pagos (meses)."""
        return self.years * 12


@dataclass
class MortgageScenario:
    """
    Representa un escenario de hipoteca calculado.

    Attributes:
        name: Nombre del escenario (conservative, balanced, aggressive)
        monthly_payment: Cuota mensual de la hipoteca
        loan_amount: Monto del préstamo hipotecario
        max_price: Precio máximo de vivienda
        debt_to_income_ratio: Ratio deuda/ingresos para este escenario
    """
    name: str
    monthly_payment: float
    loan_amount: float
    max_price: float
    debt_to_income_ratio: float


@dataclass
class MortgageCapacityResult:
    """
    Resultado completo del cálculo de capacidad hipotecaria.

    Attributes:
        max_price: Precio máximo de vivienda recomendado
        loan_amount: Monto del préstamo recomendado
        monthly_payment: Cuota mensual recomendada
        required_down_payment: Entrada requerida
        risk_score: Score de riesgo (low, medium, high)
        scenarios: Diccionario de escenarios calculados
        calculation_details: Detalles del cálculo para auditoría
        currency: Moneda de los valores
    """
    max_price: float
    loan_amount: float
    monthly_payment: float
    required_down_payment: float
    risk_score: str
    scenarios: dict
    calculation_details: dict
    currency: str = "EUR"
