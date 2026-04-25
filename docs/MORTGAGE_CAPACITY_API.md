# API de Capacidad Hipotecaria - Guía de Integración Frontend

## Contexto

Este documento describe la API de **Capacidad Hipotecaria** del backend de la aplicación de finanzas personales. Esta API permite calcular el precio máximo de vivienda que un usuario puede permitirse basándose en su historial financiero real (transacciones, ingresos, gastos, deudas).

**Objetivo:** Proporcionar al usuario una estimación realista y personalizada de su capacidad para adquirir una vivienda, con diferentes escenarios de riesgo y la posibilidad de analizar precios objetivo específicos.

---

## Resumen de Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/financial-analysis/financial-profile` | Obtiene resumen del perfil financiero del usuario |
| `GET` | `/api/financial-analysis/mortgage-capacity` | Calcula capacidad hipotecaria con parámetros en query |
| `POST` | `/api/financial-analysis/mortgage-capacity` | Calcula capacidad hipotecaria con configuración en body |
| `POST` | `/api/financial-analysis/mortgage-capacity/target-price` | Analiza viabilidad de un precio objetivo |

---

## Autenticación

Todos los endpoints requieren autenticación JWT. Incluir el token en el header:

```
Authorization: Bearer <access_token>
```

Si el token es inválido o ha expirado, la API retorna `401 Unauthorized`.

---

## Endpoint 1: Obtener Perfil Financiero

### Descripción
Retorna un resumen del estado financiero actual del usuario. Este endpoint es útil para mostrar al usuario su situación antes de calcular la capacidad hipotecaria.

### Request

```
GET /api/financial-analysis/financial-profile
```

**Query Parameters:**

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `months_to_analyze` | integer | No | 6 | Número de meses de histórico a analizar. Mínimo: 3, Máximo: 24 |

**Ejemplo de llamada:**
```
GET /api/financial-analysis/financial-profile?months_to_analyze=6
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Response

**Status 200 OK:**

```json
{
  "monthly_income": 3000.00,
  "income_stability": 92.5,
  "fixed_expenses": 800.00,
  "variable_expenses": 600.00,
  "debt_payments": 200.00,
  "disposable_income": 1400.00,
  "savings_rate_percentage": 33.3,
  "health_status": "good",
  "currency": "EUR",
  "analysis_period_months": 6
}
```

**Campos de respuesta:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `monthly_income` | float | Ingreso mensual promedio |
| `income_stability` | float | Estabilidad de ingresos en porcentaje (0-100). Mayor = más estable |
| `fixed_expenses` | float | Gastos fijos mensuales (alquiler, servicios, suscripciones) |
| `variable_expenses` | float | Gastos variables mensuales (alimentación, ocio) |
| `debt_payments` | float | Pagos de deuda mensuales (préstamos, créditos) |
| `disposable_income` | float | Ingreso disponible después de gastos y deudas |
| `savings_rate_percentage` | float | Tasa de ahorro en porcentaje |
| `health_status` | string | Estado de salud financiera |
| `currency` | string | Moneda de los valores |
| `analysis_period_months` | integer | Meses reales analizados |

**Valores posibles de `health_status`:**

| Valor | Significado | Color sugerido |
|-------|-------------|----------------|
| `excellent` | Tasa de ahorro > 20% | Verde brillante (#059669) |
| `good` | Tasa de ahorro 10-20% | Verde (#10B981) |
| `fair` | Tasa de ahorro 5-10% | Amarillo (#FBBF24) |
| `needs_improvement` | Tasa de ahorro 0-5% | Naranja (#F97316) |
| `critical` | Sin capacidad de ahorro | Rojo (#DC2626) |

---

## Endpoint 2: Calcular Capacidad Hipotecaria (GET)

### Descripción
Calcula el precio máximo de vivienda que el usuario puede permitirse, junto con escenarios alternativos y nivel de riesgo.

### Request

```
GET /api/financial-analysis/mortgage-capacity
```

**Query Parameters:**

| Parámetro | Tipo | Requerido | Default | Rango | Descripción |
|-----------|------|-----------|---------|-------|-------------|
| `months_to_analyze` | integer | No | 6 | 3-24 | Meses de histórico a analizar |
| `interest_rate` | float | No | 0.03 | 0-0.20 | Tasa de interés anual (0.03 = 3%) |
| `years` | integer | No | 30 | 5-40 | Plazo de la hipoteca en años |
| `down_payment_ratio` | float | No | 0.20 | 0-0.50 | Porcentaje de entrada (0.20 = 20%) |

**Ejemplo de llamada:**
```
GET /api/financial-analysis/mortgage-capacity?interest_rate=0.035&years=25&down_payment_ratio=0.15
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Response

