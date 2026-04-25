"""
Mortgage Capacity Calculator
============================

Motor de cálculo para determinar la capacidad hipotecaria del usuario.
Implementa cálculos financieros deterministas y auditables.
"""

import math
from typing import Dict, Any

from .models import FinancialProfile, CalculationConfig, MortgageCapacityResult


class MortgageCapacityCalculator:
    """
    Calculadora de capacidad hipotecaria.

    Determina el precio máximo de vivienda que un usuario puede permitirse
    basándose en su perfil financiero y la configuración de la hipoteca.

    Ejemplo de uso:
        profile = FinancialProfile(
            avg_income=3000,
            income_std=200,
            fixed_expenses=800,
            variable_expenses=600,
            debt_payments=200,
            savings_rate=0.15
        )
        config = CalculationConfig()
        calculator = MortgageCapacityCalculator(profile, config)
        result = calculator.calculate()
    """

    # Factores de riesgo para escenarios
    SCENARIO_FACTORS = {
        "conservative": 0.25,
        "balanced": 0.30,
        "aggressive": 0.35
    }

    def __init__(self, profile: FinancialProfile, config: CalculationConfig):
        """
        Inicializa el calculador.

        Args:
            profile: Perfil financiero del usuario
            config: Configuración de la hipoteca
        """
        self.profile = profile
        self.config = config

    def calculate(self) -> Dict[str, Any]:
        """
        Ejecuta el cálculo completo de capacidad hipotecaria.

        Returns:
            Diccionario con:
            - max_price: Precio máximo de vivienda
            - loan_amount: Monto del préstamo
            - monthly_payment: Cuota mensual
            - required_down_payment: Entrada requerida
            - risk_score: Nivel de riesgo
            - scenarios: Escenarios alternativos
            - calculation_details: Detalles del cálculo
        """
        # 1. Calcular capacidad de ahorro ajustada
        savings_capacity = self._calculate_savings_capacity()

        # 2. Calcular cuota máxima permitida
        max_quota = self._calculate_max_quota(savings_capacity)

        # 3. Calcular capacidad de préstamo
        loan_amount = self._calculate_loan_capacity(max_quota)

        # 4. Calcular precio máximo de vivienda
        max_price = self._calculate_property_price(loan_amount)

        # 5. Calcular entrada requerida
        required_down_payment = max_price * self.config.down_payment_ratio

        # 6. Evaluar riesgo
        risk_score = self._calculate_risk()

        # 7. Calcular escenarios alternativos
        scenarios = self._calculate_scenarios()

        # 8. Construir detalles de cálculo para auditoría
        calculation_details = {
            "savings_capacity": round(savings_capacity, 2),
            "max_quota_by_savings": round(savings_capacity * 0.8, 2),
            "max_quota_by_income": round(
                (self.profile.avg_income * self.config.max_debt_ratio)
                - self.profile.debt_payments, 2
            ),
            "final_max_quota": round(max_quota, 2),
            "interest_rate": self.config.interest_rate,
            "years": self.config.years,
            "down_payment_ratio": self.config.down_payment_ratio,
            "income_stability_score": round(self.profile.income_stability_score, 2),
            "total_debt_ratio": round(self.profile.total_debt_ratio, 2)
        }

        return {
            "max_price": round(max_price, 2),
            "loan_amount": round(loan_amount, 2),
            "monthly_payment": round(max_quota, 2),
            "required_down_payment": round(required_down_payment, 2),
            "risk_score": risk_score,
            "scenarios": scenarios,
            "calculation_details": calculation_details,
            "currency": self.profile.currency
        }

    def _calculate_savings_capacity(self) -> float:
        """
        Calcula la capacidad de ahorro ajustada por estabilidad de ingresos.

        La capacidad de ahorro base es el ingreso menos los gastos.
        Se aplica una penalización basada en la variabilidad de ingresos
        para ser más conservadores con ingresos inestables.

        Returns:
            Capacidad de ahorro ajustada (mensual)
        """
        total_expenses = self.profile.fixed_expenses + self.profile.variable_expenses
        base = self.profile.avg_income - total_expenses

        # Penalización por inestabilidad de ingresos
        # Mayor desviación estándar = menor capacidad ajustada
        stability_penalty = self.profile.income_std * 0.5

        return max(base - stability_penalty, 0)

    def _calculate_max_quota(self, savings_capacity: float) -> float:
        """
        Calcula la cuota máxima de hipoteca permitida.

        Se utiliza el mínimo entre:
        1. 80% de la capacidad de ahorro (para mantener margen)
        2. 35% del ingreso menos deudas existentes (ratio estándar bancario)

        Args:
            savings_capacity: Capacidad de ahorro ajustada

        Returns:
            Cuota máxima mensual
        """
        # Método 1: Basado en capacidad de ahorro
        quota_by_savings = savings_capacity * 0.8

        # Método 2: Basado en ratio de ingresos (estándar bancario)
        quota_by_income = (
            (self.profile.avg_income * self.config.max_debt_ratio)
            - self.profile.debt_payments
        )

        # Usar el menor de los dos (más conservador)
        max_quota = max(min(quota_by_savings, quota_by_income), 0)

        # Aplicar margen de seguridad si está configurado
        if self.config.safety_margin > 0:
            max_quota = max_quota * (1 - self.config.safety_margin)

        return max_quota

    def _calculate_loan_capacity(self, monthly_payment: float) -> float:
        """
        Calcula el monto máximo del préstamo hipotecario.

        Usa la fórmula de valor presente de una anualidad:
        PV = PMT × [(1 - (1 + r)^-n) / r]

        Args:
            monthly_payment: Cuota mensual máxima

        Returns:
            Monto máximo del préstamo
        """
        r = self.config.monthly_rate
        n = self.config.total_payments

        # Caso especial: tasa de interés cero
        if r == 0:
            return monthly_payment * n

        # Fórmula de valor presente de anualidad
        numerator = monthly_payment * (math.pow(1 + r, n) - 1)
        denominator = r * math.pow(1 + r, n)

        if denominator == 0:
            return 0

        return numerator / denominator

    def _calculate_property_price(self, loan_amount: float) -> float:
        """
        Calcula el precio máximo de vivienda.

        El precio de vivienda = préstamo / (1 - porcentaje de entrada)

        Args:
            loan_amount: Monto del préstamo

        Returns:
            Precio máximo de vivienda
        """
        if self.config.down_payment_ratio >= 1:
            return 0

        return loan_amount / (1 - self.config.down_payment_ratio)

    def _calculate_risk(self) -> str:
        """
        Evalúa el nivel de riesgo del perfil financiero.

        Factores considerados:
        - Tasa de ahorro
        - Estabilidad de ingresos
        - Ratio de deuda actual

        Returns:
            Nivel de riesgo: "low", "medium", "high"
        """
        risk_points = 0

        # Evaluar tasa de ahorro
        if self.profile.savings_rate < 0.10:
            risk_points += 2
        elif self.profile.savings_rate < 0.20:
            risk_points += 1

        # Evaluar estabilidad de ingresos
        if self.profile.income_stability_score < 0.7:
            risk_points += 2
        elif self.profile.income_stability_score < 0.85:
            risk_points += 1

        # Evaluar ratio de deuda actual
        if self.profile.total_debt_ratio > 0.25:
            risk_points += 2
        elif self.profile.total_debt_ratio > 0.15:
            risk_points += 1

        # Evaluar si hay margen para imprevistos
        if self.profile.disposable_income < self.profile.avg_income * 0.10:
            risk_points += 1

        # Clasificar riesgo
        if risk_points >= 4:
            return "high"
        elif risk_points >= 2:
            return "medium"
        return "low"

    def _calculate_scenarios(self) -> Dict[str, Dict[str, float]]:
        """
        Genera escenarios alternativos de hipoteca.

        Escenarios:
        - conservative (25% del ingreso): Máxima seguridad financiera
        - balanced (30% del ingreso): Equilibrio razonable
        - aggressive (35% del ingreso): Mayor riesgo, mayor vivienda

        Returns:
            Diccionario con escenarios calculados
        """
        scenarios = {}

        for label, factor in self.SCENARIO_FACTORS.items():
            # Calcular cuota para este escenario
            quota = (self.profile.avg_income * factor) - self.profile.debt_payments
            quota = max(quota, 0)

            # Calcular préstamo y precio
            loan = self._calculate_loan_capacity(quota)
            price = self._calculate_property_price(loan)
            down_payment = price * self.config.down_payment_ratio

            # Calcular ratio deuda/ingreso resultante
            total_debt_payment = self.profile.debt_payments + quota
            debt_to_income = total_debt_payment / self.profile.avg_income if self.profile.avg_income > 0 else 0

            scenarios[label] = {
                "monthly_payment": round(quota, 2),
                "loan_amount": round(loan, 2),
                "max_price": round(price, 2),
                "required_down_payment": round(down_payment, 2),
                "debt_to_income_ratio": round(debt_to_income, 4)
            }

        return scenarios

    def calculate_with_custom_price(self, target_price: float) -> Dict[str, Any]:
        """
        Calcula las condiciones necesarias para un precio objetivo.

        Útil para responder "¿Qué necesito para comprar una casa de X euros?"

        Args:
            target_price: Precio objetivo de la vivienda

        Returns:
            Condiciones necesarias y viabilidad
        """
        loan_needed = target_price * (1 - self.config.down_payment_ratio)
        down_payment_needed = target_price * self.config.down_payment_ratio

        # Calcular cuota necesaria
        r = self.config.monthly_rate
        n = self.config.total_payments

        if r == 0:
            monthly_payment_needed = loan_needed / n
        else:
            monthly_payment_needed = (
                loan_needed * r * math.pow(1 + r, n)
            ) / (math.pow(1 + r, n) - 1)

        # Evaluar viabilidad
        max_affordable = self._calculate_max_quota(self._calculate_savings_capacity())
        is_viable = monthly_payment_needed <= max_affordable

        # Calcular déficit o excedente
        gap = max_affordable - monthly_payment_needed

        # Calcular ratio de deuda resultante
        total_debt = self.profile.debt_payments + monthly_payment_needed
        resulting_debt_ratio = total_debt / self.profile.avg_income if self.profile.avg_income > 0 else 0

        return {
            "target_price": round(target_price, 2),
            "loan_needed": round(loan_needed, 2),
            "down_payment_needed": round(down_payment_needed, 2),
            "monthly_payment_needed": round(monthly_payment_needed, 2),
            "is_viable": is_viable,
            "gap": round(gap, 2),
            "resulting_debt_ratio": round(resulting_debt_ratio, 4),
            "recommendation": self._get_recommendation(is_viable, gap, resulting_debt_ratio),
            "currency": self.profile.currency
        }

    def _get_recommendation(
        self,
        is_viable: bool,
        gap: float,
        debt_ratio: float
    ) -> str:
        """
        Genera una recomendación basada en la viabilidad.

        Args:
            is_viable: Si el objetivo es alcanzable
            gap: Diferencia entre cuota máxima y necesaria
            debt_ratio: Ratio de deuda resultante

        Returns:
            Recomendación textual
        """
        if not is_viable:
            deficit_monthly = abs(gap)
            return (
                f"Objetivo no viable actualmente. Déficit mensual: "
                f"{round(deficit_monthly, 2)} {self.profile.currency}. "
                f"Considera aumentar ingresos, reducir gastos, o buscar "
                f"una vivienda más económica."
            )

        if debt_ratio > 0.40:
            return (
                "Viable pero con alto ratio de deuda. Recomendamos "
                "considerar un objetivo más conservador para mayor "
                "seguridad financiera."
            )

        if debt_ratio > 0.30:
            return (
                "Viable con ratio de deuda moderado. Considera mantener "
                "un fondo de emergencia adicional antes de proceder."
            )

        return (
            "Objetivo viable con buen margen de seguridad. "
            "Tu perfil financiero es adecuado para esta compra."
        )
