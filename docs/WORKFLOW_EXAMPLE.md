# 🔄 Workflow Completo - Ejemplo Real con AMZN, AAPL, CMG

## 📋 Escenario Inicial

**Usuario:** Juan Pérez (user_id: `uuid-456`)

**Inversiones en Base de Datos (PostgreSQL):**

| id | user_id | symbol | company_name | shares | average_price | purchase_date |
|----|---------|--------|--------------|--------|---------------|---------------|
| uuid-001 | uuid-456 | AMZN | Amazon.com Inc. | 4.0 | 190.00 | 2024-03-15 |
| uuid-002 | uuid-456 | AAPL | Apple Inc. | 2.0 | 200.00 | 2024-05-20 |
| uuid-003 | uuid-456 | CMG | Chipotle Mexican Grill | 10.0 | 45.00 | 2023-11-10 |

**Total Invertido Inicial:**
- AMZN: 4 × $190 = **$760**
- AAPL: 2 × $200 = **$400**
- CMG: 10 × $45 = **$450**
- **TOTAL INVERTIDO: $1,610**

---

## 🚀 Workflow Paso a Paso

### PASO 1️⃣: Usuario Abre la Página de Inversiones

**Frontend - `investment.component.ts`**

```typescript
ngOnInit(): void {
  this.loadPositions();
}

loadPositions(): void {
  this.loading.set(true);
  
  // UNA sola llamada HTTP
  this.investmentService.getInvestmentsWithSummary().subscribe({
    next: (data) => {
      this.positions.set(data.positions);
      this.summary.set(data.summary);
      this.insights.set(data.insights);
      this.loading.set(false);
    }
  });
}
```

**HTTP Request enviada:**
```http
GET http://localhost:8000/api/investments
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### PASO 2️⃣: Backend Recibe Request

**Backend - `routes/investments.py`**

```python
@router.get("", response_model=InvestmentsWithSummary)
async def list_investments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Autenticación: Verifica JWT token
    # current_user.id = uuid-456 (Juan Pérez)
    
    # 2. Consultar inversiones del usuario en DB
    investments = investment_service.get_user_investments(db, current_user.id)
    
    # investments = [
    #   Investment(id=uuid-001, symbol="AMZN", shares=4.0, average_price=190.00),
    #   Investment(id=uuid-002, symbol="AAPL", shares=2.0, average_price=200.00),
    #   Investment(id=uuid-003, symbol="CMG", shares=10.0, average_price=45.00)
    # ]
    
    # 3. Enriquecer con datos de mercado
    enriched = await investment_service.enrich_investments(investments)
    
    # 4. Calcular resumen
    summary = investment_service.calculate_portfolio_summary(enriched)
    
    # 5. Generar insights
    insights = investment_service.generate_insights(enriched, summary)
    
    return InvestmentsWithSummary(
        positions=enriched,
        summary=summary,
        insights=insights
    )
```

---

### PASO 3️⃣: Consulta a Base de Datos

**SQL Query Ejecutada:**
```sql
SELECT * FROM investments 
WHERE user_id = 'uuid-456'
ORDER BY created_at DESC;
```

**Resultado (3 filas):**
```
id       | user_id  | symbol | company_name              | shares | average_price | purchase_date
---------|----------|--------|---------------------------|--------|---------------|---------------
uuid-001 | uuid-456 | AMZN   | Amazon.com Inc.           | 4.0000 | 190.00        | 2024-03-15
uuid-002 | uuid-456 | AAPL   | Apple Inc.                | 2.0000 | 200.00        | 2024-05-20
uuid-003 | uuid-456 | CMG    | Chipotle Mexican Grill    | 10.0000| 45.00         | 2023-11-10
```

---

### PASO 4️⃣: Enriquecimiento con Alpha Vantage

**Backend - `investment_service.py`**

```python
async def enrich_investments(investments: List[Investment]):
    # Extraer símbolos únicos
    symbols = ["AMZN", "AAPL", "CMG"]
    
    # Obtener cotizaciones de Alpha Vantage
    quotes = await alpha_vantage_service.get_multiple_quotes(symbols)
    
    # quotes = {
    #   "AMZN": StockQuote(...),
    #   "AAPL": StockQuote(...),
    #   "CMG": StockQuote(...)
    # }
