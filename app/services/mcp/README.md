# MCP Financial Context

## Overview

El **Model Context Protocol (MCP)** es una capa de abstracción que permite a Gemini AI acceder a datos financieros estructurados sin exponer directamente la base de datos.

## Funciones Disponibles

### 1. `get_user_financial_summary(user_id, period)`

Resumen financiero completo del periodo especificado.

**Returns**:
```python
{
    "total_income": float,
    "total_expenses": float,
    "net_balance": float,
    "savings_rate": float,
    "num_accounts": int,
    "num_transactions": int,
    "currency": str
}
```

---

### 2. `get_spending_by_category(user_id, period)`

Desglose de gastos por categoría.

**Returns**:
```python
[
    {
        "category_id": str,
        "category_name": str,
        "category_color": str,
        "total": float,
        "percentage": float,
        "num_transactions": int,
        "avg_transaction": float
    },
    ...
]
```

---

### 3. `get_income_sources(user_id, period)`

Fuentes de ingreso por categoría.

**Returns**: Similar a `get_spending_by_category` pero para ingresos.

---

### 4. `get_monthly_trend(user_id, months=6)`

Serie temporal de ingresos/gastos/balance.

**Returns**:
```python
{
    "months": ["Ene 2026", "Feb 2026", ...],
    "income": [2500, 2600, ...],
    "expenses": [1800, 1850, ...],
    "balance": [700, 750, ...]
}
```

---

### 5. `get_unusual_transactions(user_id, threshold=2.0)`

Detecta transacciones anómalas usando z-score.

**Returns**:
```python
[
    {
        "transaction_id": str,
        "date": str,
        "description": str,
        "amount": float,
        "category": str,
        "z_score": float,
        "reason": str
    },
    ...
]
```

---

### 6. `get_recurring_expenses(user_id)`

Identifica gastos recurrentes (suscripciones, facturas).

**Returns**:
```python
[
    {
        "description": str,
        "category": str,
        "avg_amount": float,
        "frequency": str,  # "semanal", "mensual", etc.
        "num_occurrences": int,
        "annual_cost": float,
        "next_expected_date": str
    },
    ...
]
```

---

### 7. `get_savings_potential(user_id)`

Identifica oportunidades de ahorro.

**Returns**:
```python
[
    {
        "category": str,
        "current_spending": float,
        "historical_avg": float,
        "potential_savings_monthly": float,
        "potential_savings_annual": float,
        "recommendation": str
    },
    ...
]
```

---

### 8. `compare_periods(user_id, period1, period2)`

Compara dos periodos financieros.

**Returns**:
```python
{
    "period1_summary": {...},
    "period2_summary": {...},
    "summary_comparison": {
        "income_change": float,
        "income_change_pct": float,
        "expenses_change": float,
        "expenses_change_pct": float,
        "balance_change": float,
        "balance_change_pct": float
    },
    "category_changes": [...]
}
```

---

## Periodos Soportados

- `current_month`: Mes actual
- `last_month`: Mes anterior
- `current_year`: Año actual
- `last_year`: Año anterior
- `last_3_months`: Últimos 3 meses
- `last_6_months`: Últimos 6 meses
- `last_12_months`: Últimos 12 meses

---

## Uso Básico

```python
from app.services.mcp.financial_context import MCPFinancialContext
from app.database import get_db

db = next(get_db())
mcp = MCPFinancialContext(db)

# Resumen del mes actual
summary = mcp.get_user_financial_summary(user_id, 'current_month')
print(f"Balance: €{summary['net_balance']}")

# Gastos por categoría
spending = mcp.get_spending_by_category(user_id, 'current_month')
for cat in spending:
    print(f"{cat['category_name']}: €{cat['total']} ({cat['percentage']:.1f}%)")
```

---

## Integración con Gemini

```python
from app.services.insights_service import InsightsService

insights_service = InsightsService(db)

# Gemini utiliza MCP internamente
insights = await insights_service.generate_financial_insights(user_id)

# Gemini invoca funciones MCP según necesidad
# Ejemplo: para generar insight sobre gastos excesivos, 
# Gemini llama a get_spending_by_category + get_savings_potential
```

---

## Seguridad

✅ **Implementado**:
- Todas las queries filtran por `user_id`
- SQL injection prevention (SQLAlchemy ORM)
- No expone estructura interna de DB
- Gemini solo recibe datos estructurados, nunca queries

⚠️ **Mejoras futuras**:
- Cache de resultados (Redis)
- Rate limiting por usuario
- Audit logs de accesos

---

## Performance

**Optimizaciones**:
- Queries con índices en `user_id`, `date`, `category_id`
- Agregaciones en DB (no en Python)
- Límites razonables (ej: max 24 meses en trends)

**Benchmarks** (promedio en DB con 1000 transacciones):
- `get_user_financial_summary`: ~50ms
- `get_spending_by_category`: ~80ms
- `get_monthly_trend(6)`: ~120ms
- `get_unusual_transactions`: ~150ms

---

## Testing

```python
# test_mcp.py
import pytest
from app.services.mcp.financial_context import MCPFinancialContext

def test_get_user_financial_summary(db, user_id):
    mcp = MCPFinancialContext(db)
    summary = mcp.get_user_financial_summary(user_id, 'current_month')
    
    assert 'total_income' in summary
    assert 'total_expenses' in summary
    assert summary['savings_rate'] >= 0
```

---

**Última actualización**: 9 Enero 2026  
**Versión**: 1.0.0