**Status 200 OK:**

```json
{
  "max_price": 185000.00,
  "loan_amount": 148000.00,
  "monthly_payment": 620.00,
  "required_down_payment": 37000.00,
  "risk_score": "medium",
  "scenarios": {
    "conservative": {
      "monthly_payment": 500.00,
      "loan_amount": 120000.00,
      "max_price": 150000.00,
      "required_down_payment": 30000.00,
      "debt_to_income_ratio": 0.25
    },
    "balanced": {
      "monthly_payment": 620.00,
      "loan_amount": 148000.00,
      "max_price": 185000.00,
      "required_down_payment": 37000.00,
      "debt_to_income_ratio": 0.30
    },
    "aggressive": {
      "monthly_payment": 750.00,
      "loan_amount": 180000.00,
      "max_price": 225000.00,
      "required_down_payment": 45000.00,
      "debt_to_income_ratio": 0.35
    }
  },
  "calculation_details": {
    "savings_capacity": 800.00,
    "max_quota_by_savings": 640.00,
    "max_quota_by_income": 850.00,
    "final_max_quota": 620.00,
    "interest_rate": 0.03,
    "years": 30,
    "down_payment_ratio": 0.20,
    "income_stability_score": 0.92,
    "total_debt_ratio": 0.07
  },
  "currency": "EUR",
  "metadata": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "calculated_at": "2026-04-10T15:30:00.000Z",
    "months_analyzed": 6,
    "data_summary": {
      "avg_income": 3000.00,
      "total_expenses": 2000.00,
      "savings_rate": 0.33
    }
  }
}
```

**Campos principales de respuesta:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `max_price` | float | Precio máximo de vivienda recomendado |
| `loan_amount` | float | Monto del préstamo hipotecario |
| `monthly_payment` | float | Cuota mensual estimada |
| `required_down_payment` | float | Entrada requerida |
| `risk_score` | string | Nivel de riesgo: `low`, `medium`, `high` |
| `scenarios` | object | Tres escenarios alternativos |
| `calculation_details` | object | Detalles del cálculo para transparencia |
| `currency` | string | Moneda de los valores |
| `metadata` | object | Metadatos del cálculo |

**Valores de `risk_score`:**

