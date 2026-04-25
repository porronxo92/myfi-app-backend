# Flujo de Datos: Alpha Vantage → Backend → Frontend

## 📊 Integración Completa con Alpha Vantage API

### 1️⃣ Alpha Vantage API Response (Raw)

**Endpoint:** `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=YOUR_KEY`

**Respuesta JSON:**
```json
{
    "Global Quote": {
        "01. symbol": "IBM",
        "02. open": "302.8200",
        "03. high": "312.2600",
        "04. low": "299.9600",
        "05. price": "312.1700",
        "06. volume": "3891827",
        "07. latest trading day": "2026-01-12",
        "08. previous close": "304.2200",
        "09. change": "7.9500",
        "10. change percent": "2.6132%"
    }
}
```

---

### 2️⃣ Backend - Parsing en `alpha_vantage.py`

**Archivo:** `backend/app/utils/alpha_vantage.py`

**Método:** `get_stock_quote(symbol: str)`

```python
async def get_stock_quote(self, symbol: str) -> Optional[StockQuote]:
    # 1. Llamada HTTP a Alpha Vantage
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol.upper(),
        "apikey": self.api_key
    }
    
    response = await client.get(self.base_url, params=params)
    data = response.json()
    
    # 2. Extraer "Global Quote"
    quote_data = data.get("Global Quote", {})
    
    # 3. Parsing de campos con nomenclatura Alpha Vantage
    price = float(quote_data.get("05. price", 0))
    change = float(quote_data.get("09. change", 0))
    change_percent_str = quote_data.get("10. change percent", "0%").replace("%", "")
    change_percent = float(change_percent_str)
    
    # 4. Crear objeto StockQuote normalizado
    return StockQuote(
        symbol=quote_data.get("01. symbol", symbol).upper(),
        name=symbol.upper(),
        price=price,                                                    # De "05. price"
        change=change,                                                  # De "09. change"
        change_percent=change_percent,                                  # De "10. change percent"
        high=float(quote_data.get("03. high", price)),                 # De "03. high"
        low=float(quote_data.get("04. low", price)),                   # De "04. low"
        open=float(quote_data.get("02. open", price)),                 # De "02. open"
        previous_close=float(quote_data.get("08. previous close")),    # De "08. previous close"
        volume=int(quote_data.get("06. volume", 0)),                   # De "06. volume"
        currency="USD",
        timestamp=datetime.utcnow()
    )
```

**Schema StockQuote (Pydantic):**
```python
class StockQuote(BaseModel):
    symbol: str              # "IBM"
    name: str                # "IBM"
    price: float             # 312.17
    change: float            # 7.95
    change_percent: float    # 2.6132
    high: float              # 312.26
    low: float               # 299.96
    open: float              # 302.82
    previous_close: float    # 304.22
    volume: int              # 3891827
    currency: str            # "USD"
    timestamp: datetime      # 2026-01-12T10:30:00Z
```

---

### 3️⃣ Backend - Enriquecimiento en `investment_service.py`

**Archivo:** `backend/app/services/investment_service.py`

**Método:** `enrich_investments(investments: List[Investment])`

