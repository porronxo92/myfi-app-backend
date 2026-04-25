# Sistema de Analytics e Insights con IA

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Componentes Principales](#componentes-principales)
4. [Model Context Protocol (MCP)](#model-context-protocol-mcp)
5. [Endpoints de API](#endpoints-de-api)
6. [Configuración](#configuración)
7. [Integración Frontend](#integración-frontend)
8. [Ejemplos de Uso](#ejemplos-de-uso)
9. [Troubleshooting](#troubleshooting)
10. [Roadmap](#roadmap)

---

## 🎯 Visión General

El **Sistema de Analytics e Insights** es una capa de inteligencia financiera que transforma datos transaccionales en información accionable mediante análisis cuantitativos y recomendaciones generadas con IA.

### Objetivos Clave

- **📊 Analytics Cuantitativos**: Métricas financieras precisas y tendencias
- **💡 Insights con IA**: Recomendaciones personalizadas usando Gemini AI
- **🎯 Accionabilidad**: Información práctica que guía decisiones financieras
- **📈 Visualización**: Datos optimizados para Chart.js (pie, line, bar charts)

### Propuesta de Valor

```
Datos Transaccionales → MCP Layer → Analytics/Insights Services → API → Dashboard
```

**Antes**: Usuario ve listado de transacciones  
**Después**: Usuario recibe insights como "Gastas 40% más en 'Ocio' este mes. Cancelando Netflix ahorras €144/año"

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Angular)                       │
│  Dashboard Component │ Chart.js │ Insight Cards │ Services     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/JSON
┌───────────────────────────▼─────────────────────────────────────┐
│                       API ROUTES (FastAPI)                      │
│  /api/analytics/*  │  /api/insights/*                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼──────────┐                   ┌────────▼─────────┐
│ Analytics Service│                   │ Insights Service │
│ (Quantitative)   │                   │ (Qualitative/AI) │
└───────┬──────────┘                   └────────┬─────────┘
        │                                       │
        │           ┌───────────────────────────┤
        └───────────►   MCP Financial Context   │◄─── Gemini AI
                    │  (Database Abstraction)   │
                    └───────────┬───────────────┘
                                │
                    ┌───────────▼───────────────┐
                    │   PostgreSQL Database     │
                    │ Transactions │ Categories │
                    └───────────────────────────┘
```

### Capas del Sistema

1. **MCP Layer**: Abstracción que expone funciones estructuradas a Gemini
2. **Analytics Service**: Cálculos cuantitativos (sumas, promedios, tendencias)
3. **Insights Service**: Análisis cualitativos con Gemini AI
4. **API Routes**: Endpoints REST para frontend
5. **Frontend**: Componentes Angular + Chart.js

---

## 🧩 Componentes Principales

### 1. MCP Financial Context (`app/services/mcp/financial_context.py`)

**Propósito**: Puente entre Gemini AI y la base de datos PostgreSQL.

**Funciones Disponibles** (8 core functions):

| Función | Descripción | Retorno |
|---------|-------------|---------|
| `get_user_financial_summary` | Resumen financiero del periodo | Ingresos, gastos, balance, tasa ahorro |
| `get_spending_by_category` | Desglose de gastos por categoría | Categoría, total, %, avg, num_transactions |
| `get_income_sources` | Fuentes de ingreso por categoría | Similar a spending pero para ingresos |
| `get_monthly_trend` | Serie temporal de N meses | Arrays de ingresos/gastos/balance por mes |
| `get_unusual_transactions` | Detección de anomalías (z-score) | Transacciones con desviación > threshold |
| `get_recurring_expenses` | Identifica suscripciones/gastos fijos | Descripción, monto, frecuencia, costo anual |
| `get_savings_potential` | Oportunidades de ahorro vs histórico | Categorías con exceso de gasto >20% |
| `compare_periods` | Comparación entre dos periodos | Deltas absolutos y porcentuales |

**Ejemplo de Uso**:

```python
from app.services.mcp.financial_context import MCPFinancialContext

mcp = MCPFinancialContext(db)
summary = mcp.get_user_financial_summary(user_id, 'current_month')

# Resultado:
{
    "total_income": 2500.00,
    "total_expenses": 1800.00,
    "net_balance": 700.00,
    "savings_rate": 28.0,
    "num_accounts": 3,
    "num_transactions": 45,
    "currency": "EUR"
}
```

**Periodos Soportados**:
- `current_month`, `last_month`, `current_year`, `last_year`
- `last_3_months`, `last_6_months`, `last_12_months`

---

### 2. Analytics Service (`app/services/analytics_service.py`)

**Propósito**: Análisis cuantitativos y formateo para Chart.js.

**Métodos Principales**:

```python
class AnalyticsService:
    async def calculate_monthly_summary(user_id, period) → MonthlySummaryResponse
    async def get_category_breakdown(user_id, type, period) → CategoryBreakdownResponse
    async def get_spending_trends(user_id, months) → TrendAnalysisResponse
    async def detect_anomalies(user_id, threshold) → AnomaliesResponse
    async def get_recurring_expenses(user_id) → RecurringExpensesResponse
    async def get_savings_potential(user_id) → SavingsPotentialResponse
    async def compare_periods(user_id, period1, period2) → PeriodComparisonResponse
    
    # Chart.js formatters
    async def get_category_pie_chart_data(...) → AnalyticsWithChartsResponse
    async def get_trend_line_chart_data(...) → AnalyticsWithChartsResponse
    async def get_top_merchants_bar_chart_data(...) → AnalyticsWithChartsResponse
```

**Características**:
- ✅ Todos los métodos son async (FastAPI compatible)
- ✅ Retorna Pydantic models (type-safe)
- ✅ Formateo Chart.js integrado
- ✅ Detección de anomalías con z-score
- ✅ Identificación de gastos recurrentes

---

### 3. Insights Service (`app/services/insights_service.py`)

**Propósito**: Generación de insights cualitativos con Gemini AI.

**Métodos Principales**:

```python
class InsightsService:
    async def generate_financial_insights(user_id, num_insights) → List[FinancialInsight]
    async def analyze_financial_health(user_id) → FinancialHealthResponse
    async def get_spending_recommendations(user_id) → RecommendationsResponse
    async def predict_monthly_outlook(user_id) → MonthlyOutlookResponse
    async def generate_savings_plan(user_id, target, months) → SavingsPlanResponse
    async def custom_analysis(user_id, question, context) → CustomAnalysisResponse
    async def get_combined_dashboard_data(user_id) → CombinedAnalyticsInsightsResponse
```

**Score de Salud Financiera**:

```python
overall_score = (
    savings_score * 0.4 +        # Tasa de ahorro (40%)
    spending_control_score * 0.3 +  # Control de gastos (30%)
    income_stability_score * 0.3    # Estabilidad ingresos (30%)
)

# Grados:
# A (90-100): Excelente
# B (75-89):  Bueno
# C (60-74):  Aceptable
# D (45-59):  Necesita mejora
# F (<45):    Crítico
```

**Fallback Mode**: Si Gemini no está disponible, retorna insights básicos calculados sin IA.

---

## 🔌 Model Context Protocol (MCP)

### ¿Qué es MCP?

El **Model Context Protocol** es una abstracción que permite a Gemini AI invocar funciones estructuradas sin acceso directo a la base de datos.

### Beneficios

✅ **Seguridad**: Gemini nunca ve queries SQL ni estructura de DB  
✅ **Abstracción**: Cambios en DB no afectan a Gemini  
✅ **Trazabilidad**: Todas las llamadas pasan por funciones auditables  
✅ **Type-Safe**: Inputs/outputs bien definidos

### Flujo de Invocación

```python
# 1. Gemini recibe contexto de herramientas disponibles
context = mcp.get_context_definition()

# 2. Gemini decide qué función invocar según prompt
# Internamente llama:
summary = mcp.get_user_financial_summary(user_id, 'current_month')

# 3. MCP ejecuta query SQLAlchemy
results = db.query(Transaction).filter(...).all()

# 4. MCP retorna dict estructurado
return {
    "total_income": sum(income_transactions),
    "total_expenses": sum(expense_transactions),
    ...
}

# 5. Gemini usa el resultado para generar insight en lenguaje natural
```

### Detección de Anomalías (Z-Score)

```python
# Metodología
mean = avg(transactions)
stdev = stddev(transactions)
z_score = (transaction_amount - mean) / stdev

# Si z_score > threshold (default 2.0):
# → Transacción es inusual (>2 desviaciones estándar)

# Ejemplo:
# Gasto promedio: €50 ± €15
# Transacción de €95:
# z_score = (95 - 50) / 15 = 3.0 → ANOMALÍA
```

### Detección de Gastos Recurrentes

```python
# Criterios:
1. Descripción similar (Levenshtein distance)
2. Monto similar (±5% variación)
3. Frecuencia regular:
   - Semanal: 7 ± 1 días
   - Quincenal: 15 ± 2 días
   - Mensual: 30 ± 3 días

# Ejemplo:
# "Netflix Premium" €15.99 cada ~30 días
# → Detectado como gasto recurrente mensual
```

---

## 📡 Endpoints de API

### Analytics Endpoints

#### `GET /api/analytics/summary`

Resumen financiero del periodo.

**Query Params**:
- `period`: `current_month`, `last_month`, etc.

**Response**:
```json
{
  "user_id": "uuid",
  "period": "current_month",
  "total_income": 2500.00,
  "total_expenses": 1800.00,
  "net_balance": 700.00,
  "savings_rate": 28.0,
  "num_accounts": 3,
  "num_transactions": 45,
  "currency": "EUR"
}
```

---

#### `GET /api/analytics/categories`

Desglose por categorías (gastos o ingresos).

**Query Params**:
- `transaction_type`: `expense` | `income`
- `period`: Periodo a analizar

**Response**:
```json
{
  "user_id": "uuid",
  "period": "current_month",
  "transaction_type": "expense",
  "total_amount": 1800.00,
  "categories": [
    {
      "category_id": "uuid",
      "category_name": "Alimentación",
      "category_color": "#FF6384",
      "total": 600.00,
      "percentage": 33.3,
      "num_transactions": 15,
      "avg_transaction": 40.00
    },
    ...
  ]
}
```

---

#### `GET /api/analytics/categories/chart`

Datos formateados para Chart.js (pie chart).

**Response**:
```json
{
  "analytics_data": { ... },
  "chart_data": {
    "labels": ["Alimentación", "Transporte", "Ocio"],
    "datasets": [{
      "data": [600, 400, 300],
      "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56"],
      "borderColor": ["#fff", "#fff", "#fff"],
      "borderWidth": 2
    }]
  }
}
```

**Uso en Frontend (Angular)**:
```typescript
this.analyticsService.getCategoryChartData('expense', 'current_month')
  .subscribe(response => {
    this.pieChart = new Chart(ctx, {
      type: 'pie',
      data: response.chart_data
    });
  });
```

---

#### `GET /api/analytics/trends`

Tendencias de N meses.

**Query Params**:
- `months`: 3-24 (default: 6)

**Response**:
```json
{
  "user_id": "uuid",
  "months_analyzed": 6,
  "data_points": [
    {
      "month": "Ene 2026",
      "income": 2500,
      "expenses": 1800,
      "balance": 700,
      "savings_rate": 28.0
    },
    ...
  ],
  "averages": {
    "avg_income": 2600,
    "avg_expenses": 1850,
    "avg_balance": 750
  },
  "trend_direction": "improving"
}
```

---

#### `GET /api/analytics/trends/chart`

Datos para Chart.js (line chart).

**Response**:
```json
{
  "analytics_data": { ... },
  "chart_data": {
    "labels": ["Ene 2026", "Feb 2026", "Mar 2026", ...],
    "datasets": [
      {
        "label": "Ingresos",
        "data": [2500, 2600, 2550, ...],
        "borderColor": "#4CAF50",
        "fill": false
      },
      {
        "label": "Gastos",
        "data": [1800, 1850, 1750, ...],
        "borderColor": "#F44336",
        "fill": false
      },
      {
        "label": "Balance",
        "data": [700, 750, 800, ...],
        "borderColor": "#2196F3",
        "fill": false
      }
    ]
  }
}
```

---

#### `GET /api/analytics/anomalies`

Detecta transacciones inusuales.

**Query Params**:
- `threshold`: 1.5-3.0 (default: 2.0) - Desviaciones estándar

**Response**:
```json
{
  "user_id": "uuid",
  "threshold": 2.0,
  "num_anomalies": 3,
  "unusual_transactions": [
    {
      "transaction_id": "uuid",
      "date": "2026-01-05",
      "description": "Compra excepcional",
      "amount": 950.00,
      "category": "Electrónica",
      "z_score": 3.2,
      "reason": "Monto es 3.2 desviaciones estándar por encima del promedio (€950 vs €45 promedio)"
    },
    ...
  ]
}
```

---

#### `GET /api/analytics/recurring`

Identifica gastos recurrentes.

**Response**:
```json
{
  "user_id": "uuid",
  "num_recurring": 5,
  "recurring_expenses": [
    {
      "description": "Netflix Premium",
      "category": "Ocio/Deporte",
      "avg_amount": 15.99,
      "frequency": "mensual",
      "num_occurrences": 6,
      "annual_cost": 191.88,
      "next_expected_date": "2026-02-08"
    },
    ...
  ],
  "total_annual_cost": 1200.00
}
```

---

#### `GET /api/analytics/savings-potential`

Oportunidades de ahorro.

**Response**:
```json
{
  "user_id": "uuid",
  "total_potential_savings_monthly": 350.00,
  "total_potential_savings_annual": 4200.00,
  "opportunities": [
    {
      "category": "Ocio/Deporte",
      "current_spending": 800.00,
      "historical_avg": 600.00,
      "potential_savings_monthly": 200.00,
      "potential_savings_annual": 2400.00,
      "recommendation": "Tu gasto en 'Ocio/Deporte' es 33% superior al promedio. Considera reducir compras impulsivas."
    },
    ...
  ]
}
```

---

#### `GET /api/analytics/compare`

Compara dos periodos.

**Query Params**:
- `period1`: Primer periodo
- `period2`: Segundo periodo

**Response**:
```json
{
  "period1": {
    "period": "current_month",
    "total_income": 2500,
    "total_expenses": 1800,
    ...
  },
  "period2": {
    "period": "last_month",
    "total_income": 2400,
    "total_expenses": 1900,
    ...
  },
  "comparison": {
    "income_change": 100.00,
    "income_change_pct": 4.17,
    "expenses_change": -100.00,
    "expenses_change_pct": -5.26,
    "balance_improvement": true
  },
  "insights": [
    "Ingresos aumentaron 4.2%",
    "Gastos reducidos en 5.3% ✅",
    "Balance mejorado en €200"
  ]
}
```

---

### Insights Endpoints

#### `GET /api/insights/generate`

Genera insights con Gemini AI.

**Query Params**:
- `num_insights`: 1-10 (default: 5)

**Response**:
```json
[
  {
    "id": "insight-1",
    "type": "alert",
    "priority": "high",
    "icon": "⚠️",
    "title": "Gasto elevado en Ocio",
    "message": "Gastaste €800 en 'Ocio/Deporte' este mes, 60% más que tu promedio (€500). Considera revisar suscripciones.",
    "data_point": {
      "category": "Ocio/Deporte",
      "current": 800,
      "avg": 500
    },
    "action": {
      "label": "Ver transacciones",
      "route": "/transactions?category=Ocio/Deporte",
      "action_type": "navigate"
    },
    "generated_at": "2026-01-09T10:30:00Z"
  },
  {
    "type": "positive",
    "priority": "medium",
    "icon": "✅",
    "title": "Ahorro en Transporte",
    "message": "Reduciste tus gastos en 'Transporte' un 25% este mes. ¡Excelente!",
    ...
  },
  ...
]
```

**Tipos de Insights**:
- `alert` ⚠️: Requiere atención
- `positive` ✅: Reconocimiento
- `recommendation` 💡: Sugerencia
- `neutral` ℹ️: Información
- `prediction` 🔮: Proyección

---

#### `GET /api/insights/financial-health`

Analiza salud financiera.

**Response**:
```json
{
  "user_id": "uuid",
  "analyzed_at": "2026-01-09T10:30:00Z",
  "health_score": {
    "overall_score": 82,
    "category_scores": {
      "savings_rate": 70,
      "spending_control": 85,
      "income_stability": 90
    },
    "grade": "B",
    "summary": "Tu salud financiera está en nivel B. ¡Excelente trabajo!"
  },
  "insights": [ ... ],
  "strengths": [
    "Excelente tasa de ahorro (28%)",
    "Ingresos estables y predecibles"
  ],
  "areas_of_improvement": [
    "Mejorar el control de gastos discrecionales"
  ]
}
```

---

#### `GET /api/insights/recommendations`

Recomendaciones de optimización.

**Response**:
```json
{
  "user_id": "uuid",
  "generated_at": "2026-01-09T10:30:00Z",
  "total_potential_savings": 350.00,
  "recommendations": [
    {
      "category": "Ocio/Deporte",
      "current_spending": 800.00,
      "recommended_spending": 600.00,
      "potential_savings": 200.00,
      "reasoning": "Gasto actual excede promedio histórico en 33%. Identifica suscripciones no utilizadas.",
      "difficulty": "easy"
    },
    ...
  ],
  "quick_wins": [
    "Cancelar Spotify Premium ahorra €10/mes",
    "Cambiar plan de gimnasio ahorra €25/mes"
  ],
  "long_term_strategies": [
    "Establecer presupuestos mensuales por categoría",
    "Automatizar transferencias a ahorro el día de cobro"
  ]
}
```

**Dificultades**:
- `easy`: Acciones inmediatas (cancelar suscripción)
- `moderate`: Cambio de hábitos (reducir salidas)
- `hard`: Cambios estructurales (mudanza, coche)

---

#### `GET /api/insights/monthly-outlook`

Predicción de cierre de mes.

**Response**:
```json
{
  "user_id": "uuid",
  "current_month": "2026-01",
  "days_remaining": 12,
  "current_status": {
    "income_so_far": 2500.00,
    "expenses_so_far": 1200.00,
    "balance_so_far": 1300.00
  },
  "prediction": {
    "predicted_income": 2500.00,
    "predicted_expenses": 1835.00,
    "predicted_balance": 665.00,
    "confidence": "medium",
    "assumptions": [
      "Ingresos similares al promedio de últimos 3 meses",
      "Ritmo de gasto actual (€52.90/día) se mantiene"
    ]
  },
  "alerts": [
    "Gastos en 'Ocio' representan el 35% del total"
  ],
  "advice": "El margen es ajustado. Evita gastos innecesarios en lo que queda de mes."
}
```

---

#### `POST /api/insights/savings-plan`

Genera plan de ahorro personalizado.

**Query Params**:
- `target_amount`: Monto objetivo (€)
- `months`: Plazo en meses (1-60)

**Response**:
```json
{
  "user_id": "uuid",
  "goal": {
    "target_amount": 5000.00,
    "current_savings": 1200.00,
    "months_to_achieve": 12,
    "monthly_savings_needed": 316.67
  },
  "plan_steps": [
    {
      "step_number": 1,
      "action": "Cancelar Netflix y Disney+",
      "expected_savings": 25.00,
      "timeframe": "immediate"
    },
    {
      "step_number": 2,
      "action": "Reducir gastos en Ocio a €600/mes",
      "expected_savings": 200.00,
      "timeframe": "short-term"
    },
    ...
  ],
  "feasibility": "feasible",
  "alternative_suggestions": [],
  "motivational_message": "Con disciplina y estos cambios, alcanzarás €5,000 en 12 meses. ¡Tú puedes! 💪"
}
```

**Factibilidad**:
- `very_feasible`: Ajustes menores
- `feasible`: Requiere disciplina
- `challenging`: Cambios significativos
- `unrealistic`: Objetivo muy ambicioso

---

#### `POST /api/insights/custom-analysis`

Análisis personalizado vía chat.

**Request Body**:
```json
{
  "question": "¿En qué categoría puedo reducir más gastos?",
  "context": {
    "focus_period": "current_month",
    "target_savings": 200
  }
}
```

**Response**:
```json
{
  "user_id": "uuid",
  "question": "¿En qué categoría puedo reducir más gastos?",
  "answer": "Tu mayor oportunidad de ahorro está en 'Ocio/Deporte' (€800 este mes vs €500 promedio). Reducirla a €600 te ahorraría €200/mes, exactamente tu objetivo. Empieza cancelando suscripciones no utilizadas.",
  "supporting_data": {
    "category": "Ocio/Deporte",
    "current": 800,
    "average": 500,
    "potential_savings": 200
  },
  "related_insights": [],
  "follow_up_questions": [
    "¿Cómo puedo identificar suscripciones innecesarias?",
    "¿Cuánto ahorro si cancelo Netflix?"
  ]
}
```

---

#### `GET /api/insights/dashboard`

**Endpoint optimizado** para dashboard (1 request = todo).

**Response**:
```json
{
  "analytics": {
    "summary": { ... },
    "categories": { ... },
    "trends": { ... }
  },
  "insights": [
    { ... insight 1 ... },
    { ... insight 2 ... },
    ...
  ],
  "health_score": {
    "overall_score": 82,
    "grade": "B",
    ...
  },
  "quick_stats": {
    "balance_vs_last_month": "+12.5%",
    "savings_rate": 28.0,
    "top_category": "Alimentación",
    "num_transactions": 45
  }
}
```

---

## ⚙️ Configuración

### 1. Variables de Entorno

Crear `.env` en `backend/`:

```bash
# Gemini AI
GEMINI_API_KEY=AIzaSy...  # Obtener en https://aistudio.google.com/app/apikey

# Database
DATABASE_URL_LOCALHOST=postgresql://user:pass@localhost:5432/app_finance
DATABASE_URL_PROD=postgresql://user:pass@prod-host:5432/app_finance

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development  # or production
```

### 2. Instalación de Dependencias

```bash
cd backend
pip install -r requirements.txt
```

**Paquetes clave**:
- `google-generativeai==0.8.3` - Gemini AI
- `fastapi==0.115.5`
- `pydantic==2.10.3`
- `sqlalchemy==2.0.36`

### 3. Verificar Configuración

```python
from app.config import settings

print(settings.GEMINI_API_KEY)  # Debe mostrar la key
print(settings.LLM_PROVIDER)    # "gemini"
print(settings.LLM_MODEL)       # "gemini-2.0-flash"
```

### 4. Iniciar Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acceder a:
- API Docs: http://localhost:8000/docs
- Endpoints: http://localhost:8000/api/analytics/*

---

## 🖥️ Integración Frontend

### Servicios Angular

#### 1. Analytics Service

```typescript
// src/app/core/services/analytics.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private baseUrl = 'http://localhost:8000/api/analytics';

  constructor(private http: HttpClient) {}

  getMonthlySummary(period: string = 'current_month'): Observable<any> {
    return this.http.get(`${this.baseUrl}/summary`, { 
      params: { period } 
    });
  }

  getCategoryBreakdown(type: 'expense' | 'income', period: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/categories`, {
      params: { transaction_type: type, period }
    });
  }

  getCategoryChartData(type: 'expense' | 'income', period: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/categories/chart`, {
      params: { transaction_type: type, period }
    });
  }

  getTrends(months: number = 6): Observable<any> {
    return this.http.get(`${this.baseUrl}/trends`, {
      params: { months: months.toString() }
    });
  }

  getTrendsChartData(months: number = 6): Observable<any> {
    return this.http.get(`${this.baseUrl}/trends/chart`, {
      params: { months: months.toString() }
    });
  }

  getAnomalies(threshold: number = 2.0): Observable<any> {
    return this.http.get(`${this.baseUrl}/anomalies`, {
      params: { threshold: threshold.toString() }
    });
  }

  getRecurringExpenses(): Observable<any> {
    return this.http.get(`${this.baseUrl}/recurring`);
  }

  getSavingsPotential(): Observable<any> {
    return this.http.get(`${this.baseUrl}/savings-potential`);
  }

  comparePeriods(period1: string, period2: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/compare`, {
      params: { period1, period2 }
    });
  }
}
```

---

#### 2. Insights Service

```typescript
// src/app/core/services/insights.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class InsightsService {
  private baseUrl = 'http://localhost:8000/api/insights';

  constructor(private http: HttpClient) {}

  generateInsights(numInsights: number = 5): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/generate`, {
      params: { num_insights: numInsights.toString() }
    });
  }

  getFinancialHealth(): Observable<any> {
    return this.http.get(`${this.baseUrl}/financial-health`);
  }

  getRecommendations(): Observable<any> {
    return this.http.get(`${this.baseUrl}/recommendations`);
  }

  getMonthlyOutlook(): Observable<any> {
    return this.http.get(`${this.baseUrl}/monthly-outlook`);
  }

  createSavingsPlan(targetAmount: number, months: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/savings-plan`, null, {
      params: { 
        target_amount: targetAmount.toString(), 
        months: months.toString() 
      }
    });
  }

  customAnalysis(question: string, context?: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/custom-analysis`, {
      question,
      context
    });
  }

  getDashboardData(): Observable<any> {
    return this.http.get(`${this.baseUrl}/dashboard`);
  }
}
```

---

### Componentes Dashboard

#### Dashboard Component

```typescript
// src/app/features/dashboard/dashboard.component.ts
import { Component, OnInit } from '@angular/core';
import { InsightsService } from '@/core/services/insights.service';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
  dashboardData: any;
  loading = true;

  constructor(private insightsService: InsightsService) {}

  ngOnInit(): void {
    this.loadDashboard();
  }

  loadDashboard(): void {
    this.insightsService.getDashboardData().subscribe({
      next: (data) => {
        this.dashboardData = data;
        this.loading = false;
        this.renderCharts();
      },
      error: (err) => {
        console.error('Error loading dashboard:', err);
        this.loading = false;
      }
    });
  }

  renderCharts(): void {
    // Implementar Chart.js rendering
  }
}
```

---

#### Insight Card Component

```typescript
// src/app/shared/components/insight-card/insight-card.component.ts
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-insight-card',
  template: `
    <div class="insight-card" [ngClass]="'insight-' + insight.type">
      <div class="insight-header">
        <span class="insight-icon">{{ insight.icon }}</span>
        <span class="insight-priority" [ngClass]="'priority-' + insight.priority">
          {{ insight.priority }}
        </span>
      </div>
      <h3>{{ insight.title }}</h3>
      <p>{{ insight.message }}</p>
      <button *ngIf="insight.action" 
              (click)="handleAction(insight.action)">
        {{ insight.action.label }}
      </button>
    </div>
  `,
  styleUrls: ['./insight-card.component.scss']
})
export class InsightCardComponent {
  @Input() insight!: any;

  handleAction(action: any): void {
    if (action.action_type === 'navigate') {
      // Navigate to route
      console.log('Navigate to:', action.route);
    }
  }
}
```

---

### Chart.js Integration

```bash
npm install chart.js
```

```typescript
// src/app/features/dashboard/charts/category-pie.component.ts
import { Component, OnInit } from '@angular/core';
import { Chart, registerables } from 'chart.js';
import { AnalyticsService } from '@/core/services/analytics.service';

Chart.register(...registerables);

@Component({
  selector: 'app-category-pie-chart',
  template: '<canvas #chartCanvas></canvas>'
})
export class CategoryPieChartComponent implements OnInit {
  chart: any;

  constructor(private analyticsService: AnalyticsService) {}

  ngOnInit(): void {
    this.loadChart();
  }

  loadChart(): void {
    this.analyticsService.getCategoryChartData('expense', 'current_month')
      .subscribe(response => {
        const ctx = document.getElementById('chartCanvas') as HTMLCanvasElement;
        
        this.chart = new Chart(ctx, {
          type: 'pie',
          data: response.chart_data,
          options: {
            responsive: true,
            plugins: {
              legend: {
                position: 'bottom'
              },
              tooltip: {
                callbacks: {
                  label: (context) => {
                    const label = context.label || '';
                    const value = context.parsed || 0;
                    const percentage = ((value / context.dataset.data.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                    return `${label}: €${value.toFixed(2)} (${percentage}%)`;
                  }
                }
              }
            }
          }
        });
      });
  }
}
```

---

## 📚 Ejemplos de Uso

### Escenario 1: Dashboard Principal

```typescript
// Usuario accede al dashboard
this.insightsService.getDashboardData().subscribe(data => {
  // Renderizar resumen financiero
  this.summary = data.analytics.summary;
  
  // Mostrar insights
  this.insights = data.insights;
  
  // Renderizar gráficos
  this.renderPieChart(data.analytics.categories);
  this.renderLineChart(data.analytics.trends);
  
  // Mostrar health score
  this.healthScore = data.health_score;
});
```

---

### Escenario 2: Análisis de Categorías

```typescript
// Usuario quiere ver en qué gasta más
this.analyticsService.getCategoryChartData('expense', 'current_month')
  .subscribe(response => {
    const topCategory = response.analytics_data.categories[0];
    
    alert(`Categoría con mayor gasto: ${topCategory.category_name} (€${topCategory.total})`);
    
    // Renderizar pie chart
    this.renderPieChart(response.chart_data);
  });
```

---

### Escenario 3: Plan de Ahorro

```typescript
// Usuario quiere ahorrar €3000 en 6 meses
this.insightsService.createSavingsPlan(3000, 6).subscribe(plan => {
  console.log(`Necesitas ahorrar €${plan.goal.monthly_savings_needed}/mes`);
  
  // Mostrar pasos del plan
  plan.plan_steps.forEach(step => {
    console.log(`${step.step_number}. ${step.action} (ahorro: €${step.expected_savings})`);
  });
  
  if (plan.feasibility === 'feasible') {
    alert(plan.motivational_message);
  } else {
    console.log('Considera estas alternativas:', plan.alternative_suggestions);
  }
});
```

---

### Escenario 4: Pregunta Personalizada

```typescript
// Usuario pregunta: "¿Por qué gasté más este mes?"
const question = "¿Por qué gasté más este mes?";

this.insightsService.customAnalysis(question).subscribe(response => {
  // Mostrar respuesta de Gemini
  console.log(response.answer);
  
  // Mostrar datos de soporte
  if (response.supporting_data) {
    console.log('Detalles:', response.supporting_data);
  }
  
  // Sugerir preguntas de seguimiento
  console.log('También puedes preguntar:');
  response.follow_up_questions.forEach(q => console.log(`- ${q}`));
});
```

---

## 🔧 Troubleshooting

### Error: "Gemini API Key not configured"

**Causa**: Variable `GEMINI_API_KEY` no está en `.env`

**Solución**:
```bash
# 1. Obtener API key en: https://aistudio.google.com/app/apikey
# 2. Agregar a .env:
echo "GEMINI_API_KEY=AIzaSy..." >> .env

# 3. Reiniciar backend
uvicorn app.main:app --reload
```

---

### Error: "google.generativeai module not found"

**Causa**: Paquete no instalado

**Solución**:
```bash
pip install google-generativeai==0.8.3
```

---

### Insights retornan "Análisis en Proceso"

**Causa**: Gemini no está disponible o API key inválida

**Diagnóstico**:
```python
from app.services.insights_service import InsightsService

service = InsightsService(db)
print(service._is_gemini_available())  # Should return True
```

**Solución**:
1. Verificar API key: `echo $GEMINI_API_KEY`
2. Validar cuota de Gemini en [Google AI Studio](https://aistudio.google.com/)
3. Revisar logs: `tail -f logsBackend/app_finance_*.log`

---

### Charts no se renderizan

**Causa**: Formato de datos incorrecto

**Solución**:
```typescript
// Verificar estructura
console.log(response.chart_data);

// Debe tener:
{
  labels: [...],
  datasets: [{ data: [...], backgroundColor: [...] }]
}

// Si falta algún campo, reportar issue
```

---

### Anomalías vacías

**Causa**: Pocos datos o threshold muy alto

**Solución**:
```python
# Reducir threshold
anomalies = await analytics.detect_anomalies(user_id, threshold=1.5)

# Verificar número de transacciones
summary = await analytics.calculate_monthly_summary(user_id, 'current_month')
print(summary.num_transactions)  # Debe ser >10 para detección confiable
```

---

### CORS errors en frontend

**Solución**:
```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # ← Verificar puerto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

---

## 🚀 Roadmap

### Fase 1: Core Analytics ✅
- [x] MCP Layer con 8 funciones
- [x] Analytics Service completo
- [x] Endpoints de analytics

### Fase 2: AI Insights ✅
- [x] Insights Service con Gemini
- [x] Endpoints de insights
- [x] Health score & recommendations

### Fase 3: Frontend Integration (Next)
- [ ] Servicios Angular
- [ ] Dashboard component
- [ ] Insight cards
- [ ] Chart.js visualizations
- [ ] Chat interface para custom analysis

### Fase 4: Advanced Features
- [ ] Budgeting goals tracking
- [ ] Alerts/notifications
- [ ] PDF reports generation
- [ ] Comparative analysis (user vs benchmark)
- [ ] Multi-currency support
- [ ] Predictive ML models (beyond Gemini)

### Fase 5: Optimization
- [ ] Caching de insights (Redis)
- [ ] Background jobs para análisis pesados (Celery)
- [ ] A/B testing de prompts de Gemini
- [ ] Telemetry & analytics del sistema

---

## 📝 Notas Adicionales

### Costos de Gemini

- **Gemini 2.0 Flash**: Gratis hasta 1500 requests/día
- Después: $0.075 por 1M tokens input

**Estimación**: ~500 requests/día = gratis  
**Optimización**: Cache insights por 1 hora

---

### Seguridad

✅ **Implementado**:
- JWT authentication en todos los endpoints
- Rate limiting en login
- CORS configurado
- SQL injection prevention (SQLAlchemy ORM)
- Gemini no accede directamente a DB (MCP abstraction)

⚠️ **Pendiente**:
- Rate limiting en endpoints de insights (prevenir abuse)
- Sanitización de user input en custom_analysis
- Audit logs de llamadas a Gemini

---

### Performance

**Optimizaciones aplicadas**:
- Endpoint `/dashboard` combina múltiples queries
- Queries SQLAlchemy optimizadas con índices
- Pydantic models con validación eficiente

**Métricas objetivo**:
- `/analytics/*`: <200ms
- `/insights/generate`: <3s (Gemini latency)
- `/insights/dashboard`: <4s

---

## 📞 Soporte

**Documentación relacionada**:
- [API Usage Guide](API_USAGE_GUIDE.md)
- [JWT Authentication](JWT_AUTHENTICATION.md)
- [Logging](LOGGING.md)

**Issues comunes**:
- Revisar logs en `logsBackend/app_finance_*.log`
- API docs interactiva: http://localhost:8000/docs
- Gemini status: https://status.cloud.google.com/

---

**Última actualización**: 9 Enero 2026  
**Versión**: 1.0.0  
**Autor**: Sistema de Analytics e Insights - AppFinanzas