```

#### 4.1: Llamadas a Alpha Vantage API

**Para AMZN:**
```http
GET https://www.alphavantage.co/query
    ?function=GLOBAL_QUOTE
    &symbol=AMZN
    &apikey=YOUR_API_KEY
```

**Respuesta Alpha Vantage (AMZN):**
```json
{
  "Global Quote": {
    "01. symbol": "AMZN",
    "02. open": "178.0000",
    "03. high": "179.3000",
    "04. low": "176.5000",
    "05. price": "178.2000",
    "06. volume": "45892341",
    "07. latest trading day": "2026-01-12",
    "08. previous close": "177.3000",
    "09. change": "0.9000",
    "10. change percent": "0.5073%"
  }
}
```

**Parsing (alpha_vantage.py):**
```python
# Para AMZN
price = 178.20          # De "05. price"
change = 0.90           # De "09. change"
change_percent = 0.51   # De "10. change percent" (sin %)

stock_quote_amzn = StockQuote(
    symbol="AMZN",
    price=178.20,
    change=0.90,
    change_percent=0.51,
    high=179.30,
    low=176.50,
    open=178.00,
    previous_close=177.30,
    volume=45892341
)
```

---

**Para AAPL:**
```http
GET https://www.alphavantage.co/query
    ?function=GLOBAL_QUOTE
    &symbol=AAPL
    &apikey=YOUR_API_KEY
```

**Respuesta Alpha Vantage (AAPL):**
```json
{
  "Global Quote": {
    "01. symbol": "AAPL",
    "05. price": "230.5000",
    "09. change": "3.2500",
    "10. change percent": "1.4296%"
  }
}
```

**Parsing:**
```python
stock_quote_aapl = StockQuote(
    symbol="AAPL",
    price=230.50,
    change=3.25,
    change_percent=1.43
)
```

---

**Para CMG:**
```http
GET https://www.alphavantage.co/query
    ?function=GLOBAL_QUOTE
    &symbol=CMG
    &apikey=YOUR_API_KEY
```

**Respuesta Alpha Vantage (CMG):**
```json
{
  "Global Quote": {
    "01. symbol": "CMG",
    "05. price": "62.8000",
    "09. change": "1.1500",
    "10. change percent": "1.8644%"
  }
}
```

**Parsing:**
```python
stock_quote_cmg = StockQuote(
    symbol="CMG",
    price=62.80,
    change=1.15,
    change_percent=1.86
)
```

---

### PASO 5️⃣: Cálculos en Backend

**Backend - `investment_service.py`**

#### Posición 1: AMZN

```python
# Datos del usuario (DB)
shares = 4.0
average_price = 190.00
total_invested = 4.0 × 190.00 = 760.00

# Datos de Alpha Vantage
current_price = 178.20
change_percent = 0.51
day_change_per_share = 0.90

# Cálculos
total_value = 4.0 × 178.20 = 712.80
total_gain_loss = 712.80 - 760.00 = -47.20
total_gain_loss_percent = (-47.20 / 760.00) × 100 = -6.21%
day_change = 4.0 × 0.90 = 3.60

# EnrichedInvestment (AMZN)
{
    id: "uuid-001",
    symbol: "AMZN",
    company_name: "Amazon.com Inc.",
    shares: 4.0,
    average_price: 190.00,
    purchase_date: "2024-03-15",
    
    current_price: 178.20,        // ← De Alpha Vantage
    change_percent: 0.51,         // ← De Alpha Vantage
    total_value: 712.80,          // ← Calculado
    total_gain_loss: -47.20,      // ← Calculado (PÉRDIDA)
    total_gain_loss_percent: -6.21, // ← Calculado
    day_change: 3.60              // ← Calculado
}
```

#### Posición 2: AAPL

```python
# Datos del usuario (DB)
shares = 2.0
average_price = 200.00
total_invested = 2.0 × 200.00 = 400.00

