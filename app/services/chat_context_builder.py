"""
Chat Context Builder - Agregador de datos financieros
=====================================================

Construye el contexto completo con todos los datos financieros del usuario
para inyectarlo en el prompt del agente conversacional.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.budget import Budget
from app.models.budget_item import BudgetItem
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChatContextBuilder:
    """
    Construye el contexto financiero completo del usuario para el agente.

    Este contexto se inyecta en el system prompt de Gemini para que el agente
    tenga acceso a todos los datos financieros del usuario.
    """

    def __init__(self, db: Session, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.today = date.today()
        self.current_month = self.today.month
        self.current_year = self.today.year

    def build(self) -> Dict[str, Any]:
        """
        Construye el contexto completo con todos los datos financieros.

        Returns:
            Dict con toda la información financiera del usuario
        """
        logger.info(f"Construyendo contexto de chat para user_id: {self.user_id}")

        context = {
            "fecha_actual": self.today.isoformat(),
            "usuario": self._get_user_info(),
            "cuentas": self._get_accounts_summary(),
            "resumen_mensual": self._get_monthly_summaries(),
            "categorias_gasto": self._get_top_expense_categories(),
            "categorias_ingreso": self._get_top_income_categories(),
            "presupuestos": self._get_budgets_status(),
            "salud_financiera": self._get_health_metrics(),
            "categorias_disponibles": self._get_available_categories()
        }

        logger.info(f"Contexto construido: {len(str(context))} caracteres")
        return context

    def _get_user_info(self) -> Dict[str, Any]:
        """Obtiene información básica del usuario."""
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user:
            return {"nombre": "Usuario"}

        return {
            "nombre": user.full_name or user.username or user.email.split("@")[0],
            "email": user.email
        }

    def _get_accounts_summary(self) -> List[Dict[str, Any]]:
        """Obtiene resumen de todas las cuentas activas."""
        accounts = self.db.query(Account).filter(
            Account.user_id == self.user_id,
            Account.is_active == True
        ).all()

        result = []
        total_balance = Decimal("0")

        for acc in accounts:
            balance = acc.get_balance_as_decimal()
            total_balance += balance
            result.append({
                "id": str(acc.id),
                "nombre": acc.name,
                "tipo": acc.type,
                "saldo": float(balance),
                "moneda": acc.currency,
                "banco": acc.bank_name
            })

        # Añadir totales al final
        return {
            "cuentas": result,
            "total_cuentas": len(result),
            "saldo_total": float(total_balance)
        }

    def _get_monthly_summaries(self) -> Dict[str, Any]:
        """Obtiene resumen de ingresos/gastos de los últimos 3 meses."""
        summaries = {}

        for months_ago in range(3):
            target_date = self.today - timedelta(days=30 * months_ago)
            month = target_date.month
            year = target_date.year

            month_name = self._get_month_name(month, months_ago)
            summaries[month_name] = self._calculate_month_summary(year, month)

        return summaries

    def _get_month_name(self, month: int, months_ago: int) -> str:
        """Genera nombre descriptivo del mes."""
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        if months_ago == 0:
            return "mes_actual"
        elif months_ago == 1:
            return "mes_anterior"
        else:
            return f"hace_{months_ago}_meses"

    def _calculate_month_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Calcula resumen de un mes específico."""
        # Obtener todas las transacciones del mes
        transactions = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == self.user_id,
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).all()

        total_income = Decimal("0")
        total_expenses = Decimal("0")

        for t in transactions:
            amount = Decimal(str(t.amount)) if t.amount else Decimal("0")
            if t.type == "income":
                total_income += abs(amount)
            elif t.type == "expense":
                total_expenses += abs(amount)

        balance = total_income - total_expenses
        savings_rate = (balance / total_income * 100) if total_income > 0 else 0

        return {
            "ingresos": float(total_income),
            "gastos": float(total_expenses),
            "balance": float(balance),
            "tasa_ahorro": round(float(savings_rate), 1),
            "num_transacciones": len(transactions)
        }

    def _get_top_expense_categories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtiene las principales categorías de gasto del mes actual."""
        return self._get_top_categories_by_type("expense", limit)

    def _get_top_income_categories(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtiene las principales categorías de ingreso del mes actual."""
        return self._get_top_categories_by_type("income", limit)

    def _get_top_categories_by_type(self, cat_type: str, limit: int) -> List[Dict[str, Any]]:
        """Obtiene categorías ordenadas por monto para el mes actual."""
        transactions = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).join(
            Category, Transaction.category_id == Category.id
        ).filter(
            Account.user_id == self.user_id,
            Category.type == cat_type,
            extract('year', Transaction.date) == self.current_year,
            extract('month', Transaction.date) == self.current_month
        ).all()

        # Agrupar por categoría en Python (amount está encriptado)
        category_totals: Dict[str, Dict] = {}

        for t in transactions:
            if not t.category:
                continue
            cat_id = str(t.category_id)
            amount = abs(Decimal(str(t.amount))) if t.amount else Decimal("0")

            if cat_id not in category_totals:
                category_totals[cat_id] = {
                    "id": cat_id,
                    "nombre": t.category.name,
                    "color": t.category.color,
                    "total": Decimal("0"),
                    "num_transacciones": 0
                }

            category_totals[cat_id]["total"] += amount
            category_totals[cat_id]["num_transacciones"] += 1

        # Ordenar por total y limitar
        sorted_cats = sorted(
            category_totals.values(),
            key=lambda x: x["total"],
            reverse=True
        )[:limit]

        # Calcular porcentajes
        total_amount = sum(c["total"] for c in sorted_cats)

        result = []
        for cat in sorted_cats:
            percentage = (cat["total"] / total_amount * 100) if total_amount > 0 else 0
            result.append({
                "id": cat["id"],
                "nombre": cat["nombre"],
                "color": cat["color"],
                "total": float(cat["total"]),
                "porcentaje": round(float(percentage), 1),
                "num_transacciones": cat["num_transacciones"]
            })

        return result

    def _get_budgets_status(self) -> List[Dict[str, Any]]:
        """Obtiene estado de presupuestos activos."""
        # Buscar presupuesto del mes actual
        budget = self.db.query(Budget).filter(
            Budget.user_id == self.user_id,
            Budget.month == self.current_month,
            Budget.year == self.current_year
        ).first()

        if not budget:
            return []

        items = self.db.query(BudgetItem).filter(
            BudgetItem.budget_id == budget.id
        ).all()

        result = []
        for item in items:
            allocated = float(item.allocated_amount) if item.allocated_amount else 0
            spent = self._calculate_category_spent(item.category_id)
            remaining = allocated - spent
            percentage = (spent / allocated * 100) if allocated > 0 else 0

            category = self.db.query(Category).filter(Category.id == item.category_id).first()

            result.append({
                "categoria": category.name if category else "Sin categoría",
                "asignado": allocated,
                "gastado": spent,
                "restante": remaining,
                "porcentaje_usado": round(percentage, 1),
                "estado": "excedido" if spent > allocated else ("advertencia" if percentage > 80 else "ok")
            })

        return result

    def _calculate_category_spent(self, category_id: UUID) -> float:
        """Calcula el gasto total en una categoría para el mes actual."""
        transactions = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == self.user_id,
            Transaction.category_id == category_id,
            Transaction.type == "expense",
            extract('year', Transaction.date) == self.current_year,
            extract('month', Transaction.date) == self.current_month
        ).all()

        total = sum(abs(Decimal(str(t.amount))) for t in transactions if t.amount)
        return float(total)

    def _get_health_metrics(self) -> Dict[str, Any]:
        """Calcula métricas básicas de salud financiera."""
        current = self._calculate_month_summary(self.current_year, self.current_month)

        # Calcular métricas simples
        savings_rate = current["tasa_ahorro"]

        # Score simple basado en tasa de ahorro
        if savings_rate >= 20:
            score = 80 + min(20, savings_rate - 20)
            category = "Excelente"
        elif savings_rate >= 10:
            score = 60 + (savings_rate - 10) * 2
            category = "Buena"
        elif savings_rate >= 0:
            score = 40 + savings_rate * 2
            category = "Regular"
        else:
            score = max(0, 40 + savings_rate)
            category = "Necesita atención"

        return {
            "score": round(score),
            "categoria": category,
            "tasa_ahorro_actual": savings_rate,
            "ingresos_mes": current["ingresos"],
            "gastos_mes": current["gastos"],
            "balance_mes": current["balance"]
        }

    def _get_available_categories(self) -> Dict[str, List[str]]:
        """Obtiene todas las categorías disponibles para el usuario."""
        categories = self.db.query(Category).filter(
            Category.user_id == self.user_id
        ).all()

        expense_cats = [c.name for c in categories if c.type == "expense"]
        income_cats = [c.name for c in categories if c.type == "income"]

        return {
            "gastos": expense_cats,
            "ingresos": income_cats
        }
