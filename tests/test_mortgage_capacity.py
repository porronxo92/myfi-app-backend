"""
Tests para el módulo de Capacidad Hipotecaria
=============================================

Tests unitarios para verificar la lógica de cálculo.
"""

import pytest
from app.services.mortgage_capacity import (
    FinancialProfile,
    CalculationConfig,
    MortgageCapacityCalculator
)


class TestFinancialProfile:
    """Tests para el modelo FinancialProfile."""

    def test_create_valid_profile(self):
        """Test: Crear un perfil financiero válido."""
        profile = FinancialProfile(
            avg_income=3000,
            income_std=200,
            fixed_expenses=800,
            variable_expenses=600,
            debt_payments=200,
            savings_rate=0.15
        )
        assert profile.avg_income == 3000
        assert profile.savings_rate == 0.15

    def test_total_expenses(self):
        """Test: Cálculo de gastos totales."""
        profile = FinancialProfile(
            avg_income=3000,
            income_std=200,
            fixed_expenses=800,
            variable_expenses=600,
            debt_payments=200,
            savings_rate=0.15
        )
        assert profile.total_expenses == 1400

    def test_disposable_income(self):
        """Test: Cálculo de ingreso disponible."""
        profile = FinancialProfile(
            avg_income=3000,
            income_std=200,
            fixed_expenses=800,
            variable_expenses=600,
            debt_payments=200,
            savings_rate=0.15
        )
        # 3000 - 1400 - 200 = 1400
        assert profile.disposable_income == 1400

    def test_negative_values_raise_error(self):
        """Test: Valores negativos lanzan error."""
        with pytest.raises(ValueError):
            FinancialProfile(
                avg_income=-1000,
                income_std=200,
                fixed_expenses=800,
                variable_expenses=600,
                debt_payments=200,
                savings_rate=0.15
            )

    def test_savings_rate_normalization(self):
        """Test: Normalización de tasa de ahorro como porcentaje."""
        profile = FinancialProfile(
            avg_income=3000,
            income_std=200,
            fixed_expenses=800,
            variable_expenses=600,
            debt_payments=200,
            savings_rate=15  # Como porcentaje
        )
        assert profile.savings_rate == 0.15


class TestCalculationConfig:
    """Tests para el modelo CalculationConfig."""

    def test_default_config(self):
        """Test: Configuración por defecto."""
        config = CalculationConfig()
        assert config.interest_rate == 0.03
        assert config.years == 30
        assert config.down_payment_ratio == 0.20

    def test_monthly_rate(self):
        """Test: Cálculo de tasa mensual."""
        config = CalculationConfig(interest_rate=0.03)
        assert config.monthly_rate == 0.03 / 12

    def test_total_payments(self):
        """Test: Cálculo de pagos totales."""
        config = CalculationConfig(years=30)
        assert config.total_payments == 360

    def test_invalid_interest_rate(self):
        """Test: Tasa de interés inválida lanza error."""
        with pytest.raises(ValueError):
            CalculationConfig(interest_rate=0.50)  # 50% es demasiado

    def test_invalid_years(self):
        """Test: Plazo inválido lanza error."""
        with pytest.raises(ValueError):
            CalculationConfig(years=50)  # Máximo 40