# Datos de Alpha Vantage
current_price = 230.50
change_percent = 1.43
day_change_per_share = 3.25

# Cálculos
total_value = 2.0 × 230.50 = 461.00
total_gain_loss = 461.00 - 400.00 = 61.00
total_gain_loss_percent = (61.00 / 400.00) × 100 = 15.25%
day_change = 2.0 × 3.25 = 6.50

# EnrichedInvestment (AAPL)
{
    id: "uuid-002",
    symbol: "AAPL",
    company_name: "Apple Inc.",
    shares: 2.0,
    average_price: 200.00,
    purchase_date: "2024-05-20",
    
    current_price: 230.50,        // ← De Alpha Vantage
    change_percent: 1.43,         // ← De Alpha Vantage
    total_value: 461.00,          // ← Calculado
    total_gain_loss: 61.00,       // ← Calculado (GANANCIA)
    total_gain_loss_percent: 15.25, // ← Calculado
    day_change: 6.50              // ← Calculado
}
```

#### Posición 3: CMG

```python
# Datos del usuario (DB)
shares = 10.0
average_price = 45.00
total_invested = 10.0 × 45.00 = 450.00

# Datos de Alpha Vantage
current_price = 62.80
change_percent = 1.86
day_change_per_share = 1.15

# Cálculos
total_value = 10.0 × 62.80 = 628.00
total_gain_loss = 628.00 - 450.00 = 178.00
total_gain_loss_percent = (178.00 / 450.00) × 100 = 39.56%
day_change = 10.0 × 1.15 = 11.50

# EnrichedInvestment (CMG)
{
    id: "uuid-003",
    symbol: "CMG",
    company_name: "Chipotle Mexican Grill",
    shares: 10.0,
    average_price: 45.00,
    purchase_date: "2023-11-10",
    
    current_price: 62.80,         // ← De Alpha Vantage
    change_percent: 1.86,         // ← De Alpha Vantage
    total_value: 628.00,          // ← Calculado
    total_gain_loss: 178.00,      // ← Calculado (GANANCIA)
    total_gain_loss_percent: 39.56, // ← Calculado
    day_change: 11.50             // ← Calculado
}
```

---

### PASO 6️⃣: Resumen del Portfolio

**Backend - `investment_service.py`**

```python
def calculate_portfolio_summary(enriched_positions):
    # Suma de valores totales
    total_value = 712.80 + 461.00 + 628.00 = 1,801.80
    
    # Suma de inversiones iniciales
    total_invested = 760.00 + 400.00 + 450.00 = 1,610.00
    
    # Ganancia/Pérdida total
    total_gain_loss = 1,801.80 - 1,610.00 = 191.80
    
    # Porcentaje de ganancia
    total_gain_loss_percent = (191.80 / 1,610.00) × 100 = 11.91%
    
    # Cambio del día
    day_change = 3.60 + 6.50 + 11.50 = 21.60
    
    # Porcentaje del día
    previous_value = 1,801.80 - 21.60 = 1,780.20
    day_change_percent = (21.60 / 1,780.20) × 100 = 1.21%
    
    return PortfolioSummary(
        total_value=1801.80,
        total_invested=1610.00,
        total_gain_loss=191.80,
        total_gain_loss_percent=11.91,
        day_change=21.60,
        day_change_percent=1.21,
        positions_count=3
    )