```python
async def enrich_investments(investments: List[Investment]):
    # 1. Obtener cotizaciones de Alpha Vantage para todos los símbolos
    symbols = [inv.symbol for inv in investments]
    quotes = await alpha_vantage_service.get_multiple_quotes(symbols)
    
    enriched = []
    for investment in investments:
        quote = quotes.get(investment.symbol)  # StockQuote object
        
        # 2. Usar datos de Alpha Vantage
        current_price = quote.price              # De Alpha Vantage
        change_percent = quote.change_percent    # De Alpha Vantage
        day_change_per_share = quote.change      # De Alpha Vantage
        
        # 3. Combinar con datos del usuario (DB)
        shares = float(investment.shares)              # De DB
        avg_price = float(investment.average_price)    # De DB
        
        # 4. Calcular métricas
        total_value = shares * current_price
        total_invested = shares * avg_price
        total_gain_loss = total_value - total_invested
        total_gain_loss_percent = (total_gain_loss / total_invested * 100)
        day_change = shares * day_change_per_share
        
        # 5. Crear EnrichedInvestment
        enriched.append(EnrichedInvestment(
            # Datos originales de DB
            id=investment.id,
            symbol=investment.symbol,
            company_name=investment.company_name,
            shares=investment.shares,
            average_price=investment.average_price,
            purchase_date=investment.purchase_date,
            
            # Datos de Alpha Vantage
            current_price=current_price,        # ← De Alpha Vantage
            change_percent=change_percent,      # ← De Alpha Vantage
            
            # Cálculos derivados
            total_value=total_value,            # ← Calculado
            total_gain_loss=total_gain_loss,    # ← Calculado
            total_gain_loss_percent=total_gain_loss_percent,  # ← Calculado
            day_change=day_change               # ← Calculado
        ))
    
    return enriched
```

**Schema EnrichedInvestment:**
```python
class EnrichedInvestment(InvestmentResponse):
    # Datos de Alpha Vantage
    current_price: float          # Precio actual del mercado
    change_percent: float         # Cambio % del día
    
    # Cálculos del backend
    total_value: float            # shares × current_price
    total_gain_loss: float        # (current_price - avg_price) × shares
    total_gain_loss_percent: float  # gain_loss / invested × 100
    day_change: float             # shares × quote.change
```

---

### 4️⃣ Backend - Endpoint REST

**Archivo:** `backend/app/routes/investments.py`

**Endpoint:** `GET /api/investments`

```python
@router.get("", response_model=InvestmentsWithSummary)
async def list_investments(db: Session, current_user: User):
    # 1. Consultar posiciones del usuario en DB
    investments = investment_service.get_user_investments(db, current_user.id)
    
    # 2. Enriquecer con Alpha Vantage + cálculos
    enriched = await investment_service.enrich_investments(investments)
    
    # 3. Calcular resumen del portfolio
    summary = investment_service.calculate_portfolio_summary(enriched)
    
    # 4. Generar insights
    insights = investment_service.generate_insights(enriched, summary)
    
    # 5. Retornar todo junto
    return InvestmentsWithSummary(
        positions=enriched,
        summary=summary,
        insights=insights
    )
```

**Response JSON (enviada al frontend):**
```json
{
  "positions": [
    {
      "id": "uuid-123",
      "symbol": "IBM",
      "company_name": "International Business Machines",
      "shares": 50.0,
      "average_price": 280.00,
      "purchase_date": "2024-06-15",
      
      "current_price": 312.17,        // ← De Alpha Vantage
      "change_percent": 2.6132,       // ← De Alpha Vantage
      
      "total_value": 15608.50,        // ← Calculado: 50 × 312.17
      "total_gain_loss": 1608.50,     // ← Calculado: (312.17 - 280) × 50
      "total_gain_loss_percent": 11.49, // ← Calculado: 1608.50 / 14000 × 100
      "day_change": 397.50            // ← Calculado: 50 × 7.95
    }
  ],
  "summary": {
    "total_value": 15608.50,
    "total_invested": 14000.00,
    "total_gain_loss": 1608.50,
    "total_gain_loss_percent": 11.49,
    "day_change": 397.50,
    "day_change_percent": 2.61,
    "positions_count": 1
  },
  "insights": [
    {
      "type": "success",
      "title": "Excelente Rendimiento",
      "message": "Tu cartera ha generado un +11.49% de ganancia.",
      "icon": "🚀"
    }
  ]
}
```

---

### 5️⃣ Frontend - Servicio Angular

**Archivo:** `frontend/src/app/core/services/investment.service.ts`

