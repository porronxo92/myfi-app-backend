"""
Analytics Service - Análisis Cuantitativos
==========================================

Servicio para cálculos cuantitativos sobre datos financieros.
NO genera texto, solo datos estructurados y métricas.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, extract
from decimal import Decimal
import statistics

from app.models.transaction import Transaction
from app.models.category import Category
from app.models.account import Account
from app.services.mcp.financial_context import MCPFinancialContext
from app.schemas.analytics import (
    MonthlySummaryResponse,
    PeriodRange,
    CategoryBreakdownResponse,
    CategoryBreakdownItem,
    TrendAnalysisResponse,
    MonthlyDataPoint,
    AnomaliesResponse,
    UnusualTransaction,
    RecurringExpensesResponse,
    RecurringExpense,
    SavingsPotentialResponse,
    SavingOpportunity,
    PeriodComparisonResponse,
    ChartData,
    ChartDataset,
    AnalyticsWithChartsResponse
)


class AnalyticsService:
    """
    Servicio de analytics financieros.
    
    Proporciona funciones para cálculos cuantitativos, tendencias,
    detección de anomalías y preparación de datos para visualización.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.mcp = MCPFinancialContext(db)
    
    async def calculate_monthly_summary(
        self, 
        user_id: UUID, 
        period: str = 'current_month',
        account_id: Optional[str] = None
    ) -> MonthlySummaryResponse:
        """
        Calcula el resumen financiero mensual del usuario.
        
        Args:
            user_id: ID del usuario
            period: Período a analizar ('current_month', 'last_month', etc.)
            account_id: UUID de cuenta específica (opcional)
        
        Returns:
            MonthlySummaryResponse con todos los datos del resumen
        """
        # Usar la función MCP para obtener los datos
        summary_data = self.mcp.get_user_financial_summary(user_id, period, account_id)
        
        # Convertir a schema Pydantic
        return MonthlySummaryResponse(
            user_id=summary_data['user_id'],
            period=summary_data['period'],
            period_range=PeriodRange(
                start=summary_data['period_range']['start'],
                end=summary_data['period_range']['end']
            ),
            total_income=summary_data['total_income'],
            total_expenses=summary_data['total_expenses'],
            net_balance=summary_data['net_balance'],
            savings_rate=summary_data['savings_rate'],
            num_accounts=summary_data['num_accounts'],
            num_transactions=summary_data['num_transactions'],
            currency=summary_data['currency']
        )
    
    async def get_category_breakdown(
        self, 
        user_id: UUID, 
        transaction_type: str = 'expense',
        period: str = 'current_month',
        account_id: Optional[str] = None
    ) -> CategoryBreakdownResponse:
        """
        Obtiene el desglose por categorías.
        
        Args:
            user_id: ID del usuario
            transaction_type: 'income' o 'expense'
            period: Período a analizar
            account_id: UUID de cuenta específica (opcional)
        
        Returns:
            CategoryBreakdownResponse con desglose detallado
        """
        if transaction_type == 'expense':
            categories_data = self.mcp.get_spending_by_category(user_id, period, account_id)
        else:
            categories_data = self.mcp.get_income_sources(user_id, period, account_id)
        
        # Parsear período
        start_date, end_date = self.mcp._parse_period(period)
        
        # Convertir a items de schema
        category_items = [
            CategoryBreakdownItem(
                category_id=cat['category_id'],
                category_name=cat['category_name'],
                color=cat.get('color'),
                total=cat['total'],
                percentage=cat['percentage'],
                num_transactions=cat['num_transactions'],
                avg_transaction=cat.get('avg_transaction', cat['total'] / cat['num_transactions'] if cat['num_transactions'] > 0 else 0)
            )
            for cat in categories_data
        ]
        
        total_amount = sum(item.total for item in category_items)
        
        return CategoryBreakdownResponse(
            period=period,
            period_range=PeriodRange(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d")
            ),
            transaction_type=transaction_type,
            categories=category_items,
            total_amount=total_amount
        )
    
    async def get_spending_trends(
        self, 
        user_id: UUID, 
        months: int = 6
    ) -> TrendAnalysisResponse:
        """
        Analiza tendencias de gastos e ingresos.
        
        Args:
            user_id: ID del usuario
            months: Número de meses a analizar
        
        Returns:
            TrendAnalysisResponse con datos de tendencia
        """
        trend_data = self.mcp.get_monthly_trend(user_id, months)
        
        # Convertir a data points
        data_points = [
            MonthlyDataPoint(
                month=month,
                income=income,
                expenses=expense,
                balance=balance
            )
            for month, income, expense, balance in zip(
                trend_data['months'],
                trend_data['income'],
                trend_data['expenses'],
                trend_data['balance']
            )
        ]
        
        # Calcular promedios
        avg_income = statistics.mean(trend_data['income']) if trend_data['income'] else 0
        avg_expenses = statistics.mean(trend_data['expenses']) if trend_data['expenses'] else 0
        avg_balance = statistics.mean(trend_data['balance']) if trend_data['balance'] else 0
        
        # Determinar tendencia
        if len(trend_data['balance']) >= 3:
            recent_balances = trend_data['balance'][-3:]
            older_balances = trend_data['balance'][-6:-3] if len(trend_data['balance']) >= 6 else trend_data['balance'][:-3]
            
            avg_recent = statistics.mean(recent_balances) if recent_balances else 0
            avg_older = statistics.mean(older_balances) if older_balances else avg_recent
            
            if avg_recent > avg_older * 1.1:
                trend_direction = "improving"
            elif avg_recent < avg_older * 0.9:
                trend_direction = "declining"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "stable"
        
        return TrendAnalysisResponse(
            months=months,
            data_points=data_points,
            avg_income=avg_income,
            avg_expenses=avg_expenses,
            avg_balance=avg_balance,
            trend_direction=trend_direction
        )
    
    async def detect_anomalies(
        self, 
        user_id: UUID, 
        threshold: float = 2.0
    ) -> AnomaliesResponse:
        """
        Detecta transacciones anómalas.
        
        Args:
            user_id: ID del usuario
            threshold: Umbral de z-score (default 2.0)
        
        Returns:
            AnomaliesResponse con transacciones inusuales
        """
        unusual_data = self.mcp.get_unusual_transactions(user_id, threshold)
        
        # Convertir a schema
        anomalies = [
            UnusualTransaction(
                id=item['id'],
                date=item['date'],
                description=item['description'],
                amount=item['amount'],
                type=item['type'],
                category=item['category'],
                z_score=item['z_score'],
                reason=item['reason']
            )
            for item in unusual_data
        ]
        
        return AnomaliesResponse(
            threshold=threshold,
            num_anomalies=len(anomalies),
            anomalies=anomalies
        )
    
    async def calculate_savings_rate(
        self, 
        user_id: UUID, 
        period: str = 'current_month'
    ) -> Dict[str, Any]:
        """
        Calcula la tasa de ahorro del período.
        
        Returns:
            {
                "period": "current_month",
                "savings_rate": 28.0,
                "savings_amount": 700.00,
                "income": 2500.00,
                "expenses": 1800.00
            }
        """
        summary = await self.calculate_monthly_summary(user_id, period)
        
        return {
            "period": period,
            "savings_rate": summary.savings_rate,
            "savings_amount": summary.net_balance,
            "income": summary.total_income,
            "expenses": summary.total_expenses
        }
    
    async def get_top_merchants(
        self, 
        user_id: UUID, 
        limit: int = 10,
        period: str = 'current_month'
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los principales comercios/conceptos por volumen de gasto.
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de resultados
            period: Período a analizar
        
        Returns:
            Lista de comercios ordenados por gasto total
        """
        start_date, end_date = self.mcp._parse_period(period)
        
        # Obtener cuentas del usuario
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()
        
        account_ids = [acc.id for acc in accounts]
        
        # Query para agrupar por descripción (merchant)
        top_merchants = self.db.query(
            Transaction.description,
            Category.name.label('category_name'),
            func.count(Transaction.id).label('count'),
            func.sum(func.abs(Transaction.amount)).label('total')
        ).outerjoin(
            Category, Transaction.category_id == Category.id
        ).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date.date(),
            Transaction.date <= end_date.date(),
            Transaction.type == 'expense'
        ).group_by(
            Transaction.description, Category.name
        ).order_by(
            desc('total')
        ).limit(limit).all()
        
        result = []
        for merchant in top_merchants:
            result.append({
                "merchant": merchant.description,
                "category": merchant.category_name or "Sin categoría",
                "num_transactions": merchant.count,
                "total_spent": float(merchant.total)
            })
        
        return result
    
    async def get_recurring_expenses(self, user_id: UUID) -> RecurringExpensesResponse:
        """
        Identifica gastos recurrentes (suscripciones, facturas).
        
        Returns:
            RecurringExpensesResponse con lista de gastos recurrentes
        """
        recurring_data = self.mcp.get_recurring_expenses(user_id)
        
        # Convertir a schema
        recurring_items = [
            RecurringExpense(
                description=item['description'],
                category=item['category'],
                avg_amount=item['avg_amount'],
                frequency=item['frequency'],
                occurrences=item['occurrences'],
                last_date=item['last_date'],
                annual_cost=item['annual_cost']
            )
            for item in recurring_data
        ]
        
        total_annual = sum(item.annual_cost for item in recurring_items)
        
        return RecurringExpensesResponse(
            num_recurring=len(recurring_items),
            total_annual_cost=total_annual,
            recurring_expenses=recurring_items
        )
    
    async def get_savings_potential(self, user_id: UUID) -> SavingsPotentialResponse:
        """
        Analiza el potencial de ahorro del usuario.
        
        Returns:
            SavingsPotentialResponse con oportunidades identificadas
        """
        # Nota: MCP necesita implementar last_6_months
        # Por ahora, usaremos current_month vs promedio histórico simulado
        opportunities_data = self.mcp.get_savings_potential(user_id)
        
        # Convertir a schema
        opportunities = [
            SavingOpportunity(
                category=item['category'],
                current_spending=item['current_spending'],
                historical_avg=item['historical_avg'],
                excess_amount=item['excess_amount'],
                potential_savings_monthly=item['potential_savings_monthly'],
                potential_savings_annual=item['potential_savings_annual'],
                recommendation=item['recommendation']
            )
            for item in opportunities_data
        ]
        
        total_monthly = sum(opp.potential_savings_monthly for opp in opportunities)
        total_annual = sum(opp.potential_savings_annual for opp in opportunities)
        
        return SavingsPotentialResponse(
            num_opportunities=len(opportunities),
            total_potential_monthly=total_monthly,
            total_potential_annual=total_annual,
            opportunities=opportunities
        )
    
    async def compare_periods(
        self, 
        user_id: UUID, 
        period1: str = 'current_month',
        period2: str = 'last_month'
    ) -> PeriodComparisonResponse:
        """
        Compara dos períodos diferentes.
        
        Returns:
            PeriodComparisonResponse con análisis comparativo
        """
        comparison_data = self.mcp.compare_periods(user_id, period1, period2)
        
        # El MCP ya retorna el formato correcto
        return PeriodComparisonResponse(**comparison_data)
    
    # ===== FUNCIONES PARA CHART.JS =====
    
    async def get_category_pie_chart_data(
        self, 
        user_id: UUID, 
        transaction_type: str = 'expense',
        period: str = 'current_month'
    ) -> AnalyticsWithChartsResponse:
        """
        Prepara datos para gráfico de pastel (pie chart) de categorías.
        
        Returns:
            Datos analíticos + datos formateados para Chart.js
        """
        breakdown = await self.get_category_breakdown(user_id, transaction_type, period)
        
        # Extraer labels y data
        labels = [cat.category_name for cat in breakdown.categories]
        data = [cat.total for cat in breakdown.categories]
        colors = [cat.color or '#6B7280' for cat in breakdown.categories]
        
        chart_data = ChartData(
            labels=labels,
            datasets=[
                ChartDataset(
                    label=f"{'Gastos' if transaction_type == 'expense' else 'Ingresos'} por Categoría",
                    data=data,
                    backgroundColor=colors
                )
            ]
        )
        
        return AnalyticsWithChartsResponse(
            analytics_data=breakdown.dict(),
            chart_data=chart_data,
            chart_type="pie"
        )
    
    async def get_trend_line_chart_data(
        self, 
        user_id: UUID, 
        months: int = 6
    ) -> AnalyticsWithChartsResponse:
        """
        Prepara datos para gráfico de líneas de tendencia.
        
        Returns:
            Datos analíticos + datos formateados para Chart.js
        """
        trends = await self.get_spending_trends(user_id, months)
        
        labels = [dp.month for dp in trends.data_points]
        income_data = [dp.income for dp in trends.data_points]
        expenses_data = [dp.expenses for dp in trends.data_points]
        balance_data = [dp.balance for dp in trends.data_points]
        
        chart_data = ChartData(
            labels=labels,
            datasets=[
                ChartDataset(
                    label="Ingresos",
                    data=income_data,
                    borderColor="#10B981",
                    backgroundColor=["#10B98120"],
                    fill=False
                ),
                ChartDataset(
                    label="Gastos",
                    data=expenses_data,
                    borderColor="#EF4444",
                    backgroundColor=["#EF444420"],
                    fill=False
                ),
                ChartDataset(
                    label="Balance",
                    data=balance_data,
                    borderColor="#3B82F6",
                    backgroundColor=["#3B82F620"],
                    fill=True
                )
            ]
        )
        
        return AnalyticsWithChartsResponse(
            analytics_data=trends.dict(),
            chart_data=chart_data,
            chart_type="line"
        )
    
    async def get_top_merchants_bar_chart_data(
        self, 
        user_id: UUID, 
        limit: int = 10,
        period: str = 'current_month'
    ) -> AnalyticsWithChartsResponse:
        """
        Prepara datos para gráfico de barras de top comercios.
        
        Returns:
            Datos analíticos + datos formateados para Chart.js
        """
        merchants = await self.get_top_merchants(user_id, limit, period)
        
        labels = [m['merchant'][:30] + '...' if len(m['merchant']) > 30 else m['merchant'] for m in merchants]
        data = [m['total_spent'] for m in merchants]
        
        # Generar lista de colores (uno por cada barra)
        colors = ["#3B82F6", "#8B5CF6", "#EC4899", "#10B981", "#F59E0B", 
                  "#EF4444", "#06B6D4", "#6366F1", "#84CC16", "#F97316"]
        bar_colors = [colors[i % len(colors)] for i in range(len(data))]
        
        chart_data = ChartData(
            labels=labels,
            datasets=[
                ChartDataset(
                    label="Gasto Total (€)",
                    data=data,
                    backgroundColor=bar_colors
                )
            ]
        )
        
        return AnalyticsWithChartsResponse(
            analytics_data={"merchants": merchants},
            chart_data=chart_data,
            chart_type="bar"
        )

    # ============================================
    # NUEVOS MÉTODOS PARA DATOS ANUALES
    # ============================================

    async def get_annual_balance(
        self,
        user_id: UUID,
        year: int,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene el balance inicial (1 enero) y balance actual del año.
        """
        from datetime import datetime, date
        
        # Construir fechas
        start_of_year = date(year, 1, 1)
        end_of_year = date(year, 12, 31)
        today = datetime.now().date()
        last_date = min(today, end_of_year)
        
        # Filtrar cuentas
        accounts_query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        )
        
        if account_id:
            from uuid import UUID as UUIDType
            account_uuid = UUIDType(account_id) if isinstance(account_id, str) else account_id
            accounts_query = accounts_query.filter(Account.id == account_uuid)
        
        accounts = accounts_query.all()
        account_ids = [acc.id for acc in accounts]
        
        if not account_ids:
            return {
                "year": year,
                "account_id": account_id,
                "initial_balance": 0.0,
                "current_balance": 0.0,
                "currency": "EUR",
                "last_update_date": str(last_date)
            }
        
        # Balance actual de las cuentas
        current_balance = sum([float(acc.balance) for acc in accounts])
        
        # Calcular balance inicial del año (31 de diciembre del año anterior)
        # Balance inicial = Balance actual - (Ingresos del año - Gastos del año)
        
        # Obtener todas las transacciones del año actual
        transactions_this_year = self.db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_of_year,
            Transaction.date <= last_date
        ).all()
        
        # Sumar ingresos y gastos del año
        total_income_year = sum([float(t.amount) for t in transactions_this_year if t.type == 'income'])
        total_expenses_year = sum([abs(float(t.amount)) for t in transactions_this_year if t.type == 'expense'])
        
        # Balance inicial = Balance actual - Ingresos + Gastos
        # (revertimos las operaciones del año para llegar al balance del 31/12 del año anterior)
        initial_balance = current_balance - total_income_year + total_expenses_year
        
        return {
            "year": year,
            "account_id": account_id,
            "initial_balance": round(initial_balance, 2),
            "current_balance": round(current_balance, 2),
            "currency": accounts[0].currency if accounts else "EUR",
            "last_update_date": str(last_date)
        }

    async def get_annual_savings_rate(
        self,
        user_id: UUID,
        year: int,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calcula la tasa de ahorro anual.
        """
        from datetime import date
        
        balance_data = await self.get_annual_balance(user_id, year, account_id)
        
        initial = balance_data['initial_balance']
        current = balance_data['current_balance']
        
        savings_amount = current - initial
        savings_percentage = (savings_amount / initial * 100) if initial != 0 else 0
        
        start_of_year = date(year, 1, 1)
        today = date.today()
        
        return {
            "year": year,
            "account_id": account_id,
            "initial_balance": initial,
            "current_balance": current,
            "savings_amount": savings_amount,
            "savings_percentage": round(savings_percentage, 2),
            "period": {
                "from": str(start_of_year),
                "to": str(min(today, date(year, 12, 31)))
            }
        }

    async def get_annual_income(
        self,
        user_id: UUID,
        year: int,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suma total de ingresos del año hasta la fecha.
        """
        from datetime import date
        
        start_of_year = date(year, 1, 1)
        end_of_year = date(year, 12, 31)
        today = date.today()
        last_date = min(today, end_of_year)
        
        # Filtrar cuentas
        accounts_query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        )
        
        if account_id:
            from uuid import UUID as UUIDType
            account_uuid = UUIDType(account_id) if isinstance(account_id, str) else account_id
            accounts_query = accounts_query.filter(Account.id == account_uuid)
        
        accounts = accounts_query.all()
        account_ids = [acc.id for acc in accounts]
        
        if not account_ids:
            return {
                "year": year,
                "account_id": account_id,
                "total_income": 0.0,
                "months_with_data": 0,
                "monthly_average": 0.0,
                "breakdown_by_month": [],
                "currency": "EUR"
            }
        
        # Calcular ingresos totales
        total_income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_of_year,
            Transaction.date <= last_date,
            Transaction.type == 'income'
        ).scalar() or Decimal('0.00')
        
        # Obtener desglose por mes
        monthly_data = self.db.query(
            extract('month', Transaction.date).label('month'),
            func.sum(Transaction.amount).label('income')
        ).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_of_year,
            Transaction.date <= last_date,
            Transaction.type == 'income'
        ).group_by(
            extract('month', Transaction.date)
        ).all()
        
        breakdown = [
            {"month": int(m.month), "income": float(m.income)}
            for m in monthly_data
        ]
        
        months_with_data = len(breakdown)
        monthly_average = float(total_income) / months_with_data if months_with_data > 0 else 0.0
        
        return {
            "year": year,
            "account_id": account_id,
            "total_income": float(total_income),
            "months_with_data": months_with_data,
            "monthly_average": round(monthly_average, 2),
            "breakdown_by_month": breakdown,
            "currency": accounts[0].currency if accounts else "EUR"
        }

    async def get_annual_expenses(
        self,
        user_id: UUID,
        year: int,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suma total de gastos del año hasta la fecha.
        """
        from datetime import date
        
        start_of_year = date(year, 1, 1)
        end_of_year = date(year, 12, 31)
        today = date.today()
        last_date = min(today, end_of_year)
        
        # Filtrar cuentas
        accounts_query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        )
        
        if account_id:
            from uuid import UUID as UUIDType
            account_uuid = UUIDType(account_id) if isinstance(account_id, str) else account_id
            accounts_query = accounts_query.filter(Account.id == account_uuid)
        
        accounts = accounts_query.all()
        account_ids = [acc.id for acc in accounts]
        
        if not account_ids:
            return {
                "year": year,
                "account_id": account_id,
                "total_expenses": 0.0,
                "months_with_data": 0,
                "monthly_average": 0.0,
                "breakdown_by_month": [],
                "currency": "EUR"
            }
        
        # Calcular gastos totales (valor absoluto)
        total_expenses = self.db.query(func.sum(func.abs(Transaction.amount))).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_of_year,
            Transaction.date <= last_date,
            Transaction.type == 'expense'
        ).scalar() or Decimal('0.00')
        
        # Obtener desglose por mes
        monthly_data = self.db.query(
            extract('month', Transaction.date).label('month'),
            func.sum(func.abs(Transaction.amount)).label('expenses')
        ).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_of_year,
            Transaction.date <= last_date,
            Transaction.type == 'expense'
        ).group_by(
            extract('month', Transaction.date)
        ).all()
        
        breakdown = [
            {"month": int(m.month), "expenses": float(m.expenses)}
            for m in monthly_data
        ]
        
        months_with_data = len(breakdown)
        monthly_average = float(total_expenses) / months_with_data if months_with_data > 0 else 0.0
        
        return {
            "year": year,
            "account_id": account_id,
            "total_expenses": float(total_expenses),
            "months_with_data": months_with_data,
            "monthly_average": round(monthly_average, 2),
            "breakdown_by_month": breakdown,
            "currency": accounts[0].currency if accounts else "EUR"
        }

    async def get_monthly_category_breakdown(
        self,
        user_id: UUID,
        year: int,
        month: int,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene desglose de ingresos y gastos por categoría para un mes específico.
        
        Returns:
            Dict con estructura:
            {
                "income": {"categories": [...], "total": float},
                "expenses": {"categories": [...], "total": float},
                "period": {"year": int, "month": int}
            }
        """
        from datetime import date
        from uuid import UUID as UUIDType
        
        # Construir rango de fechas del mes
        start_of_month = date(year, month, 1)
        if month == 12:
            end_of_month = date(year + 1, 1, 1)
        else:
            end_of_month = date(year, month + 1, 1)
        
        # Filtrar cuentas
        accounts_query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        )
        
        if account_id:
            account_uuid = UUIDType(account_id) if isinstance(account_id, str) else account_id
            accounts_query = accounts_query.filter(Account.id == account_uuid)
        
        accounts = accounts_query.all()
        account_ids = [acc.id for acc in accounts]
        
        if not account_ids:
            return {
                "income": {"categories": [], "total": 0.0},
                "expenses": {"categories": [], "total": 0.0},
                "period": {"year": year, "month": month}
            }
        
        # Query para ingresos por categoría
        income_data = self.db.query(
            Category.name.label('category'),
            Category.color,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_of_month,
            Transaction.date < end_of_month,
            Transaction.type == 'income'
        ).group_by(Category.name, Category.color).all()
        
        # Query para gastos por categoría
        expense_data = self.db.query(
            Category.name.label('category'),
            Category.color,
            func.sum(func.abs(Transaction.amount)).label('total'),
            func.count(Transaction.id).label('count')
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_of_month,
            Transaction.date < end_of_month,
            Transaction.type == 'expense'
        ).group_by(Category.name, Category.color).all()
        
        # Procesar ingresos
        income_total = sum([float(row.total) for row in income_data])
        income_categories = [
            {
                "category": row.category,
                "total": round(float(row.total), 2),
                "percentage": round((float(row.total) / income_total * 100), 2) if income_total > 0 else 0,
                "color": row.color or self._generate_green_color(i, len(income_data)),
                "count": row.count
            }
            for i, row in enumerate(income_data)
        ]
        
        # Procesar gastos
        expense_total = sum([float(row.total) for row in expense_data])
        expense_categories = [
            {
                "category": row.category,
                "total": round(float(row.total), 2),
                "percentage": round((float(row.total) / expense_total * 100), 2) if expense_total > 0 else 0,
                "color": row.color or self._generate_red_color(i, len(expense_data)),
                "count": row.count
            }
            for i, row in enumerate(expense_data)
        ]
        
        return {
            "income": {
                "categories": income_categories,
                "total": round(income_total, 2)
            },
            "expenses": {
                "categories": expense_categories,
                "total": round(expense_total, 2)
            },
            "period": {
                "year": year,
                "month": month
            }
        }

    async def get_yearly_monthly_trend(
        self,
        user_id: UUID,
        year: int,
        account_id: Optional[str] = None
    ) -> list:
        """
        Obtiene tendencia mensual de ingresos y gastos para todo el año.
        
        Returns:
            Lista de 12 elementos (uno por mes) con income y expenses
        """
        from datetime import date
        from uuid import UUID as UUIDType
        
        # Filtrar cuentas
        accounts_query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        )
        
        if account_id:
            account_uuid = UUIDType(account_id) if isinstance(account_id, str) else account_id
            accounts_query = accounts_query.filter(Account.id == account_uuid)
        
        accounts = accounts_query.all()
        account_ids = [acc.id for acc in accounts]
        
        if not account_ids:
            return self._empty_monthly_trend()
        
        # Query para ingresos por mes
        income_by_month = self.db.query(
            extract('month', Transaction.date).label('month'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.account_id.in_(account_ids),
            extract('year', Transaction.date) == year,
            Transaction.type == 'income'
        ).group_by(extract('month', Transaction.date)).all()
        
        # Query para gastos por mes
        expense_by_month = self.db.query(
            extract('month', Transaction.date).label('month'),
            func.sum(func.abs(Transaction.amount)).label('total')
        ).filter(
            Transaction.account_id.in_(account_ids),
            extract('year', Transaction.date) == year,
            Transaction.type == 'expense'
        ).group_by(extract('month', Transaction.date)).all()
        
        # Convertir a diccionarios
        income_dict = {int(row.month): float(row.total) for row in income_by_month}
        expense_dict = {int(row.month): float(row.total) for row in expense_by_month}
        
        # Nombres de meses en español
        month_names = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        
        # Construir array de 12 meses
        monthly_trend = []
        for month_num in range(1, 13):
            monthly_trend.append({
                "month": month_num,
                "month_name": month_names[month_num - 1],
                "income": round(income_dict.get(month_num, 0.0), 2),
                "expenses": round(expense_dict.get(month_num, 0.0), 2)
            })
        
        return monthly_trend

    def _generate_green_color(self, index: int, total: int) -> str:
        """Genera tonos de verde para categorías de ingresos"""
        greens = ["#10b981", "#34d399", "#6ee7b7", "#a7f3d0", "#d1fae5"]
        return greens[index % len(greens)]

    def _generate_red_color(self, index: int, total: int) -> str:
        """Genera tonos de rojo para categorías de gastos"""
        reds = ["#ef4444", "#f87171", "#fca5a5", "#fecaca", "#fee2e2"]
        return reds[index % len(reds)]

    def _empty_monthly_trend(self) -> list:
        """Retorna estructura vacía para tendencia mensual"""
        month_names = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        return [
            {
                "month": i,
                "month_name": month_names[i - 1],
                "income": 0.0,
                "expenses": 0.0
            }
            for i in range(1, 13)
        ]