```

**Tabla Resumen:**

| Métrica | Valor |
|---------|-------|
| Valor Total Actual | **$1,801.80** |
| Total Invertido | $1,610.00 |
| Ganancia/Pérdida | **+$191.80** |
| Rendimiento | **+11.91%** |
| Cambio del Día | **+$21.60** |
| % Cambio del Día | **+1.21%** |
| Posiciones | 3 |

---

### PASO 7️⃣: Generación de Insights

**Backend - `investment_service.py`**

```python
def generate_insights(enriched, summary):
    insights = []
    
    # 1. Diversificación (solo 3 posiciones)
    if summary.positions_count < 5:
        insights.append(InvestmentInsight(
            type="warning",
            title="Baja Diversificación",
            message="Tienes solo 3 posiciones. Considera diversificar en al menos 5-10 empresas diferentes para reducir el riesgo.",
            icon="⚠️"
        ))
    
    # 2. Rendimiento (+11.91% > +10%)
    if summary.total_gain_loss_percent > 10:
        insights.append(InvestmentInsight(
            type="success",
            title="Excelente Rendimiento",
            message="Tu cartera ha generado un +11.91% de ganancia.",
            icon="🚀"
        ))
    
    # 3. Concentración
    # CMG representa: 628.00 / 1801.80 = 34.87% > 30%
    max_position_percent = (628.00 / 1801.80) * 100  # 34.87%
    
    if max_position_percent > 30:
        insights.append(InvestmentInsight(
            type="warning",
            title="Alta Concentración",
            message="Una de tus posiciones (CMG) representa el 34.87% de tu cartera. Considera rebalancear.",
            icon="⚖️"
        ))
    
    return insights
```

**Insights Generados:**
1. ⚠️ **Baja Diversificación** - Solo 3 posiciones
2. 🚀 **Excelente Rendimiento** - +11.91% de ganancia
3. ⚖️ **Alta Concentración** - CMG representa 34.87%

---

### PASO 8️⃣: Response JSON al Frontend

**Backend Response:**

```json
{
  "positions": [
    {
      "id": "uuid-001",
      "user_id": "uuid-456",
      "symbol": "AMZN",
      "company_name": "Amazon.com Inc.",
      "shares": 4.0,
      "average_price": 190.00,
      "purchase_date": "2024-03-15",
      "current_price": 178.20,
      "change_percent": 0.51,
      "total_value": 712.80,
      "total_gain_loss": -47.20,
      "total_gain_loss_percent": -6.21,
      "day_change": 3.60
    },
    {
      "id": "uuid-002",
      "user_id": "uuid-456",
      "symbol": "AAPL",
      "company_name": "Apple Inc.",
      "shares": 2.0,
      "average_price": 200.00,
      "purchase_date": "2024-05-20",
      "current_price": 230.50,
      "change_percent": 1.43,
      "total_value": 461.00,
      "total_gain_loss": 61.00,
      "total_gain_loss_percent": 15.25,
      "day_change": 6.50
    },
    {
      "id": "uuid-003",
      "user_id": "uuid-456",
      "symbol": "CMG",
      "company_name": "Chipotle Mexican Grill",
      "shares": 10.0,
      "average_price": 45.00,
      "purchase_date": "2023-11-10",
      "current_price": 62.80,
      "change_percent": 1.86,
      "total_value": 628.00,
      "total_gain_loss": 178.00,
      "total_gain_loss_percent": 39.56,
      "day_change": 11.50
    }
  ],
  "summary": {
    "total_value": 1801.80,
    "total_invested": 1610.00,
    "total_gain_loss": 191.80,
    "total_gain_loss_percent": 11.91,
    "day_change": 21.60,
    "day_change_percent": 1.21,
    "positions_count": 3
  },
  "insights": [
    {
      "type": "warning",
      "title": "Baja Diversificación",
      "message": "Tienes solo 3 posiciones. Considera diversificar...",
      "icon": "⚠️"
    },
    {
      "type": "success",
      "title": "Excelente Rendimiento",
      "message": "Tu cartera ha generado un +11.91% de ganancia.",
      "icon": "🚀"
    },
    {
      "type": "warning",
      "title": "Alta Concentración",
      "message": "Una de tus posiciones (CMG) representa el 34.87%...",
      "icon": "⚖️"
    }
  ]
}
```

---

### PASO 9️⃣: Frontend Recibe y Procesa

**Frontend - `investment.component.ts`**

```typescript
this.investmentService.getInvestmentsWithSummary().subscribe({
  next: (data) => {
    // Asignar datos a signals
    this.positions.set(data.positions);
    // positions() = [
    //   { symbol: "AMZN", total_value: 712.80, total_gain_loss: -47.20, ... },
    //   { symbol: "AAPL", total_value: 461.00, total_gain_loss: 61.00, ... },
    //   { symbol: "CMG", total_value: 628.00, total_gain_loss: 178.00, ... }
    // ]
    
    this.summary.set(data.summary);
    // summary() = {
    //   total_value: 1801.80,
    //   total_gain_loss: 191.80,
    //   total_gain_loss_percent: 11.91,
    //   ...
    // }
    
    this.insights.set(data.insights);
    // insights() = [
    //   { type: "warning", title: "Baja Diversificación", ... },
    //   { type: "success", title: "Excelente Rendimiento", ... },
    //   { type: "warning", title: "Alta Concentración", ... }
    // ]
    
    this.loading.set(false);
  }
});
```

---

### PASO 🔟: Renderizado en Pantalla

**Frontend - `investment.component.html`**

#### KPI Cards

```html
<!-- Valor Total -->
<div class="kpi-card primary">
  <span class="kpi-value">{{ formatCurrency(summary().totalValue) }}</span>
  <!-- Muestra: $1,801.80 -->
  <span class="kpi-subtext">{{ summary().positionsCount }} posiciones</span>
  <!-- Muestra: 3 posiciones -->