```typescript
getInvestmentsWithSummary(): Observable<{
  positions: EnrichedPosition[];
  summary: PortfolioSummary;
  insights: InvestmentInsight[];
}> {
  // Una sola llamada HTTP al backend
  return this.http.get<{...}>(this.apiUrl);
  
  // El backend YA hizo:
  // ✅ Consulta a Alpha Vantage
  // ✅ Parsing de respuesta
  // ✅ Enriquecimiento de datos
  // ✅ Cálculos de ganancias
  // ✅ Resumen del portfolio
  // ✅ Generación de insights
}
```

---

### 6️⃣ Frontend - Componente Angular

**Archivo:** `frontend/src/app/features/investment/investment.component.ts`

```typescript
loadPositions(): void {
  this.investmentService.getInvestmentsWithSummary().subscribe({
    next: (data) => {
      // Datos YA vienen procesados
      this.positions.set(data.positions);  // EnrichedPosition[]
      this.summary.set(data.summary);      // PortfolioSummary
      this.insights.set(data.insights);    // InvestmentInsight[]
      
      // NO hay lógica de negocio aquí
      // Solo asignación y display
    }
  });
}
```

---

### 7️⃣ Frontend - Template HTML

**Archivo:** `frontend/src/app/features/investment/investment.component.html`

```html
<!-- KPI: Valor Total -->
<div class="kpi-card">
  <span class="kpi-value">
    {{ formatCurrency(summary().totalValue) }}
  </span>
  <!-- Muestra: $15,608.50 -->
</div>

<!-- Tabla de Posiciones -->
<tr *ngFor="let position of positions()">
  <td>{{ position.symbol }}</td>
  <!-- IBM -->
  
  <td>{{ position.companyName }}</td>
  <!-- International Business Machines -->
  
  <td>{{ position.shares }}</td>
  <!-- 50.0 -->
  
  <td>{{ formatCurrency(position.currentPrice) }}</td>
  <!-- $312.17 (de Alpha Vantage) -->
  
  <td [ngClass]="getValueClass(position.changePercent)">
    {{ formatPercent(position.changePercent) }}
  </td>
  <!-- +2.61% (de Alpha Vantage) -->
  
  <td>{{ formatCurrency(position.totalValue) }}</td>
  <!-- $15,608.50 (calculado en backend) -->
  
  <td [ngClass]="getValueClass(position.totalGainLoss)">
    {{ formatCurrency(position.totalGainLoss) }}
    ({{ formatPercent(position.totalGainLossPercent) }})
  </td>
  <!-- +$1,608.50 (+11.49%) (calculado en backend) -->
</tr>

<!-- Insights -->
<div *ngFor="let insight of insights()" 
     [ngClass]="'alert-' + insight.type">
  <strong>{{ insight.icon }} {{ insight.title }}</strong>
  <p>{{ insight.message }}</p>
</div>
<!-- 🚀 Excelente Rendimiento: Tu cartera ha generado un +11.49%... -->
```

---

## 📊 Mapeo de Campos Alpha Vantage → Frontend

| Alpha Vantage Field | Backend Parse | Frontend Display | Ubicación en UI |
|---------------------|---------------|------------------|-----------------|
| `"05. price"` | `current_price` | `{{ position.currentPrice \| currency }}` | Tabla posiciones |
| `"09. change"` | `change` → `day_change` | `{{ position.dayChange \| currency }}` | Cambio del día |
| `"10. change percent"` | `change_percent` | `{{ position.changePercent }}%` | Tendencia |
| `"03. high"` | `high` | - | (Disponible pero no usado) |
| `"04. low"` | `low` | - | (Disponible pero no usado) |
| `"02. open"` | `open` | - | (Disponible pero no usado) |
| `"08. previous close"` | `previous_close` | - | (Disponible pero no usado) |
| `"06. volume"` | `volume` | - | (Disponible pero no usado) |

---

## 🔄 Flujo Completo en Diagrama

