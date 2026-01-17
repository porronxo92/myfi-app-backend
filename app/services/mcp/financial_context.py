"""
MCP Financial Context - Database Bridge
========================================

Proporciona funciones estructuradas que Gemini puede invocar a través del
Model Context Protocol para consultar datos financieros del usuario.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, extract
from decimal import Decimal
import statistics

from app.models.transaction import Transaction
from app.models.category import Category
from app.models.account import Account
from app.models.user import User


class MCPFinancialContext:
    """
    Capa MCP que expone funciones financieras estructuradas para Gemini.
    
    Cada método representa una herramienta que Gemini puede invocar para
    obtener información específica sobre las finanzas del usuario.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_context_definition(self) -> Dict[str, Any]:
        """
        Retorna la definición completa del contexto MCP que Gemini necesita.
        Incluye la lista de herramientas disponibles y sus descripciones.
        """
        return {
            "system_role": "financial_advisor",
            "available_tools": [
                {
                    "name": "get_user_financial_summary",
                    "description": "Obtiene un resumen general de la situación financiera del usuario",
                    "parameters": {
                        "user_id": "UUID del usuario",
                        "period": "Periodo temporal: 'current_month', 'last_month', 'current_year'"
                    },
                    "returns": "Resumen con ingresos, gastos, balance, número de cuentas y transacciones"
                },
                {
                    "name": "get_spending_by_category",
                    "description": "Desglose de gastos agrupados por categoría con porcentajes",
                    "parameters": {
                        "user_id": "UUID del usuario",
                        "period": "Periodo temporal"
                    },
                    "returns": "Lista de categorías con montos y porcentajes"
                },
                {
                    "name": "get_income_sources",
                    "description": "Identifica las fuentes de ingreso y sus montos",
                    "parameters": {
                        "user_id": "UUID del usuario",
                        "period": "Periodo temporal"
                    },
                    "returns": "Lista de categorías de ingreso con montos"
                },
                {
                    "name": "get_monthly_trend",
                    "description": "Tendencia mensual de ingresos, gastos y balance",
                    "parameters": {
                        "user_id": "UUID del usuario",
                        "months": "Número de meses a analizar (default 6)"
                    },
                    "returns": "Serie temporal con datos mensuales"
                },
                {
                    "name": "get_unusual_transactions",
                    "description": "Detecta transacciones atípicas basándose en desviación estándar",
                    "parameters": {
                        "user_id": "UUID del usuario",
                        "threshold": "Umbral de desviación estándar (default 2.0)"
                    },
                    "returns": "Lista de transacciones inusuales con explicación"
                },
                {
                    "name": "get_recurring_expenses",
                    "description": "Identifica gastos recurrentes (suscripciones, facturas fijas)",
                    "parameters": {
                        "user_id": "UUID del usuario"
                    },
                    "returns": "Lista de gastos recurrentes con frecuencia y monto"
                },
                {
                    "name": "get_savings_potential",
                    "description": "Analiza el potencial de ahorro por categoría",
                    "parameters": {
                        "user_id": "UUID del usuario"
                    },
                    "returns": "Categorías con oportunidades de reducción de gasto"
                },
                {
                    "name": "compare_periods",
                    "description": "Compara dos períodos temporales diferentes",
                    "parameters": {
                        "user_id": "UUID del usuario",
                        "period1": "Primer periodo",
                        "period2": "Segundo periodo"
                    },
                    "returns": "Comparativa detallada entre ambos periodos"
                }
            ],
            "database_schema": {
                "tables": ["users", "accounts", "transactions", "categories"],
                "main_relationships": "User -> Account -> Transaction -> Category"
            }
        }
    
    def _parse_period(self, period: str = 'current_month') -> tuple[datetime, datetime]:
        """
        Convierte una cadena de periodo en rango de fechas.
        
        Args:
            period: 'current_month', 'last_month', 'current_year', 'last_year', o 'YYYY-MM'
        
        Returns:
            Tupla (start_date, end_date)
        """
        now = datetime.now()
        
        # Verificar si es un formato YYYY-MM (ej: 2025-12, 2026-01)
        import re
        if re.match(r'^\d{4}-\d{2}$', period):
            year, month = map(int, period.split('-'))
            start = datetime(year, month, 1)
            # Calcular último día del mes
            if month == 12:
                end = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = datetime(year, month + 1, 1) - timedelta(days=1)
            return start, end
        
        # Periodos predefinidos
        if period == 'current_month':
            start = datetime(now.year, now.month, 1)
            # Último día del mes actual
            if now.month == 12:
                end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
        
        elif period == 'last_month':
            if now.month == 1:
                start = datetime(now.year - 1, 12, 1)
                end = datetime(now.year, 1, 1) - timedelta(days=1)
            else:
                start = datetime(now.year, now.month - 1, 1)
                end = datetime(now.year, now.month, 1) - timedelta(days=1)
        
        elif period == 'current_year':
            start = datetime(now.year, 1, 1)
            end = datetime(now.year, 12, 31)
        
        elif period == 'last_year':
            start = datetime(now.year - 1, 1, 1)
            end = datetime(now.year - 1, 12, 31)
        
        else:
            # Default a mes actual
            start = datetime(now.year, now.month, 1)
            if now.month == 12:
                end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
        
        return start, end
    
    def get_user_financial_summary(
        self, 
        user_id: UUID, 
        period: str = 'current_month',
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene un resumen general de la situación financiera del usuario.
        
        Args:
            user_id: ID del usuario
            period: Período a analizar
            account_id: UUID de cuenta específica como string (opcional). Si se proporciona, solo analiza esa cuenta.
        
        Returns:
            {
                "user_id": "...",
                "period": "2025-01",
                "total_income": 2500.00,
                "total_expenses": 1800.00,
                "net_balance": 700.00,
                "savings_rate": 28.0,
                "num_accounts": 3,
                "num_transactions": 45,
                "currency": "EUR"
            }
        """
        start_date, end_date = self._parse_period(period)
        
        # Obtener cuentas del usuario (filtrar por account_id si se proporciona)
        accounts_query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        )
        
        if account_id is not None:
            # Convertir string UUID a UUID object
            from uuid import UUID as UUIDType
            account_uuid = UUIDType(account_id) if isinstance(account_id, str) else account_id
            accounts_query = accounts_query.filter(Account.id == account_uuid)
        
        accounts = accounts_query.all()
        
        account_ids = [acc.id for acc in accounts]
        
        # Calcular ingresos totales
        total_income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date.date(),
            Transaction.date <= end_date.date(),
            Transaction.type == 'income'
        ).scalar() or Decimal('0.00')
        
        # Calcular gastos totales (en valor absoluto)
        total_expenses = self.db.query(func.sum(func.abs(Transaction.amount))).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date.date(),
            Transaction.date <= end_date.date(),
            Transaction.type == 'expense'
        ).scalar() or Decimal('0.00')
        
        # Conteo de transacciones
        num_transactions = self.db.query(func.count(Transaction.id)).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date.date(),
            Transaction.date <= end_date.date()
        ).scalar() or 0
        
        net_balance = float(total_income) - float(total_expenses)
        savings_rate = (net_balance / float(total_income) * 100) if float(total_income) > 0 else 0
        
        return {
            "user_id": str(user_id),
            "period": period,
            "period_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            },
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_balance": net_balance,
            "savings_rate": round(savings_rate, 2),
            "num_accounts": len(accounts),
            "num_transactions": num_transactions,
            "currency": accounts[0].currency if accounts else "EUR"
        }
    
    def get_spending_by_category(
        self, 
        user_id: UUID, 
        period: str = 'current_month',
        account_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Desglose de gastos agrupados por categoría.
        
        Args:
            user_id: ID del usuario
            period: Período a analizar
            account_id: UUID de cuenta específica como string (opcional)
        
        Returns:
            [
                {
                    "category_name": "Alimentación",
                    "category_id": "...",
                    "total": 450.50,
                    "percentage": 25.0,
                    "num_transactions": 12,
                    "avg_transaction": 37.54
                },
                ...
            ]
        """
        start_date, end_date = self._parse_period(period)
        
        # Obtener cuentas del usuario (filtrar por account_id si se proporciona)
        accounts_query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        )
        
        if account_id is not None:
            # Convertir string UUID a UUID object
            from uuid import UUID as UUIDType
            account_uuid = UUIDType(account_id) if isinstance(account_id, str) else account_id
            accounts_query = accounts_query.filter(Account.id == account_uuid)
        
        accounts = accounts_query.all()
        
        account_ids = [acc.id for acc in accounts]
        
        # Query agrupada por categoría
        category_spending = self.db.query(
            Category.id,
            Category.name,
            Category.color,
            func.sum(func.abs(Transaction.amount)).label('total'),
            func.count(Transaction.id).label('count'),
            func.avg(func.abs(Transaction.amount)).label('avg_amount')
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date.date(),
            Transaction.date <= end_date.date(),
            Transaction.type == 'expense'
        ).group_by(
            Category.id, Category.name, Category.color
        ).order_by(
            desc('total')
        ).all()
        
        # Calcular total general para porcentajes
        total_general = sum([float(cat.total) for cat in category_spending])
        
        result = []
        for cat in category_spending:
            percentage = (float(cat.total) / total_general * 100) if total_general > 0 else 0
            result.append({
                "category_id": str(cat.id),
                "category_name": cat.name,
                "color": cat.color,
                "total": float(cat.total),
                "percentage": round(percentage, 2),
                "num_transactions": cat.count,
                "avg_transaction": float(cat.avg_amount)
            })
        
        return result
    
    def get_income_sources(
        self, 
        user_id: UUID, 
        period: str = 'current_month',
        account_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Identifica las fuentes de ingreso del usuario.
        
        Args:
            user_id: ID del usuario
            period: Período a analizar
            account_id: UUID de cuenta específica como string (opcional)
        """
        start_date, end_date = self._parse_period(period)
        
        # Obtener cuentas del usuario (filtrar por account_id si se proporciona)
        accounts_query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        )
        
        if account_id is not None:
            # Convertir string UUID a UUID object
            from uuid import UUID as UUIDType
            account_uuid = UUIDType(account_id) if isinstance(account_id, str) else account_id
            accounts_query = accounts_query.filter(Account.id == account_uuid)
        
        accounts = accounts_query.all()
        
        account_ids = [acc.id for acc in accounts]
        
        income_sources = self.db.query(
            Category.id,
            Category.name,
            Category.color,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date.date(),
            Transaction.date <= end_date.date(),
            Transaction.type == 'income'
        ).group_by(
            Category.id, Category.name, Category.color
        ).order_by(
            desc('total')
        ).all()
        
        result = []
        for source in income_sources:
            result.append({
                "category_id": str(source.id),
                "category_name": source.name,
                "color": source.color,
                "total": float(source.total),
                "num_transactions": source.count
            })
        
        return result
    
    def get_monthly_trend(
        self, 
        user_id: UUID, 
        months: int = 6
    ) -> Dict[str, Any]:
        """
        Tendencia mensual de ingresos, gastos y balance.
        
        Returns:
            {
                "months": ["2024-08", "2024-09", ..., "2025-01"],
                "income": [2500, 2300, 2600, ...],
                "expenses": [1800, 1900, 2100, ...],
                "balance": [700, 400, 500, ...]
            }
        """
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()
        
        account_ids = [acc.id for acc in accounts]
        
        # Calcular fecha de inicio (N meses atrás)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months)
        
        # Query agrupada por año-mes
        monthly_data = self.db.query(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month'),
            Transaction.type,
            func.sum(func.abs(Transaction.amount)).label('total')
        ).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date.date()
        ).group_by(
            'year', 'month', Transaction.type
        ).order_by(
            'year', 'month'
        ).all()
        
        # Organizar datos por mes
        monthly_dict = {}
        for row in monthly_data:
            month_key = f"{int(row.year)}-{int(row.month):02d}"
            if month_key not in monthly_dict:
                monthly_dict[month_key] = {"income": 0, "expenses": 0}
            
            if row.type == 'income':
                monthly_dict[month_key]["income"] = float(row.total)
            elif row.type == 'expense':
                monthly_dict[month_key]["expenses"] = float(row.total)
        
        # Crear series temporales
        months_list = sorted(monthly_dict.keys())
        income_list = [monthly_dict[m]["income"] for m in months_list]
        expenses_list = [monthly_dict[m]["expenses"] for m in months_list]
        balance_list = [income - expense for income, expense in zip(income_list, expenses_list)]
        
        return {
            "months": months_list,
            "income": income_list,
            "expenses": expenses_list,
            "balance": balance_list
        }
    
    def get_unusual_transactions(
        self, 
        user_id: UUID, 
        threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Detecta transacciones atípicas basándose en desviación estándar.
        
        Args:
            threshold: Número de desviaciones estándar para considerar inusual
        
        Returns:
            Lista de transacciones con explicación de por qué son inusuales
        """
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()
        
        account_ids = [acc.id for acc in accounts]
        
        # Obtener todas las transacciones de los últimos 3 meses
        three_months_ago = datetime.now() - timedelta(days=90)
        
        transactions = self.db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= three_months_ago.date()
        ).all()
        
        if len(transactions) < 10:  # No hay suficientes datos
            return []
        
        # Calcular estadísticas por tipo
        expense_amounts = [float(abs(t.amount)) for t in transactions if t.type == 'expense']
        income_amounts = [float(t.amount) for t in transactions if t.type == 'income']
        
        unusual = []
        
        # Análisis de gastos
        if len(expense_amounts) >= 5:
            mean_expense = statistics.mean(expense_amounts)
            stdev_expense = statistics.stdev(expense_amounts) if len(expense_amounts) > 1 else 0
            
            for t in transactions:
                if t.type == 'expense':
                    amount = float(abs(t.amount))
                    if stdev_expense > 0:
                        z_score = (amount - mean_expense) / stdev_expense
                        if abs(z_score) >= threshold:
                            unusual.append({
                                "id": str(t.id),
                                "date": t.date.strftime("%Y-%m-%d"),
                                "description": t.description,
                                "amount": amount,
                                "type": t.type,
                                "category": t.category.name if t.category else "Sin categoría",
                                "z_score": round(z_score, 2),
                                "reason": f"{'Alto' if z_score > 0 else 'Bajo'} respecto a tu gasto promedio de €{mean_expense:.2f}"
                            })
        
        # Análisis de ingresos
        if len(income_amounts) >= 5:
            mean_income = statistics.mean(income_amounts)
            stdev_income = statistics.stdev(income_amounts) if len(income_amounts) > 1 else 0
            
            for t in transactions:
                if t.type == 'income':
                    amount = float(t.amount)
                    if stdev_income > 0:
                        z_score = (amount - mean_income) / stdev_income
                        if abs(z_score) >= threshold:
                            unusual.append({
                                "id": str(t.id),
                                "date": t.date.strftime("%Y-%m-%d"),
                                "description": t.description,
                                "amount": amount,
                                "type": t.type,
                                "category": t.category.name if t.category else "Sin categoría",
                                "z_score": round(z_score, 2),
                                "reason": f"{'Alto' if z_score > 0 else 'Bajo'} respecto a tu ingreso promedio de €{mean_income:.2f}"
                            })
        
        # Ordenar por z_score absoluto (más inusuales primero)
        unusual.sort(key=lambda x: abs(x['z_score']), reverse=True)
        
        return unusual[:10]  # Retornar top 10
    
    def get_recurring_expenses(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Identifica gastos recurrentes (suscripciones, facturas).
        
        Busca transacciones con:
        - Mismo monto (±5%)
        - Misma descripción (similarity)
        - Frecuencia mensual
        """
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()
        
        account_ids = [acc.id for acc in accounts]
        
        # Obtener transacciones de los últimos 6 meses
        six_months_ago = datetime.now() - timedelta(days=180)
        
        transactions = self.db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= six_months_ago.date(),
            Transaction.type == 'expense'
        ).order_by(Transaction.date).all()
        
        # Agrupar por descripción similar
        grouped = {}
        for t in transactions:
            desc_key = t.description.lower().strip()[:30]  # Primeros 30 caracteres
            if desc_key not in grouped:
                grouped[desc_key] = []
            grouped[desc_key].append(t)
        
        # Identificar recurrentes
        recurring = []
        for desc, trans_list in grouped.items():
            if len(trans_list) >= 3:  # Al menos 3 ocurrencias
                amounts = [float(abs(t.amount)) for t in trans_list]
                avg_amount = statistics.mean(amounts)
                stdev = statistics.stdev(amounts) if len(amounts) > 1 else 0
                
                # Verificar si los montos son similares (variación < 5%)
                if stdev / avg_amount < 0.05 if avg_amount > 0 else True:
                    # Calcular frecuencia (días promedio entre transacciones)
                    dates = sorted([t.date for t in trans_list])
                    intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                    avg_interval = statistics.mean(intervals) if intervals else 0
                    
                    frequency = "mensual" if 25 <= avg_interval <= 35 else \
                                "quincenal" if 12 <= avg_interval <= 17 else \
                                "semanal" if 6 <= avg_interval <= 8 else "irregular"
                    
                    recurring.append({
                        "description": trans_list[0].description,
                        "category": trans_list[0].category.name if trans_list[0].category else "Sin categoría",
                        "avg_amount": round(avg_amount, 2),
                        "frequency": frequency,
                        "occurrences": len(trans_list),
                        "last_date": dates[-1].strftime("%Y-%m-%d"),
                        "annual_cost": round(avg_amount * (365 / avg_interval if avg_interval > 0 else 12), 2)
                    })
        
        # Ordenar por costo anual
        recurring.sort(key=lambda x: x['annual_cost'], reverse=True)
        
        return recurring
    
    def get_savings_potential(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Analiza el potencial de ahorro comparando gastos actuales con promedios.
        """
        # Obtener gastos del mes actual
        current_spending = self.get_spending_by_category(user_id, 'current_month')
        
        # Obtener gastos de los últimos 6 meses
        six_months_spending = self.get_spending_by_category(user_id, 'last_6_months')
        
        # Comparar y encontrar oportunidades
        opportunities = []
        
        current_dict = {item['category_name']: item['total'] for item in current_spending}
        
        for cat in six_months_spending:
            cat_name = cat['category_name']
            avg_historical = cat['total'] / 6  # Promedio mensual
            current = current_dict.get(cat_name, 0)
            
            if current > avg_historical * 1.2:  # 20% más que el promedio
                excess = current - avg_historical
                opportunities.append({
                    "category": cat_name,
                    "current_spending": round(current, 2),
                    "historical_avg": round(avg_historical, 2),
                    "excess_amount": round(excess, 2),
                    "potential_savings_monthly": round(excess, 2),
                    "potential_savings_annual": round(excess * 12, 2),
                    "recommendation": f"Reducir {cat_name} al promedio histórico de €{avg_historical:.2f}"
                })
        
        opportunities.sort(key=lambda x: x['potential_savings_monthly'], reverse=True)
        
        return opportunities
    
    def compare_periods(
        self, 
        user_id: UUID, 
        period1: str = 'current_month', 
        period2: str = 'last_month'
    ) -> Dict[str, Any]:
        """
        Compara dos períodos temporales diferentes.
        """
        summary1 = self.get_user_financial_summary(user_id, period1)
        summary2 = self.get_user_financial_summary(user_id, period2)
        
        spending1 = self.get_spending_by_category(user_id, period1)
        spending2 = self.get_spending_by_category(user_id, period2)
        
        # Calcular diferencias
        income_diff = summary1['total_income'] - summary2['total_income']
        expenses_diff = summary1['total_expenses'] - summary2['total_expenses']
        balance_diff = summary1['net_balance'] - summary2['net_balance']
        
        income_pct = (income_diff / summary2['total_income'] * 100) if summary2['total_income'] > 0 else 0
        expenses_pct = (expenses_diff / summary2['total_expenses'] * 100) if summary2['total_expenses'] > 0 else 0
        
        # Comparar categorías
        spending1_dict = {item['category_name']: item['total'] for item in spending1}
        spending2_dict = {item['category_name']: item['total'] for item in spending2}
        
        category_changes = []
        all_categories = set(spending1_dict.keys()) | set(spending2_dict.keys())
        
        for cat in all_categories:
            amount1 = spending1_dict.get(cat, 0)
            amount2 = spending2_dict.get(cat, 0)
            diff = amount1 - amount2
            pct_change = (diff / amount2 * 100) if amount2 > 0 else (100 if amount1 > 0 else 0)
            
            if abs(pct_change) >= 10:  # Solo cambios significativos (>10%)
                category_changes.append({
                    "category": cat,
                    "period1_amount": round(amount1, 2),
                    "period2_amount": round(amount2, 2),
                    "difference": round(diff, 2),
                    "percentage_change": round(pct_change, 2)
                })
        
        category_changes.sort(key=lambda x: abs(x['percentage_change']), reverse=True)
        
        return {
            "period1": summary1['period_range'],
            "period2": summary2['period_range'],
            "summary_comparison": {
                "income": {
                    "period1": summary1['total_income'],
                    "period2": summary2['total_income'],
                    "difference": round(income_diff, 2),
                    "percentage_change": round(income_pct, 2)
                },
                "expenses": {
                    "period1": summary1['total_expenses'],
                    "period2": summary2['total_expenses'],
                    "difference": round(expenses_diff, 2),
                    "percentage_change": round(expenses_pct, 2)
                },
                "balance": {
                    "period1": summary1['net_balance'],
                    "period2": summary2['net_balance'],
                    "difference": round(balance_diff, 2)
                }
            },
            "category_changes": category_changes[:10],  # Top 10 cambios
            "insights": self._generate_comparison_insights(
                income_pct, expenses_pct, category_changes
            )
        }
    
    def _generate_comparison_insights(
        self, 
        income_pct: float, 
        expenses_pct: float, 
        category_changes: List[Dict]
    ) -> List[str]:
        """Genera insights textuales simples de la comparación."""
        insights = []
        
        if income_pct > 10:
            insights.append(f"Tus ingresos aumentaron un {income_pct:.1f}%")
        elif income_pct < -10:
            insights.append(f"Tus ingresos disminuyeron un {abs(income_pct):.1f}%")
        
        if expenses_pct > 10:
            insights.append(f"Tus gastos aumentaron un {expenses_pct:.1f}%")
        elif expenses_pct < -10:
            insights.append(f"Redujiste tus gastos un {abs(expenses_pct):.1f}%")
        
        if category_changes:
            top_change = category_changes[0]
            if top_change['percentage_change'] > 0:
                insights.append(
                    f"Mayor incremento en {top_change['category']}: "
                    f"+{top_change['percentage_change']:.0f}%"
                )
        
        return insights