</div>

<!-- Rendimiento Histórico -->
<div class="kpi-card">
  <span class="kpi-value" class="positive">
    {{ formatCurrency(summary().totalGainLoss) }}
  </span>
  <!-- Muestra: +$191.80 en VERDE -->
  <span class="kpi-subtext positive">
    {{ formatPercent(summary().totalGainLossPercent) }}
  </span>
  <!-- Muestra: +11.91% en VERDE -->
</div>

<!-- Ganancia del Día -->
<div class="kpi-card">
  <span class="kpi-value positive">
    {{ formatCurrency(summary().dayChange) }}
  </span>
  <!-- Muestra: +$21.60 en VERDE -->
  <span class="kpi-subtext positive">
    {{ formatPercent(summary().dayChangePercent) }}
  </span>
  <!-- Muestra: +1.21% en VERDE -->
</div>
```

#### Tabla de Posiciones

```html
<table>
  <thead>
    <tr>
      <th>Símbolo</th>
      <th>Empresa</th>
      <th>Acciones</th>
      <th>Precio Compra</th>
      <th>Precio Actual</th>
      <th>Cambio %</th>
      <th>Valor Total</th>
      <th>Ganancia/Pérdida</th>
    </tr>
  </thead>
  <tbody>
    <!-- Fila 1: AMZN -->
    <tr>
      <td>AMZN</td>
      <td>Amazon.com Inc.</td>
      <td>4.0</td>
      <td>$190.00</td>
      <td>$178.20</td>
      <td class="positive">+0.51%</td>
      <td>$712.80</td>
      <td class="negative">-$47.20 (-6.21%)</td>
      <!-- En ROJO porque es pérdida -->
    </tr>
    
    <!-- Fila 2: AAPL -->
    <tr>
      <td>AAPL</td>
      <td>Apple Inc.</td>
      <td>2.0</td>
      <td>$200.00</td>
      <td>$230.50</td>
      <td class="positive">+1.43%</td>
      <td>$461.00</td>
      <td class="positive">+$61.00 (+15.25%)</td>
      <!-- En VERDE porque es ganancia -->
    </tr>
    
    <!-- Fila 3: CMG -->
    <tr>
      <td>CMG</td>
      <td>Chipotle Mexican Grill</td>
      <td>10.0</td>
      <td>$45.00</td>
      <td>$62.80</td>
      <td class="positive">+1.86%</td>
      <td>$628.00</td>
      <td class="positive">+$178.00 (+39.56%)</td>
      <!-- En VERDE porque es ganancia -->
    </tr>
  </tbody>
</table>
```

#### Insights

```html
<div class="insights-container">
  <!-- Insight 1 -->
  <div class="alert warning">
    <strong>⚠️ Baja Diversificación</strong>
    <p>Tienes solo 3 posiciones. Considera diversificar...</p>
  </div>
  
  <!-- Insight 2 -->
  <div class="alert success">
    <strong>🚀 Excelente Rendimiento</strong>
    <p>Tu cartera ha generado un +11.91% de ganancia.</p>
  </div>
  
  <!-- Insight 3 -->
  <div class="alert warning">
    <strong>⚖️ Alta Concentración</strong>
    <p>Una de tus posiciones (CMG) representa el 34.87%...</p>
  </div>
