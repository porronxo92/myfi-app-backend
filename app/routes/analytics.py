"""
Analytics Routes - Endpoints para análisis cuantitativos
=========================================================

Endpoints para obtener métricas financieras, tendencias y análisis
cuantitativos de transacciones.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.security import get_current_user
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    MonthlySummaryResponse,
    CategoryBreakdownResponse,
    TrendAnalysisResponse,
    AnomaliesResponse,
    RecurringExpensesResponse,
    SavingsPotentialResponse,
    PeriodComparisonResponse,
    AnalyticsWithChartsResponse,
    TransactionType
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=MonthlySummaryResponse)
async def get_monthly_summary(
    period: str = Query(
        "current_month",
        description="Periodo a analizar: 'current_month', 'last_month', 'current_year', etc."
    ),
    account_id: Optional[str] = Query(
        None,
        description="UUID de cuenta para filtrar (opcional). Si no se proporciona, se analizan todas las cuentas"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el resumen financiero del mes/periodo especificado.
    
    Incluye:
    - Total de ingresos y gastos
    - Balance neto
    - Tasa de ahorro
    - Número de transacciones y cuentas
    
    **Periodos válidos:**
    - `current_month`: Mes actual
    - `last_month`: Mes anterior
    - `current_year`: Año actual
    - `last_year`: Año anterior
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        summary = await analytics.calculate_monthly_summary(user_id, period, account_id)
        return summary
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Periodo inválido: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular resumen: {str(e)}")


@router.get("/categories", response_model=CategoryBreakdownResponse)
async def get_category_breakdown(
    transaction_type: TransactionType = Query(
        TransactionType.EXPENSE,
        description="Tipo de transacción: 'expense' o 'income'"
    ),
    period: str = Query(
        "current_month",
        description="Periodo a analizar"
    ),
    account_id: Optional[str] = Query(
        None,
        description="UUID de cuenta para filtrar (opcional)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el desglose de gastos o ingresos por categoría.
    
    Incluye para cada categoría:
    - Nombre y color
    - Total gastado/ingresado
    - Porcentaje del total
    - Número de transacciones
    - Promedio por transacción
    
    **Casos de uso:**
    - Identificar en qué categorías se gasta más
    - Analizar fuentes de ingreso
    - Crear gráficos de pie charts
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        breakdown = await analytics.get_category_breakdown(
            user_id, 
            transaction_type.value, 
            period,
            account_id
        )
        return breakdown
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener categorías: {str(e)}")


@router.get("/categories/chart", response_model=AnalyticsWithChartsResponse)
async def get_category_chart_data(
    transaction_type: TransactionType = Query(
        TransactionType.EXPENSE,
        description="Tipo de transacción: 'expense' o 'income'"
    ),
    period: str = Query(
        "current_month",
        description="Periodo a analizar"
    ),
    account_id: Optional[str] = Query(
        None,
        description="ID de cuenta para filtrar (opcional)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene datos formateados para Chart.js (pie chart de categorías).
    
    Retorna el desglose de categorías + estructura lista para Chart.js:
    ```json
    {
      "analytics_data": {...},
      "chart_data": {
        "labels": ["Alimentación", "Transporte", ...],
        "datasets": [{
          "data": [500, 300, ...],
          "backgroundColor": ["#FF6384", "#36A2EB", ...]
        }]
      }
    }
    ```
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        chart_data = await analytics.get_category_pie_chart_data(
            user_id,
            transaction_type.value,
            period
        )
        return chart_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar gráfico: {str(e)}")


@router.get("/trends", response_model=TrendAnalysisResponse)
async def get_spending_trends(
    months: int = Query(
        6,
        ge=3,
        le=24,
        description="Número de meses a analizar (3-24)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene tendencias de ingresos/gastos/balance de los últimos N meses.
    
    Incluye:
    - Serie temporal mensual (ingresos, gastos, balance)
    - Promedios generales
    - Dirección de la tendencia (improving/declining/stable)
    
    **Útil para:**
    - Detectar patrones de gasto a lo largo del tiempo
    - Visualizar evolución de ahorros
    - Crear line charts
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        trends = await analytics.get_spending_trends(user_id, months)
        return trends
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular tendencias: {str(e)}")


@router.get("/trends/chart", response_model=AnalyticsWithChartsResponse)
async def get_trends_chart_data(
    months: int = Query(6, ge=3, le=24),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene datos de tendencias formateados para Chart.js (line chart).
    
    Retorna estructura optimizada para gráficos de líneas:
    ```json
    {
      "analytics_data": {...},
      "chart_data": {
        "labels": ["Ene 2026", "Feb 2026", ...],
        "datasets": [
          {"label": "Ingresos", "data": [3000, 3200, ...], "borderColor": "#4CAF50"},
          {"label": "Gastos", "data": [2500, 2800, ...], "borderColor": "#F44336"},
          {"label": "Balance", "data": [500, 400, ...], "borderColor": "#2196F3"}
        ]
      }
    }
    ```
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        chart_data = await analytics.get_trend_line_chart_data(user_id, months)
        return chart_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar gráfico de tendencias: {str(e)}")


@router.get("/anomalies", response_model=AnomaliesResponse)
async def detect_anomalies(
    threshold: float = Query(
        2.0,
        ge=1.5,
        le=3.0,
        description="Umbral de desviación estándar (1.5-3.0)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detecta transacciones inusuales usando análisis estadístico (z-score).
    
    Identifica transacciones que se desvían significativamente del patrón normal:
    - Gastos excepcionalmente altos
    - Ingresos inesperados
    - Compras fuera de lo común
    
    **Threshold (umbral):**
    - 1.5: Muy sensible (detecta más anomalías)
    - 2.0: Balanced (recomendado)
    - 3.0: Conservador (solo anomalías extremas)
    
    Cada anomalía incluye:
    - Detalles de la transacción
    - Z-score (nivel de desviación)
    - Razón de por qué es inusual
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        anomalies = await analytics.detect_anomalies(user_id, threshold)
        return anomalies
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al detectar anomalías: {str(e)}")


@router.get("/recurring", response_model=RecurringExpensesResponse)
async def get_recurring_expenses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Identifica gastos recurrentes (suscripciones, facturas, etc.).
    
    Detecta patrones basándose en:
    - Descripción similar
    - Monto similar (±5% variación)
    - Frecuencia regular (semanal/quincenal/mensual)
    
    Para cada gasto recurrente muestra:
    - Descripción y categoría
    - Monto promedio
    - Frecuencia de cobro
    - Costo anual estimado
    - Próxima fecha esperada
    
    **Útil para:**
    - Identificar suscripciones olvidadas
    - Planificar presupuesto mensual
    - Optimizar gastos fijos
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        recurring = await analytics.get_recurring_expenses(user_id)
        return recurring
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al identificar gastos recurrentes: {str(e)}")


@router.get("/savings-potential", response_model=SavingsPotentialResponse)
async def get_savings_potential(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analiza oportunidades de ahorro comparando gastos actuales vs histórico.
    
    Identifica categorías donde el gasto actual excede el promedio histórico
    y sugiere reducciones realistas.
    
    Para cada oportunidad muestra:
    - Categoría con exceso de gasto
    - Gasto actual vs promedio histórico
    - Ahorro potencial mensual y anual
    - Recomendación específica
    
    **Metodología:**
    - Compara mes actual vs promedio últimos 6 meses
    - Solo considera excesos > 20% (significativos)
    - Prioriza por mayor potencial de ahorro
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        potential = await analytics.get_savings_potential(user_id)
        return potential
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular potencial de ahorro: {str(e)}")


@router.get("/compare", response_model=PeriodComparisonResponse)
async def compare_periods(
    period1: str = Query(
        "current_month",
        description="Primer periodo a comparar"
    ),
    period2: str = Query(
        "last_month",
        description="Segundo periodo a comparar"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compara dos periodos financieros lado a lado.
    
    Muestra para cada periodo:
    - Resumen financiero completo
    - Cambios absolutos y porcentuales
    - Diferencias en categorías de gasto
    - Nuevas categorías o categorías eliminadas
    
    **Comparaciones útiles:**
    - `current_month` vs `last_month`: Evolución mensual
    - `current_year` vs `last_year`: Progreso anual
    - Mes específico vs promedio: Identificar meses atípicos
    
    **Insights incluidos:**
    - Áreas de mejora (gastos reducidos)
    - Áreas de preocupación (gastos incrementados)
    - Balance general de la comparación
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        comparison = await analytics.compare_periods(user_id, period1, period2)
        return comparison
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al comparar periodos: {str(e)}")


@router.get("/top-merchants", response_model=AnalyticsWithChartsResponse)
async def get_top_merchants(
    period: str = Query("current_month"),
    limit: int = Query(10, ge=5, le=20, description="Número de merchants a retornar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene los comercios/destinatarios donde más se ha gastado.
    
    Agrupa transacciones por descripción (merchant) y retorna:
    - Top N comercios por total gastado
    - Datos formateados para bar chart
    
    **Útil para:**
    - Identificar principales destinatarios de gastos
    - Detectar patrones de compra
    - Visualizar distribución de gastos por merchant
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        chart_data = await analytics.get_top_merchants_bar_chart_data(
            user_id,
            limit,
            period
        )
        return chart_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener top merchants: {str(e)}")


@router.get("/savings-rate")
async def get_savings_rate(
    period: str = Query("current_month"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calcula la tasa de ahorro del periodo especificado.
    
    Fórmula: (Ingresos - Gastos) / Ingresos * 100
    
    **Interpretación:**
    - > 20%: Excelente
    - 10-20%: Bueno
    - 5-10%: Aceptable
    - < 5%: Necesita mejora
    - Negativo: Déficit
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        rate_data = await analytics.calculate_savings_rate(user_id, period)
        rate = rate_data['savings_rate']
        
        # Interpretación
        if rate > 20:
            interpretation = "Excelente"
        elif rate > 10:
            interpretation = "Bueno"
        elif rate > 5:
            interpretation = "Aceptable"
        elif rate >= 0:
            interpretation = "Necesita mejora"
        else:
            interpretation = "Déficit"
        
        return {
            **rate_data,
            "assessment": interpretation
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular tasa de ahorro: {str(e)}")


# ============================================
# NUEVOS ENDPOINTS PARA FILTROS ANUALES
# ============================================

@router.get("/available-years")
async def get_available_years(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Devuelve los años en los que el usuario tiene transacciones.
    
    Returns:
        {
            "years": [2026, 2025, 2024],
            "current_year": 2026
        }
    """
    try:
        from datetime import datetime
        from sqlalchemy import extract, distinct
        from app.models.transaction import Transaction
        from app.models.account import Account
        
        user_id = current_user.id
        
        # Obtener años con transacciones
        years_query = db.query(distinct(extract('year', Transaction.date))).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id
        ).order_by(
            extract('year', Transaction.date).desc()
        ).all()
        
        years = [int(year[0]) for year in years_query]
        current_year = datetime.now().year
        
        # Asegurar que el año actual esté incluido aunque no tenga transacciones
        if current_year not in years:
            years.insert(0, current_year)
        
        return {
            "years": years,
            "current_year": current_year
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener años disponibles: {str(e)}")


@router.get("/annual-balance")
async def get_annual_balance(
    year: int = Query(..., description="Año a consultar"),
    account_id: Optional[str] = Query(None, description="UUID de cuenta específica"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Devuelve el balance inicial (1 enero) y balance actual del año.
    Si account_id es None, agrupa todas las cuentas.
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        balance_data = await analytics.get_annual_balance(user_id, year, account_id)
        return balance_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular balance anual: {str(e)}")


@router.get("/annual-savings-rate")
async def get_annual_savings_rate(
    year: int = Query(..., description="Año a consultar"),
    account_id: Optional[str] = Query(None, description="UUID de cuenta específica"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calcula la tasa de ahorro anual.
    savings_amount = current_balance - initial_balance
    savings_percentage = (savings_amount / initial_balance) * 100
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        savings_data = await analytics.get_annual_savings_rate(user_id, year, account_id)
        return savings_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular tasa de ahorro anual: {str(e)}")


@router.get("/annual-income")
async def get_annual_income(
    year: int = Query(..., description="Año a consultar"),
    account_id: Optional[str] = Query(None, description="UUID de cuenta específica"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Suma total de ingresos del año hasta la fecha.
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        income_data = await analytics.get_annual_income(user_id, year, account_id)
        return income_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular ingresos anuales: {str(e)}")


@router.get("/annual-expenses")
async def get_annual_expenses(
    year: int = Query(..., description="Año a consultar"),
    account_id: Optional[str] = Query(None, description="UUID de cuenta específica"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Suma total de gastos del año hasta la fecha.
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        expenses_data = await analytics.get_annual_expenses(user_id, year, account_id)
        return expenses_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular gastos anuales: {str(e)}")


@router.get("/category-breakdown")
async def get_category_breakdown_by_month(
    year: int = Query(..., description="Año a consultar"),
    month: int = Query(..., description="Mes a consultar (1-12)"),
    account_id: Optional[str] = Query(None, description="UUID de cuenta específica"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el desglose de ingresos y gastos por categoría para un año y mes específicos.
    
    Retorna dos conjuntos de datos:
    - **income**: Categorías de ingresos con totales y porcentajes
    - **expenses**: Categorías de gastos con totales y porcentajes
    
    Ideal para crear Doughnut Charts separados de ingresos y gastos.
    
    Response:
    ```json
    {
      "income": {
        "categories": [
          {"category": "Salario", "total": 2500.00, "percentage": 78.5, "color": "#10b981"},
          {"category": "Freelance", "total": 680.00, "percentage": 21.5, "color": "#34d399"}
        ],
        "total": 3180.00
      },
      "expenses": {
        "categories": [
          {"category": "Alimentación", "total": 450.00, "percentage": 35.2, "color": "#ef4444"},
          {"category": "Transporte", "total": 280.00, "percentage": 21.9, "color": "#f87171"}
        ],
        "total": 1280.00
      },
      "period": {"year": 2025, "month": 1}
    }
    ```
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        breakdown_data = await analytics.get_monthly_category_breakdown(
            user_id, year, month, account_id
        )
        return breakdown_data
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al obtener desglose por categoría: {str(e)}"
        )


@router.get("/monthly-trend")
async def get_monthly_trend_by_year(
    year: int = Query(..., description="Año a consultar"),
    account_id: Optional[str] = Query(None, description="UUID de cuenta específica"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene la tendencia mensual de ingresos y gastos para un año completo.
    
    Retorna un array de 12 elementos (uno por cada mes) con:
    - **month**: Número del mes (1-12)
    - **month_name**: Nombre del mes en español
    - **income**: Total de ingresos del mes
    - **expenses**: Total de gastos del mes
    
    Ideal para crear Line Charts con evolución mensual.
    
    Response:
    ```json
    [
      {"month": 1, "month_name": "Enero", "income": 2500.00, "expenses": 1280.00},
      {"month": 2, "month_name": "Febrero", "income": 2500.00, "expenses": 1350.00},
      ...
    ]
    ```
    """
    try:
        user_id = current_user.id
        analytics = AnalyticsService(db)
        
        trend_data = await analytics.get_yearly_monthly_trend(
            user_id, year, account_id
        )
        return trend_data
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al obtener tendencia mensual: {str(e)}"
        )