```
┌─────────────────────────────────────────────────────────────────┐
│                   ALPHA VANTAGE API                             │
│  GET /query?function=GLOBAL_QUOTE&symbol=IBM&apikey=xxx         │
│                                                                 │
│  Response:                                                      │
│  {                                                              │
│    "Global Quote": {                                            │
│      "01. symbol": "IBM",                                       │
│      "05. price": "312.17",      ← PRECIO ACTUAL               │
│      "09. change": "7.95",       ← CAMBIO DEL DÍA              │
│      "10. change percent": "2.6132%" ← % CAMBIO                │
│    }                                                            │
│  }                                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ HTTP Request (async httpx)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND - alpha_vantage.py                         │
│  get_stock_quote(symbol: "IBM")                                 │
│                                                                 │
│  1. Parse JSON:                                                 │
│     price = float(data["Global Quote"]["05. price"])            │
│     change = float(data["Global Quote"]["09. change"])          │
│                                                                 │
│  2. Return StockQuote:                                          │
│     {                                                           │
│       symbol: "IBM",                                            │
│       price: 312.17,          ← Normalizado                    │
│       change: 7.95,           ← Normalizado                    │
│       change_percent: 2.6132  ← Sin "%"                        │
│     }                                                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Used by
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           BACKEND - investment_service.py                       │
│  enrich_investments(investments)                                │
│                                                                 │
│  User data (DB):                 Alpha Vantage:                 │
│  - symbol: "IBM"                 - current_price: 312.17        │
│  - shares: 50                    - change: 7.95                 │
│  - average_price: 280            - change_percent: 2.61         │
│                                                                 │
│  Calculations:                                                  │
│  total_value = 50 × 312.17 = 15,608.50                         │
│  total_gain_loss = (312.17 - 280) × 50 = 1,608.50             │
│  day_change = 50 × 7.95 = 397.50                               │
│                                                                 │
│  Return EnrichedInvestment:                                     │
│  {                                                              │
│    symbol: "IBM",                                               │
│    shares: 50,                                                  │
│    current_price: 312.17,        ← De Alpha Vantage            │
│    change_percent: 2.61,         ← De Alpha Vantage            │
│    total_value: 15608.50,        ← Calculado                   │
│    total_gain_loss: 1608.50,     ← Calculado                   │
│    day_change: 397.50            ← Calculado                   │
│  }                                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ HTTP Response (JSON)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│          FRONTEND - investment.service.ts                       │
│  getInvestmentsWithSummary()                                    │
│                                                                 │
│  return this.http.get('/api/investments')                       │
│                                                                 │
│  Response ya incluye TODO calculado                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Observable
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│         FRONTEND - investment.component.ts                      │
│  loadPositions()                                                │
│                                                                 │
│  this.positions.set(data.positions)                             │
│  this.summary.set(data.summary)                                 │
│                                                                 │
│  NO hay lógica de negocio - solo display                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Data Binding
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND - HTML Template                           │
│                                                                 │
│  <td>{{ position.currentPrice | currency }}</td>                │
│  → Muestra: $312.17                                             │
│                                                                 │
│  <td>{{ position.changePercent }}%</td>                         │
│  → Muestra: +2.61%                                              │
│                                                                 │
│  <td>{{ position.totalGainLoss | currency }}</td>               │
│  → Muestra: +$1,608.50                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ Conclusión

1. **Alpha Vantage** proporciona datos RAW en formato específico (`"01. symbol"`, `"05. price"`, etc.)
2. **Backend** parsea, normaliza, enriquece y calcula TODO
3. **Frontend** recibe datos listos para mostrar, sin lógica de negocio

**Ventajas de esta arquitectura:**
- ✅ API key NUNCA expuesta en frontend
- ✅ Lógica de negocio centralizada (una sola fuente de verdad)
- ✅ Frontend simple y rápido (solo display)
- ✅ Caché posible en backend (futuro con Redis)
- ✅ Testing más fácil (mock en backend, no en frontend)
- ✅ Mantenimiento simplificado (cambios en un solo lugar)

---

**Última actualización:** 2026-01-12