</div>
```

---

## 📊 Diagrama Visual del Flujo Completo

```
┌──────────────────────────────────────────────────────────────────┐
│                    1. USUARIO ABRE PÁGINA                        │
│              http://localhost:4200/inversiones                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│          2. FRONTEND ANGULAR (investment.component.ts)           │
│                                                                  │
│  ngOnInit() {                                                    │
│    this.loadPositions()                                          │
│  }                                                               │
│                                                                  │
│  loadPositions() {                                               │
│    this.investmentService.getInvestmentsWithSummary()            │
│  }                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ HTTP GET /api/investments
                             │ Bearer Token
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│         3. BACKEND FASTAPI (routes/investments.py)               │
│                                                                  │
│  @router.get("/api/investments")                                 │
│  async def list_investments(current_user: User):                 │
│                                                                  │
│    # Validar JWT: current_user.id = uuid-456                     │
│                                                                  │
│    # A. Query DB                                                 │
│    investments = get_user_investments(db, uuid-456)              │
│                                                                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              4. POSTGRESQL DATABASE                              │
│                                                                  │
│  SELECT * FROM investments WHERE user_id = 'uuid-456'            │
│                                                                  │
│  RESULTADO (3 filas):                                            │
│  ┌────────┬────────┬──────┬────────┬────────────┐               │
│  │ symbol │ shares │ avg$ │ invest │ purchase   │               │
│  ├────────┼────────┼──────┼────────┼────────────┤               │
│  │ AMZN   │ 4.0    │ 190  │ $760   │ 2024-03-15 │               │
│  │ AAPL   │ 2.0    │ 200  │ $400   │ 2024-05-20 │               │
│  │ CMG    │ 10.0   │ 45   │ $450   │ 2023-11-10 │               │
│  └────────┴────────┴──────┴────────┴────────────┘               │
│                                                                  │
│  TOTAL INVERTIDO: $1,610                                         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ Return investments[]
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│      5. BACKEND (investment_service.enrich_investments)          │
│                                                                  │
│  symbols = ["AMZN", "AAPL", "CMG"]                               │
│                                                                  │
│  # B. Obtener cotizaciones actuales                              │
│  quotes = await alpha_vantage_service.get_multiple_quotes()      │
│                                                                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ 3 HTTP Calls
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              6. ALPHA VANTAGE API (3 llamadas)                   │
│                                                                  │
│  ┌─────────── AMZN ──────────┐                                   │
│  │ GET /query?function=       │                                  │
│  │   GLOBAL_QUOTE&symbol=AMZN │                                  │
│  │                            │                                  │
│  │ Response:                  │                                  │
│  │ {                          │                                  │
│  │   "05. price": "178.20",   │ ◄── PRECIO ACTUAL               │
│  │   "09. change": "0.90",    │ ◄── CAMBIO DEL DÍA              │
│  │   "10. change %": "0.51%"  │ ◄── % CAMBIO                    │
│  │ }                          │                                  │
│  └────────────────────────────┘                                  │
│                                                                  │
│  ┌─────────── AAPL ──────────┐                                   │
│  │ GET /query?function=       │                                  │
│  │   GLOBAL_QUOTE&symbol=AAPL │                                  │
│  │                            │                                  │
│  │ Response:                  │                                  │
│  │ {                          │                                  │
│  │   "05. price": "230.50",   │ ◄── PRECIO ACTUAL               │
│  │   "09. change": "3.25",    │ ◄── CAMBIO DEL DÍA              │
│  │   "10. change %": "1.43%"  │ ◄── % CAMBIO                    │
│  │ }                          │                                  │
│  └────────────────────────────┘                                  │
│                                                                  │
│  ┌──────────── CMG ──────────┐                                   │
│  │ GET /query?function=       │                                  │
│  │   GLOBAL_QUOTE&symbol=CMG  │                                  │
│  │                            │                                  │
│  │ Response:                  │                                  │
│  │ {                          │                                  │
│  │   "05. price": "62.80",    │ ◄── PRECIO ACTUAL               │
│  │   "09. change": "1.15",    │ ◄── CAMBIO DEL DÍA              │
│  │   "10. change %": "1.86%"  │ ◄── % CAMBIO                    │
│  │ }                          │                                  │
│  └────────────────────────────┘                                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ Parsed quotes
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│       7. BACKEND - CÁLCULOS (investment_service.py)              │
│                                                                  │
│  ┌────────────── AMZN ───────────────┐                           │
│  │ DB: 4 × $190 = $760 invertido     │                           │
│  │ Alpha: $178.20 actual             │                           │
│  │                                   │                           │
│  │ CÁLCULOS:                         │                           │
│  │ ├─ total_value: 4 × 178.20 = 712.80                           │
│  │ ├─ gain_loss: 712.80 - 760 = -47.20  ◄── PÉRDIDA             │
│  │ ├─ gain_%: -47.20/760 × 100 = -6.21%                          │
│  │ └─ day_change: 4 × 0.90 = 3.60                                │
│  └───────────────────────────────────┘                           │
│                                                                  │
│  ┌────────────── AAPL ───────────────┐                           │
│  │ DB: 2 × $200 = $400 invertido     │                           │
│  │ Alpha: $230.50 actual             │                           │
│  │                                   │                           │
│  │ CÁLCULOS:                         │                           │
│  │ ├─ total_value: 2 × 230.50 = 461.00                           │
│  │ ├─ gain_loss: 461 - 400 = 61.00  ◄── GANANCIA                │
│  │ ├─ gain_%: 61/400 × 100 = 15.25%                              │
│  │ └─ day_change: 2 × 3.25 = 6.50                                │
│  └───────────────────────────────────┘                           │
│                                                                  │
│  ┌────────────── CMG ────────────────┐                           │
│  │ DB: 10 × $45 = $450 invertido     │                           │
│  │ Alpha: $62.80 actual              │                           │
│  │                                   │                           │
│  │ CÁLCULOS:                         │                           │
│  │ ├─ total_value: 10 × 62.80 = 628.00                           │
│  │ ├─ gain_loss: 628 - 450 = 178.00 ◄── GANANCIA                │
│  │ ├─ gain_%: 178/450 × 100 = 39.56%                             │
│  │ └─ day_change: 10 × 1.15 = 11.50                              │
│  └───────────────────────────────────┘                           │
│                                                                  │
│  ┌──────── PORTFOLIO SUMMARY ────────┐                           │
│  │ total_value: 712.80 + 461 + 628 = 1,801.80                    │
│  │ total_invested: 760 + 400 + 450 = 1,610.00                    │
│  │ total_gain: 1,801.80 - 1,610 = +191.80  ◄── GANANCIA TOTAL   │
│  │ gain_%: 191.80/1,610 × 100 = +11.91%                          │
│  │ day_change: 3.60 + 6.50 + 11.50 = +21.60                      │
│  │ day_%: 21.60/1,780.20 × 100 = +1.21%                          │
│  │ positions: 3                                                  │
│  └───────────────────────────────────┘                           │
│                                                                  │
│  ┌──────────── INSIGHTS ─────────────┐                           │
│  │ 1. ⚠️  Baja Diversificación (3 < 5)                           │
│  │ 2. 🚀 Excelente Rendimiento (+11.91% > +10%)                  │
│  │ 3. ⚖️  Alta Concentración (CMG = 34.87% > 30%)                │
│  └───────────────────────────────────┘                           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ JSON Response
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│         8. HTTP RESPONSE → FRONTEND                              │
│                                                                  │
│  {                                                               │
│    "positions": [...3 EnrichedInvestment objects...],            │
│    "summary": {                                                  │
│      "total_value": 1801.80,                                     │
│      "total_gain_loss": 191.80,                                  │
│      "total_gain_loss_percent": 11.91,                           │
│      "day_change": 21.60,                                        │
│      ...                                                         │
│    },                                                            │
│    "insights": [...3 InvestmentInsight objects...]               │
│  }                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ Observable.subscribe()
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│       9. FRONTEND - ASIGNACIÓN (investment.component.ts)         │
│                                                                  │
│  this.positions.set(data.positions)                              │
│  this.summary.set(data.summary)                                  │
│  this.insights.set(data.insights)                                │
│  this.loading.set(false)                                         │
│                                                                  │
│  // NO hay lógica de negocio                                     │
│  // Solo asignación a signals                                    │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ Data Binding
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│         10. RENDERIZADO EN PANTALLA (HTML)                       │
│                                                                  │
│  ┌─────────────── KPI CARDS ──────────────┐                      │
│  │                                        │                      │
│  │  💰 Valor Total        📊 Rendimiento  │                      │
│  │     $1,801.80              +$191.80    │                      │
│  │     3 posiciones            +11.91%    │                      │
│  │                                        │                      │
│  │  ⚡ Ganancia del Día                   │                      │
│  │     +$21.60                            │                      │
│  │     +1.21%                             │                      │
│  └────────────────────────────────────────┘                      │
│                                                                  │
│  ┌───────────── TABLA DE POSICIONES ──────────────────────┐      │
│  │ Símbolo │ Acciones │ Precio$ │ Actual │ Valor  │ G/P   │      │
│  ├─────────┼──────────┼─────────┼────────┼────────┼───────┤      │
│  │ AMZN    │ 4.0      │ $190    │ $178   │ $712   │ -$47  │ 🔴   │
│  │ AAPL    │ 2.0      │ $200    │ $230   │ $461   │ +$61  │ 🟢   │
│  │ CMG     │ 10.0     │ $45     │ $62    │ $628   │ +$178 │ 🟢   │
│  └─────────┴──────────┴─────────┴────────┴────────┴───────┘      │
│                                                                  │
│  ┌──────────────── INSIGHTS ─────────────────┐                   │
│  │ ⚠️  Baja Diversificación                  │                   │
│  │    Solo 3 posiciones. Diversifica más...  │                   │
│  │                                           │                   │
│  │ 🚀 Excelente Rendimiento                  │                   │
│  │    Tu cartera ha generado +11.91%         │                   │
│  │                                           │                   │
│  │ ⚖️  Alta Concentración                    │                   │
│  │    CMG representa 34.87% de tu cartera    │                   │
│  └───────────────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## ⏱️ Tiempos de Ejecución Aproximados

