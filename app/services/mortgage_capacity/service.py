"""
Mortgage Capacity Service
=========================

Servicio de orquestación para el cálculo de capacidad hipotecaria.
Obtiene datos del usuario desde la base de datos y ejecuta los cálculos.
"""

from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import statistics

from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.services.mcp.financial_context import MCPFinancialContext

from .models import FinancialProfile, CalculationConfig
from .calculator import MortgageCapacityCalculator


class MortgageCapacityService:
    """
    Servicio de capacidad hipotecaria.

    Coordina la obtención de datos financieros del usuario y la ejecución
    de los cálculos de capacidad hipotecaria.

    Ejemplo de uso:
        service = MortgageCapacityService(db)
        result = await service.calculate_mortgage_capacity(user_id)
    """

    # Categorías que típicamente representan gastos fijos
    FIXED_EXPENSE_CATEGORIES = [
        "alquiler", "hipoteca", "luz", "electricidad", "agua", "gas",
        "internet", "teléfono", "seguros", "seguro", "gimnasio",
        "suscripciones", "netflix", "spotify", "comunidad",
        "impuestos", "préstamo", "prestamo", "crédito", "credito"
    ]

    # Categorías que típicamente representan pagos de deuda
    DEBT_CATEGORIES = [
        "préstamo", "prestamo", "crédito", "credito", "deuda",
        "financiación", "financiacion", "cuota", "hipoteca"
    ]

    def __init__(self, db: Session):
        """
        Inicializa el servicio.

        Args:
            db: Sesión de base de datos SQLAlchemy
        """
        self.db = db
        self.mcp = MCPFinancialContext(db)

    async def calculate_mortgage_capacity(
        self,
        user_id: UUID,
        config: Optional[CalculationConfig] = None,
        months_to_analyze: int = 6
    ) -> Dict[str, Any]:
        """
        Calcula la capacidad hipotecaria del usuario.

        Args:
            user_id: ID del usuario
            config: Configuración de cálculo (opcional)
            months_to_analyze: Meses de histórico a analizar

        Returns:
            Resultado completo del cálculo de capacidad hipotecaria
        """
        # 1. Obtener datos financieros agregados
        financial_data = await self._get_financial_data(user_id, months_to_analyze)

        # 2. Construir perfil financiero
        profile = FinancialProfile(
            avg_income=financial_data["avg_income"],
            income_std=financial_data["income_std"],
            fixed_expenses=financial_data["fixed_expenses"],
            variable_expenses=financial_data["variable_expenses"],
            debt_payments=financial_data["debt_payments"],
            savings_rate=financial_data["savings_rate"],
            currency=financial_data.get("currency", "EUR")
        )

        # 3. Usar configuración por defecto si no se proporciona
        if config is None:
            config = CalculationConfig()

        # 4. Ejecutar cálculo
        calculator = MortgageCapacityCalculator(profile, config)
        result = calculator.calculate()

        # 5. Añadir metadatos
        result["metadata"] = {
            "user_id": str(user_id),
            "calculated_at": datetime.now().isoformat(),
            "months_analyzed": months_to_analyze,
            "data_summary": {
                "avg_income": financial_data["avg_income"],
                "total_expenses": financial_data["fixed_expenses"] + financial_data["variable_expenses"],
                "savings_rate": financial_data["savings_rate"]
            }
        }

        return result

    async def calculate_for_target_price(
        self,
        user_id: UUID,
        target_price: float,
        config: Optional[CalculationConfig] = None,
        months_to_analyze: int = 6
    ) -> Dict[str, Any]:
        """
        Calcula las condiciones necesarias para un precio objetivo.

        Args:
            user_id: ID del usuario
            target_price: Precio objetivo de la vivienda
            config: Configuración de cálculo (opcional)
            months_to_analyze: Meses de histórico a analizar

        Returns:
            Análisis de viabilidad para el precio objetivo
        """
        # 1. Obtener datos financieros
        financial_data = await self._get_financial_data(user_id, months_to_analyze)

        # 2. Construir perfil
        profile = FinancialProfile(
            avg_income=financial_data["avg_income"],
            income_std=financial_data["income_std"],
            fixed_expenses=financial_data["fixed_expenses"],
            variable_expenses=financial_data["variable_expenses"],
            debt_payments=financial_data["debt_payments"],
            savings_rate=financial_data["savings_rate"],
            currency=financial_data.get("currency", "EUR")
        )

        # 3. Configuración
        if config is None:
            config = CalculationConfig()

        # 4. Calcular para precio objetivo
        calculator = MortgageCapacityCalculator(profile, config)
        result = calculator.calculate_with_custom_price(target_price)

        # 5. Añadir comparación con capacidad máxima
        full_calculation = calculator.calculate()
        result["comparison"] = {
            "max_affordable_price": full_calculation["max_price"],
            "difference_from_max": round(target_price - full_calculation["max_price"], 2),
            "percentage_of_max": round(
                (target_price / full_calculation["max_price"] * 100)
                if full_calculation["max_price"] > 0 else 0, 2
            )
        }

        return result

    async def _get_financial_data(
        self,
        user_id: UUID,
        months: int = 6
    ) -> Dict[str, Any]:
        """
        Obtiene los datos financieros agregados del usuario.

        Args:
            user_id: ID del usuario
            months: Número de meses a analizar

        Returns:
            Diccionario con datos financieros agregados
        """
        # Obtener cuentas del usuario
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()

        if not accounts:
            return self._empty_financial_data()

        account_ids = [acc.id for acc in accounts]
        currency = accounts[0].currency if accounts else "EUR"

        # Calcular rango de fechas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months)

        # Obtener transacciones del período
        transactions = self.db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date.date()
        ).all()

        if not transactions:
            return self._empty_financial_data(currency)

        # Agrupar transacciones por mes
        monthly_data = self._group_by_month(transactions)

        # Calcular métricas de ingresos
        monthly_incomes = [data["income"] for data in monthly_data.values()]
        avg_income = statistics.mean(monthly_incomes) if monthly_incomes else 0
        income_std = statistics.stdev(monthly_incomes) if len(monthly_incomes) > 1 else 0

        # Clasificar gastos
        fixed_expenses, variable_expenses, debt_payments = self._classify_expenses(
            transactions, len(monthly_data)
        )

        # Calcular tasa de ahorro
        total_income = sum(monthly_incomes)
        total_expenses = sum(data["expenses"] for data in monthly_data.values())
        savings_rate = (
            (total_income - total_expenses) / total_income
            if total_income > 0 else 0
        )
        savings_rate = max(min(savings_rate, 1), 0)  # Limitar entre 0 y 1

        return {
            "avg_income": round(avg_income, 2),
            "income_std": round(income_std, 2),
            "fixed_expenses": round(fixed_expenses, 2),
            "variable_expenses": round(variable_expenses, 2),
            "debt_payments": round(debt_payments, 2),
            "savings_rate": round(savings_rate, 4),
            "currency": currency,
            "months_with_data": len(monthly_data)
        }

    def _group_by_month(
        self,
        transactions: list
    ) -> Dict[str, Dict[str, float]]:
        """
        Agrupa transacciones por mes.

        Args:
            transactions: Lista de transacciones

        Returns:
            Diccionario con datos mensuales
        """
        monthly_data = {}

        for t in transactions:
            if t.date:
                month_key = t.date.strftime("%Y-%m")
                if month_key not in monthly_data:
                    monthly_data[month_key] = {"income": 0.0, "expenses": 0.0}

                amount = float(t.amount) if t.amount else 0.0

                if t.type == "income":
                    monthly_data[month_key]["income"] += amount
                elif t.type == "expense":
                    monthly_data[month_key]["expenses"] += abs(amount)

        return monthly_data

    def _classify_expenses(
        self,
        transactions: list,
        num_months: int
    ) -> tuple:
        """
        Clasifica gastos en fijos, variables y deudas.

        Args:
            transactions: Lista de transacciones
            num_months: Número de meses analizados

        Returns:
            Tupla (fixed_expenses, variable_expenses, debt_payments) promedios mensuales
        """
        fixed_total = 0.0
        variable_total = 0.0
        debt_total = 0.0

        for t in transactions:
            if t.type != "expense":
                continue

            amount = abs(float(t.amount)) if t.amount else 0.0
            category_name = (
                t.category.name.lower() if t.category and t.category.name
                else ""
            )
            description = (t.description or "").lower()

            # Clasificar por categoría o descripción
            is_debt = any(
                keyword in category_name or keyword in description
                for keyword in self.DEBT_CATEGORIES
            )
            is_fixed = any(
                keyword in category_name or keyword in description
                for keyword in self.FIXED_EXPENSE_CATEGORIES
            )

            if is_debt:
                debt_total += amount
            elif is_fixed:
                fixed_total += amount
            else:
                variable_total += amount

        # Calcular promedios mensuales
        if num_months > 0:
            fixed_avg = fixed_total / num_months
            variable_avg = variable_total / num_months
            debt_avg = debt_total / num_months
        else:
            fixed_avg = variable_avg = debt_avg = 0

        return fixed_avg, variable_avg, debt_avg

    def _empty_financial_data(self, currency: str = "EUR") -> Dict[str, Any]:
        """
        Retorna estructura de datos vacía.

        Args:
            currency: Moneda por defecto

        Returns:
            Diccionario con valores en cero
        """
        return {
            "avg_income": 0.0,
            "income_std": 0.0,
            "fixed_expenses": 0.0,
            "variable_expenses": 0.0,
            "debt_payments": 0.0,
            "savings_rate": 0.0,
            "currency": currency,
            "months_with_data": 0
        }

    async def get_financial_profile_summary(
        self,
        user_id: UUID,
        months: int = 6
    ) -> Dict[str, Any]:
        """
        Obtiene un resumen del perfil financiero para UI.

        Args:
            user_id: ID del usuario
            months: Meses a analizar

        Returns:
            Resumen del perfil financiero
        """
        data = await self._get_financial_data(user_id, months)

        # Calcular métricas adicionales
        total_expenses = data["fixed_expenses"] + data["variable_expenses"]
        disposable_income = max(
            data["avg_income"] - total_expenses - data["debt_payments"], 0
        )

        # Evaluar salud financiera
        if data["savings_rate"] >= 0.20:
            health_status = "excellent"
        elif data["savings_rate"] >= 0.10:
            health_status = "good"
        elif data["savings_rate"] >= 0.05:
            health_status = "fair"
        elif data["savings_rate"] > 0:
            health_status = "needs_improvement"
        else:
            health_status = "critical"

        return {
            "monthly_income": data["avg_income"],
            "income_stability": round(
                max(1 - (data["income_std"] / data["avg_income"]
                    if data["avg_income"] > 0 else 0), 0) * 100, 1
            ),
            "fixed_expenses": data["fixed_expenses"],
            "variable_expenses": data["variable_expenses"],
            "debt_payments": data["debt_payments"],
            "disposable_income": round(disposable_income, 2),
            "savings_rate_percentage": round(data["savings_rate"] * 100, 1),
            "health_status": health_status,
            "currency": data["currency"],
            "analysis_period_months": data["months_with_data"]
        }