class TestMortgageCapacityCalculator:
    """Tests para el calculador de capacidad hipotecaria."""

    @pytest.fixture
    def standard_profile(self):
        """Perfil estándar para tests."""
        return FinancialProfile(
            avg_income=3000,
            income_std=200,
            fixed_expenses=800,
            variable_expenses=600,
            debt_payments=200,
            savings_rate=0.15
        )

    @pytest.fixture
    def standard_config(self):
        """Configuración estándar para tests."""
        return CalculationConfig()

    def test_calculate_returns_dict(self, standard_profile, standard_config):
        """Test: El cálculo retorna un diccionario."""
        calculator = MortgageCapacityCalculator(standard_profile, standard_config)
        result = calculator.calculate()

        assert isinstance(result, dict)
        assert "max_price" in result
        assert "loan_amount" in result
        assert "monthly_payment" in result
        assert "risk_score" in result
        assert "scenarios" in result

    def test_calculate_positive_values(self, standard_profile, standard_config):
        """Test: Los valores calculados son positivos."""
        calculator = MortgageCapacityCalculator(standard_profile, standard_config)
        result = calculator.calculate()

        assert result["max_price"] >= 0
        assert result["loan_amount"] >= 0
        assert result["monthly_payment"] >= 0

    def test_loan_less_than_price(self, standard_profile, standard_config):
        """Test: El préstamo es menor que el precio (hay entrada)."""
        calculator = MortgageCapacityCalculator(standard_profile, standard_config)
        result = calculator.calculate()

        assert result["loan_amount"] < result["max_price"]

    def test_scenarios_calculated(self, standard_profile, standard_config):
        """Test: Se calculan los tres escenarios."""
        calculator = MortgageCapacityCalculator(standard_profile, standard_config)
        result = calculator.calculate()

        assert "conservative" in result["scenarios"]
        assert "balanced" in result["scenarios"]
        assert "aggressive" in result["scenarios"]

    def test_scenarios_ordering(self, standard_profile, standard_config):
        """Test: Los escenarios están ordenados por precio."""
        calculator = MortgageCapacityCalculator(standard_profile, standard_config)
        result = calculator.calculate()

        conservative = result["scenarios"]["conservative"]["max_price"]
        balanced = result["scenarios"]["balanced"]["max_price"]
        aggressive = result["scenarios"]["aggressive"]["max_price"]

        assert conservative <= balanced <= aggressive

    def test_risk_score_values(self, standard_profile, standard_config):
        """Test: El score de riesgo es válido."""
        calculator = MortgageCapacityCalculator(standard_profile, standard_config)
        result = calculator.calculate()

        assert result["risk_score"] in ["low", "medium", "high"]

    def test_high_savings_low_risk(self):
        """Test: Alta tasa de ahorro = bajo riesgo."""
        profile = FinancialProfile(
            avg_income=5000,
            income_std=100,
            fixed_expenses=800,
            variable_expenses=600,
            debt_payments=0,
            savings_rate=0.40
        )
        config = CalculationConfig()
        calculator = MortgageCapacityCalculator(profile, config)
        result = calculator.calculate()

        assert result["risk_score"] == "low"

    def test_low_savings_high_risk(self):
        """Test: Baja tasa de ahorro = alto riesgo."""
        profile = FinancialProfile(
            avg_income=2000,
            income_std=500,
            fixed_expenses=1000,
            variable_expenses=700,
            debt_payments=200,
            savings_rate=0.05
        )
        config = CalculationConfig()
        calculator = MortgageCapacityCalculator(profile, config)
        result = calculator.calculate()

        assert result["risk_score"] in ["medium", "high"]

    def test_custom_price_viable(self, standard_profile, standard_config):
        """Test: Análisis de precio objetivo viable."""
        calculator = MortgageCapacityCalculator(standard_profile, standard_config)
        full_result = calculator.calculate()

        # Usar un precio menor al máximo
        target_price = full_result["max_price"] * 0.8
        result = calculator.calculate_with_custom_price(target_price)

        assert result["is_viable"] == True
        assert result["gap"] >= 0

    def test_custom_price_not_viable(self, standard_profile, standard_config):
        """Test: Análisis de precio objetivo no viable."""
        calculator = MortgageCapacityCalculator(standard_profile, standard_config)
        full_result = calculator.calculate()

        # Usar un precio mucho mayor al máximo
        target_price = full_result["max_price"] * 1.5
        result = calculator.calculate_with_custom_price(target_price)

        assert result["is_viable"] == False
        assert result["gap"] < 0

    def test_zero_interest_rate(self, standard_profile):
        """Test: Tasa de interés cero funciona."""
        config = CalculationConfig(interest_rate=0)
        calculator = MortgageCapacityCalculator(standard_profile, config)
        result = calculator.calculate()

        assert result["max_price"] > 0
        assert result["loan_amount"] > 0

    def test_calculation_details_present(self, standard_profile, standard_config):
        """Test: Los detalles de cálculo están presentes."""
        calculator = MortgageCapacityCalculator(standard_profile, standard_config)
        result = calculator.calculate()

        details = result["calculation_details"]
        assert "savings_capacity" in details
        assert "max_quota_by_savings" in details
        assert "max_quota_by_income" in details
        assert "income_stability_score" in details


class TestEdgeCases:
    """Tests para casos extremos."""

    def test_zero_income(self):
        """Test: Ingreso cero retorna valores cero."""
        profile = FinancialProfile(
            avg_income=0,
            income_std=0,
            fixed_expenses=0,
            variable_expenses=0,
            debt_payments=0,
            savings_rate=0
        )
        config = CalculationConfig()
        calculator = MortgageCapacityCalculator(profile, config)
        result = calculator.calculate()

        assert result["max_price"] == 0
        assert result["loan_amount"] == 0
        assert result["monthly_payment"] == 0

    def test_high_expenses_no_capacity(self):
        """Test: Gastos altos = sin capacidad."""
        profile = FinancialProfile(
            avg_income=2000,
            income_std=100,
            fixed_expenses=1500,
            variable_expenses=500,
            debt_payments=0,
            savings_rate=0
        )
        config = CalculationConfig()
        calculator = MortgageCapacityCalculator(profile, config)
        result = calculator.calculate()

        # Sin capacidad de ahorro, el precio máximo debería ser 0 o muy bajo
        assert result["max_price"] <= 0 or result["monthly_payment"] <= 0

    def test_different_down_payment_ratios(self):
        """Test: Diferentes porcentajes de entrada."""
        profile = FinancialProfile(
            avg_income=3000,
            income_std=200,
            fixed_expenses=800,
            variable_expenses=600,
            debt_payments=200,
            savings_rate=0.15
        )

        # Con 10% de entrada vs 30%
        config_10 = CalculationConfig(down_payment_ratio=0.10)
        config_30 = CalculationConfig(down_payment_ratio=0.30)

        calc_10 = MortgageCapacityCalculator(profile, config_10)
        calc_30 = MortgageCapacityCalculator(profile, config_30)

        result_10 = calc_10.calculate()
        result_30 = calc_30.calculate()

        # Con más entrada, se puede acceder a mayor precio
        assert result_30["max_price"] > result_10["max_price"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