1. Frontend → Backend: **10-20ms** (localhost)
2. Query PostgreSQL: **5-15ms** (3 filas)
3. Alpha Vantage calls (3x): **1500-2000ms** (500ms cada una, secuencial)
4. Cálculos backend: **2-5ms** (muy rápido)
5. JSON serialization: **5-10ms**
6. Backend → Frontend: **10-20ms**
7. Renderizado Angular: **20-50ms**

**TOTAL: ~1.6-2.2 segundos** (la mayoría es espera de Alpha Vantage)

---

## 🎯 Resumen del Ejemplo

**Portfolio de Juan Pérez:**

| Ticker | Acciones | Compra | Invertido | Actual | Valor | Ganancia | ROI |
|--------|----------|--------|-----------|--------|-------|----------|-----|
| AMZN | 4 | $190 | $760 | $178.20 | $712.80 | **-$47.20** | **-6.21%** 🔴 |
| AAPL | 2 | $200 | $400 | $230.50 | $461.00 | **+$61.00** | **+15.25%** 🟢 |
| CMG | 10 | $45 | $450 | $62.80 | $628.00 | **+$178.00** | **+39.56%** 🟢 |
| **TOTAL** | | | **$1,610** | | **$1,801.80** | **+$191.80** | **+11.91%** |

**Conclusión:** Aunque AMZN está en pérdida, CMG y AAPL compensan con ganancias significativas, resultando en un portfolio positivo del +11.91%.

---

**Fecha del ejemplo:** 2026-01-12  
**Precios son ilustrativos, basados en el flujo técnico real**