| Valor | Significado | Color sugerido |
|-------|-------------|----------------|
| `low` | Perfil financiero sólido | Verde (#10B981) |
| `medium` | Perfil aceptable con consideraciones | Amarillo (#F59E0B) |
| `high` | Se recomienda mejorar situación antes de comprar | Rojo (#EF4444) |

**Descripción de escenarios:**

| Escenario | Factor DTI | Descripción |
|-----------|------------|-------------|
| `conservative` | 25% | Máxima seguridad financiera, menor estrés |
| `balanced` | 30% | Equilibrio razonable entre precio y seguridad |
| `aggressive` | 35% | Mayor precio pero mayor riesgo financiero |

---

## Endpoint 3: Calcular Capacidad Hipotecaria (POST)

### Descripción
Igual que el endpoint GET pero permite enviar configuración completa en el body. Útil cuando se necesitan todos los parámetros de configuración.

### Request

```
POST /api/financial-analysis/mortgage-capacity
Content-Type: application/json
```

**Query Parameters:**

| Parámetro | Tipo | Requerido | Default |
|-----------|------|-----------|---------|
| `months_to_analyze` | integer | No | 6 |

**Body:**

```json
{
  "interest_rate": 0.035,
  "years": 25,
  "down_payment_ratio": 0.15,
  "max_debt_ratio": 0.35,
  "safety_margin": 0.10
}
```

**Campos del body:**

| Campo | Tipo | Requerido | Default | Rango | Descripción |
|-------|------|-----------|---------|-------|-------------|
| `interest_rate` | float | No | 0.03 | 0-0.20 | Tasa de interés anual |
| `years` | integer | No | 30 | 5-40 | Plazo en años |
| `down_payment_ratio` | float | No | 0.20 | 0-0.50 | Porcentaje de entrada |
| `max_debt_ratio` | float | No | 0.35 | 0.20-0.50 | Ratio máximo deuda/ingresos |
| `safety_margin` | float | No | 0.10 | 0-0.30 | Margen de seguridad adicional |

### Response

Mismo formato que el endpoint GET.

---

## Endpoint 4: Analizar Precio Objetivo

### Descripción
Permite al usuario ingresar un precio de vivienda específico y determinar si es alcanzable con su perfil financiero actual. Responde a la pregunta: "¿Puedo permitirme una casa de X euros?"

### Request

```
POST /api/financial-analysis/mortgage-capacity/target-price
Content-Type: application/json
```

**Query Parameters:**

| Parámetro | Tipo | Requerido | Default |
|-----------|------|-----------|---------|
| `months_to_analyze` | integer | No | 6 |

**Body:**

```json
{
  "target_price": 200000,
  "config": {
    "interest_rate": 0.03,
    "years": 30,
    "down_payment_ratio": 0.20
  }
}
```

**Campos del body:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `target_price` | float | Sí | Precio objetivo de la vivienda (debe ser > 0) |
| `config` | object | No | Configuración de hipoteca (mismos campos que POST anterior) |

### Response

**Status 200 OK - Objetivo VIABLE:**

```json
{
  "target_price": 170000.00,
  "loan_needed": 136000.00,
  "down_payment_needed": 34000.00,
  "monthly_payment_needed": 574.00,
  "is_viable": true,
  "gap": 46.00,
  "resulting_debt_ratio": 0.28,
  "recommendation": "Objetivo viable con buen margen de seguridad. Tu perfil financiero es adecuado para esta compra.",
  "comparison": {
    "max_affordable_price": 185000.00,
    "difference_from_max": -15000.00,
    "percentage_of_max": 91.89
  },
  "currency": "EUR"
}
```

**Status 200 OK - Objetivo NO VIABLE:**

```json
{
  "target_price": 250000.00,
  "loan_needed": 200000.00,
  "down_payment_needed": 50000.00,
  "monthly_payment_needed": 844.00,
  "is_viable": false,
  "gap": -224.00,
  "resulting_debt_ratio": 0.42,
  "recommendation": "Objetivo no viable actualmente. Déficit mensual: 224.00 EUR. Considera aumentar ingresos, reducir gastos, o buscar una vivienda más económica.",
  "comparison": {
    "max_affordable_price": 185000.00,
    "difference_from_max": 65000.00,
    "percentage_of_max": 135.14
  },
  "currency": "EUR"
}
```

**Campos de respuesta:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `target_price` | float | Precio objetivo solicitado |
| `loan_needed` | float | Préstamo necesario para ese precio |
| `down_payment_needed` | float | Entrada necesaria |
| `monthly_payment_needed` | float | Cuota mensual que se pagaría |
| `is_viable` | boolean | `true` si el objetivo es alcanzable |
| `gap` | float | Diferencia entre cuota máxima y necesaria. Positivo = sobra, Negativo = falta |
| `resulting_debt_ratio` | float | Ratio deuda/ingresos resultante |
| `recommendation` | string | Recomendación textual personalizada |
| `comparison` | object | Comparación con la capacidad máxima |

**Campos de `comparison`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `max_affordable_price` | float | Precio máximo que puede pagar |
| `difference_from_max` | float | Diferencia con el objetivo. Negativo = objetivo menor al máximo |
| `percentage_of_max` | float | El objetivo como % del máximo (100 = igual, >100 = supera el máximo) |

---

## Manejo de Errores

### Errores Comunes

**400 Bad Request - Parámetros inválidos:**
```json
{
  "detail": "Parámetros inválidos: interest_rate debe estar entre 0% y 20%"
}
```

**401 Unauthorized - Token inválido o expirado:**
```json
{
  "detail": "Could not validate credentials"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Error al calcular capacidad hipotecaria: [mensaje de error]"
}
```

### Usuario sin datos suficientes

Si el usuario no tiene suficientes transacciones, la API retorna valores en cero:

```json
{
  "max_price": 0,
  "loan_amount": 0,
  "monthly_payment": 0,
  "required_down_payment": 0,
  "risk_score": "high",
  "scenarios": {
    "conservative": { "max_price": 0, "monthly_payment": 0, ... },
    "balanced": { "max_price": 0, "monthly_payment": 0, ... },
    "aggressive": { "max_price": 0, "monthly_payment": 0, ... }
  },
  "metadata": {
    "months_analyzed": 0,
    "data_summary": {
      "avg_income": 0,
      "total_expenses": 0,
      "savings_rate": 0
    }
  }
}
```

**Recomendación UI:** Detectar cuando `metadata.months_analyzed === 0` o `max_price === 0` y mostrar mensaje:
> "Necesitas al menos 3 meses de transacciones registradas para calcular tu capacidad hipotecaria."

---

## Flujo de Implementación Recomendado

### Paso 1: Crear el Servicio HTTP

```typescript
// services/mortgage-capacity.service.ts

interface MortgageConfig {
  interestRate?: number;
  years?: number;
  downPaymentRatio?: number;
  maxDebtRatio?: number;
  safetyMargin?: number;
}

class MortgageCapacityService {
  private baseUrl = '/api/financial-analysis';

  async getFinancialProfile(monthsToAnalyze = 6): Promise<FinancialProfile> {
    const response = await fetch(
      `${this.baseUrl}/financial-profile?months_to_analyze=${monthsToAnalyze}`,
      { headers: this.getHeaders() }
    );
    return response.json();
  }

  async calculateMortgageCapacity(config?: MortgageConfig): Promise<MortgageCapacityResult> {
    const params = new URLSearchParams();
    if (config?.interestRate) params.set('interest_rate', String(config.interestRate));
    if (config?.years) params.set('years', String(config.years));
    if (config?.downPaymentRatio) params.set('down_payment_ratio', String(config.downPaymentRatio));

    const response = await fetch(
      `${this.baseUrl}/mortgage-capacity?${params}`,
      { headers: this.getHeaders() }
    );
    return response.json();
  }

  async analyzeTargetPrice(targetPrice: number, config?: MortgageConfig): Promise<TargetPriceResult> {
    const response = await fetch(
      `${this.baseUrl}/mortgage-capacity/target-price`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          target_price: targetPrice,
          config: config ? {
            interest_rate: config.interestRate,
            years: config.years,
            down_payment_ratio: config.downPaymentRatio
          } : undefined
        })
      }
    );
    return response.json();
  }

  private getHeaders(): HeadersInit {
    return {
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    };
  }
}
```

### Paso 2: Crear Interfaces/Tipos

```typescript
// types/mortgage-capacity.types.ts

type HealthStatus = 'excellent' | 'good' | 'fair' | 'needs_improvement' | 'critical';
type RiskLevel = 'low' | 'medium' | 'high';

interface FinancialProfile {
  monthly_income: number;
  income_stability: number;
  fixed_expenses: number;
  variable_expenses: number;
  debt_payments: number;
  disposable_income: number;
  savings_rate_percentage: number;
  health_status: HealthStatus;
  currency: string;
  analysis_period_months: number;
}

interface ScenarioDetail {
  monthly_payment: number;
  loan_amount: number;
  max_price: number;
  required_down_payment: number;
  debt_to_income_ratio: number;
}

interface MortgageCapacityResult {
  max_price: number;
  loan_amount: number;
  monthly_payment: number;
  required_down_payment: number;
  risk_score: RiskLevel;
  scenarios: {
    conservative: ScenarioDetail;
    balanced: ScenarioDetail;
    aggressive: ScenarioDetail;
  };
  calculation_details: {
    savings_capacity: number;
    max_quota_by_savings: number;
    max_quota_by_income: number;
    final_max_quota: number;
    interest_rate: number;
    years: number;
    down_payment_ratio: number;
    income_stability_score: number;
    total_debt_ratio: number;
  };
  currency: string;
  metadata: {
    user_id: string;
    calculated_at: string;
    months_analyzed: number;
    data_summary: {
      avg_income: number;
      total_expenses: number;
      savings_rate: number;
    };
  };
}

interface TargetPriceResult {
  target_price: number;
  loan_needed: number;
  down_payment_needed: number;
  monthly_payment_needed: number;
  is_viable: boolean;
  gap: number;
  resulting_debt_ratio: number;
  recommendation: string;
  comparison: {
    max_affordable_price: number;
    difference_from_max: number;
    percentage_of_max: number;
  };
  currency: string;
}
```

### Paso 3: Estructura de Pantalla Sugerida

```
┌────────────────────────────────────────────────────────────────────┐
│  CALCULADORA DE CAPACIDAD HIPOTECARIA                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  TU PERFIL FINANCIERO                          [Actualizar]  │ │
│  │                                                              │ │
│  │  Ingresos mensuales:    €3,000        Estabilidad: ████░ 92% │ │
│  │  Gastos fijos:          €800          Gastos variables: €600 │ │
│  │  Pagos de deuda:        €200          Disponible: €1,400     │ │
│  │                                                              │ │
│  │  Tasa de ahorro: 33.3%                Estado: ● BUENO        │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  CONFIGURACIÓN DE HIPOTECA                    [▼ Expandir]   │ │
│  │                                                              │ │
│  │  Tipo de interés: [3.0 %]    Plazo: [30 años]               │ │
│  │  Porcentaje entrada: [20 %]                                  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│                    [  CALCULAR CAPACIDAD  ]                        │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                  PRECIO MÁXIMO DE VIVIENDA                   │ │
│  │                                                              │ │
│  │                       €185,000                               │ │
│  │                                                              │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│ │
│  │  │  Préstamo  │ │   Cuota    │ │  Entrada   │ │   Riesgo   ││ │
│  │  │  €148,000  │ │  €620/mes  │ │  €37,000   │ │  ● MEDIO   ││ │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘│ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  ESCENARIOS                                                  │ │
│  │                                                              │ │
│  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐   │ │
│  │  │  CONSERVADOR   │ │  EQUILIBRADO   │ │    AGRESIVO    │   │ │
│  │  │                │ │   ✓ Actual     │ │                │   │ │
│  │  │   €150,000     │ │   €185,000     │ │   €225,000     │   │ │
│  │  │   €500/mes     │ │   €620/mes     │ │   €750/mes     │   │ │
│  │  │   DTI: 25%     │ │   DTI: 30%     │ │   DTI: 35%     │   │ │
│  │  │                │ │                │ │                │   │ │
│  │  │  Menor riesgo  │ │  Recomendado   │ │  Mayor riesgo  │   │ │
│  │  └────────────────┘ └────────────────┘ └────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  ¿TIENES UN PRECIO EN MENTE?                                 │ │
│  │                                                              │ │
│  │  Precio objetivo: [€ 200,000        ]  [ ANALIZAR ]          │ │
│  │                                                              │ │
│  │  ┌────────────────────────────────────────────────────────┐ │ │
│  │  │  ✗ NO VIABLE                                           │ │ │
│  │  │                                                        │ │ │
│  │  │  Te faltan €55/mes para alcanzar este objetivo.        │ │ │
│  │  │  Este precio es un 108% de tu capacidad máxima.        │ │ │
│  │  │                                                        │ │ │
│  │  │  Recomendación: Considera aumentar ingresos, reducir   │ │ │
│  │  │  gastos, o buscar una vivienda más económica.          │ │ │
│  │  └────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Paso 4: Utilidades de Formateo

```typescript
// utils/format.ts

export const formatCurrency = (amount: number, currency = 'EUR'): string => {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
};

export const formatPercentage = (value: number, decimals = 1): string => {
  return `${value.toFixed(decimals)}%`;
};

export const getHealthStatusColor = (status: HealthStatus): string => {
  const colors = {
    excellent: '#059669',
    good: '#10B981',
    fair: '#FBBF24',
    needs_improvement: '#F97316',
    critical: '#DC2626'
  };
  return colors[status];
};

export const getHealthStatusLabel = (status: HealthStatus): string => {
  const labels = {
    excellent: 'Excelente',
    good: 'Bueno',
    fair: 'Aceptable',
    needs_improvement: 'Necesita mejora',
    critical: 'Crítico'
  };
  return labels[status];
};

export const getRiskScoreColor = (risk: RiskLevel): string => {
  const colors = {
    low: '#10B981',
    medium: '#F59E0B',
    high: '#EF4444'
  };
  return colors[risk];
};

export const getRiskScoreLabel = (risk: RiskLevel): string => {
  const labels = {
    low: 'Bajo',
    medium: 'Medio',
    high: 'Alto'
  };
  return labels[risk];
};
```

### Paso 5: Validaciones en Frontend

```typescript
// utils/validation.ts

export const validateMortgageConfig = (config: MortgageConfig): string[] => {
  const errors: string[] = [];

  if (config.interestRate !== undefined) {
    if (config.interestRate < 0 || config.interestRate > 0.20) {
      errors.push('El tipo de interés debe estar entre 0% y 20%');
    }
  }

  if (config.years !== undefined) {
    if (config.years < 5 || config.years > 40) {
      errors.push('El plazo debe estar entre 5 y 40 años');
    }
  }

  if (config.downPaymentRatio !== undefined) {
    if (config.downPaymentRatio < 0 || config.downPaymentRatio > 0.50) {
      errors.push('El porcentaje de entrada debe estar entre 0% y 50%');
    }
  }

  return errors;
};

export const validateTargetPrice = (price: number): string | null => {
  if (price <= 0) {
    return 'El precio debe ser mayor que 0';
  }
  if (price > 10000000) {
    return 'El precio parece demasiado alto';
  }
  return null;
};
```

---

## Estados de UI a Manejar

### 1. Loading
Mostrar skeleton o spinner mientras se cargan los datos.

### 2. Sin datos suficientes
Cuando `metadata.months_analyzed === 0` o `max_price === 0`:
```
"Para calcular tu capacidad hipotecaria necesitamos al menos 3 meses
de historial de transacciones. Continúa registrando tus movimientos
y vuelve pronto."
```

### 3. Error de API
Mostrar mensaje de error con opción de reintentar.

### 4. Resultado exitoso
Mostrar todos los datos con la estructura visual recomendada.

### 5. Análisis de precio - Viable
Destacar en verde con icono de check.

### 6. Análisis de precio - No viable
Destacar en rojo/naranja con icono de warning y mostrar la recomendación.

---

## Notas Técnicas Adicionales

1. **Caché:** Los resultados no cambian frecuentemente. Se puede cachear por 1 hora o hasta que el usuario agregue nuevas transacciones.

2. **Responsive:** Los escenarios deben adaptarse a móvil (cards apiladas verticalmente).

3. **Accesibilidad:** Usar roles ARIA apropiados para los indicadores de color (health_status, risk_score).

4. **Internacionalización:** El backend retorna `currency` en cada respuesta. Usarlo para formatear correctamente.

5. **DTI (Debt-to-Income):** Si el frontend necesita explicar qué significa, el DTI es el ratio entre todos los pagos de deuda mensuales y los ingresos mensuales. Un DTI del 30% significa que el 30% de los ingresos se destina a pagar deudas.

---

## Resumen de Colores

| Elemento | Valor | Color Hex |
|----------|-------|-----------|
| Health - Excellent | `excellent` | #059669 |
| Health - Good | `good` | #10B981 |
| Health - Fair | `fair` | #FBBF24 |
| Health - Needs Improvement | `needs_improvement` | #F97316 |
| Health - Critical | `critical` | #DC2626 |
| Risk - Low | `low` | #10B981 |
| Risk - Medium | `medium` | #F59E0B |
| Risk - High | `high` | #EF4444 |
| Scenario - Conservative | - | #6366F1 |
| Scenario - Balanced | - | #10B981 |
| Scenario - Aggressive | - | #F59E0B |
| Viable | `true` | #10B981 |
| Not Viable | `false` | #EF4444 |
