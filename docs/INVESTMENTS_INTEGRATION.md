# Integración del Módulo de Inversiones Bursátiles

## Resumen de Implementación

Se ha completado la implementación completa del módulo de inversiones bursátiles siguiendo la arquitectura establecida: **TODO el procesamiento, cálculos y llamadas a APIs externas se realizan en el backend**, mientras que el frontend es únicamente un escaparate de datos.

---

## 📊 Arquitectura

### Flujo de Datos
```
Usuario (Frontend Angular)
       ↓
   [REST API]
       ↓
Backend FastAPI
   ├── Autenticación JWT
   ├── Rate Limiting
   ├── Servicio Investment
   │   ├── CRUD Operaciones
   │   ├── Enriquecimiento de datos
   │   ├── Cálculo de métricas
   │   └── Generación de insights
   └── Servicio Alpha Vantage
       ├── Búsqueda de acciones
       ├── Cotizaciones en tiempo real
       └── Mock data (fallback)
       ↓
   PostgreSQL
```

---

## 🗂️ Componentes del Backend

### 1. Modelo ORM (SQLAlchemy)
**Archivo:** `backend/app/models/investment.py`

```python
class Investment(Base):
    __tablename__ = "investments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    symbol = Column(String(10), nullable=False)
    company_name = Column(String(255), nullable=False)
    shares = Column(Numeric(10, 4), nullable=False)
    average_price = Column(Numeric(10, 2), nullable=False)
    purchase_date = Column(Date, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Características:**
- Usa UUID para `id` y `user_id` (compatibilidad con esquema existente)
- Tipo `Numeric` para precisión en valores monetarios
- Relación con `User` con cascade delete

---

### 2. Schemas Pydantic
**Archivo:** `backend/app/schemas/investment.py`

**Esquemas Principales:**
- `InvestmentBase`: Campos base con validadores
- `InvestmentCreate`: Request para crear posición
- `InvestmentUpdate`: Request para actualizar (campos opcionales)
- `InvestmentResponse`: Respuesta del ORM
- `StockQuote`: Datos de cotización de Alpha Vantage
- `StockSearchResult`: Resultados de búsqueda
- `EnrichedInvestment`: **CRÍTICO** - Posición + datos de mercado + cálculos
- `PortfolioSummary`: **CRÍTICO** - Resumen agregado del portfolio
- `InvestmentInsight`: Recomendaciones generadas
- `InvestmentsWithSummary`: **RESPUESTA PRINCIPAL** - Combina todo

**Validadores:**
```python
@field_validator('symbol')
def symbol_uppercase(cls, v: str) -> str:
    return v.upper().strip()

@field_validator('shares', 'average_price')
def round_decimals(cls, v: Decimal) -> Decimal:
    return v.quantize(Decimal('0.0001'))
```

---

### 3. Servicio Alpha Vantage
**Archivo:** `backend/app/utils/alpha_vantage.py`

**Métodos:**
```python
async def search_stocks(keywords: str) -> List[StockSearchResult]
    # Función: SYMBOL_SEARCH
    # Retorna: Top 10 resultados
    # Fallback: Mock data de 8 acciones populares

async def get_stock_quote(symbol: str) -> Optional[StockQuote]
    # Función: GLOBAL_QUOTE
    # Retorna: Precio actual, cambio, volumen, etc.
    # Fallback: Mock data con precios realistas

async def get_multiple_quotes(symbols: List[str]) -> Dict[str, StockQuote]
    # Batch retrieval
    # Optimizado para enriquecer múltiples posiciones
```

**Configuración requerida en `.env`:**
```env
ALPHA_VANTAGE_API_KEY=IP8B1NDDPRG8F5T3
ALPHA_VANTAGE_BASE_URL=https://www.alphavantage.co/query
```

**Mock Data (desarrollo/fallback):**
- AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX
- Precios realistas con variaciones

---

### 4. Servicio de Lógica de Negocio
**Archivo:** `backend/app/services/investment_service.py`

**CRUD Operations:**
- `get_user_investments(db, user_id)`: Consulta todas las posiciones
- `get_investment_by_id(db, investment_id, user_id)`: Una posición con validación de ownership
- `create_investment(db, data, user_id)`: Crear nueva
- `update_investment(db, id, data, user_id)`: PATCH update
- `delete_investment(db, id, user_id)`: Eliminar

**Procesamiento de Datos (CRÍTICO):**

**`enrich_investments(investments: List[Investment])`**
1. Obtiene cotizaciones actuales de Alpha Vantage
2. Para cada posición calcula:
   - `current_price`: Precio actual de mercado
   - `total_value` = shares × current_price
   - `total_gain_loss` = (current_price - average_price) × shares
   - `total_gain_loss_percent` = ((current_price - average_price) / average_price) × 100
   - `day_change` = shares × change_today

**`calculate_portfolio_summary(enriched_positions)`**
Agrega todas las posiciones:
```python
total_value = Σ(position.total_value)
total_invested = Σ(position.shares × position.average_price)
total_gain_loss = total_value - total_invested
total_gain_loss_percent = (total_gain_loss / total_invested) × 100
day_change = Σ(position.day_change)
day_change_percent = (day_change / (total_value - day_change)) × 100
positions_count = len(positions)
```

**`generate_insights(enriched_positions, summary)`**
Genera recomendaciones basadas en:
1. **Diversificación**: Alerta si < 5 posiciones
2. **Rendimiento**: Celebra si > +10%, alerta si < -10%
3. **Concentración**: Alerta si una posición > 30% del portfolio

---

### 5. Endpoints REST
**Archivo:** `backend/app/routes/investments.py`

**Todos los endpoints requieren autenticación y rate limiting**

#### `GET /api/investments/search?q={query}`
Buscar acciones por símbolo o nombre de empresa.

**Query Parameters:**
- `q` (required): Texto de búsqueda (mínimo 2 caracteres)

**Response:**
```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "type": "Equity",
    "region": "United States",
    "currency": "USD"
  }
]
```

---

#### `GET /api/investments` ⭐ **ENDPOINT PRINCIPAL**
Obtener todas las inversiones del usuario con datos enriquecidos, resumen y recomendaciones.

**Response:**
```json
{
  "positions": [
    {
      "id": "uuid-123",
      "user_id": "uuid-456",
      "symbol": "AAPL",
      "company_name": "Apple Inc.",
      "shares": 50.0,
      "average_price": 165.50,
      "purchase_date": "2024-01-15",
      "notes": "Long term investment",
      "current_price": 178.50,
      "change_percent": 1.33,
      "total_value": 8925.00,
      "total_gain_loss": 650.00,
      "total_gain_loss_percent": 7.85,
      "day_change": 117.50
    }
  ],
  "summary": {
    "total_value": 45320.00,
    "total_invested": 42000.00,
    "total_gain_loss": 3320.00,
    "total_gain_loss_percent": 7.90,
    "day_change": 245.00,
    "day_change_percent": 0.54,
    "positions_count": 4
  },
  "insights": [
    {
      "type": "warning",
      "title": "Baja Diversificación",
      "message": "Tienes solo 4 posición(es). Considera diversificar...",
      "icon": "⚠️"
    }
  ]
}
```

**Características:**
- Una sola llamada retorna TODO lo necesario
- Datos ya enriquecidos con precios actuales
- Cálculos ya realizados
- Insights ya generados

---

#### `GET /api/investments/{id}`
Obtener una inversión específica enriquecida.

**Response:**
```json
{
  "id": "uuid-123",
  "symbol": "AAPL",
  "current_price": 178.50,
  "total_value": 8925.00,
  ...
}
```

---

#### `POST /api/investments`
Crear nueva posición.

**Request:**
```json
{
  "symbol": "TSLA",
  "company_name": "Tesla Inc.",
  "shares": 15.5,
  "average_price": 250.00,
  "purchase_date": "2024-12-30",
  "notes": "High risk/reward"
}
```

**Response:** `201 Created` con el objeto creado

---

#### `PATCH /api/investments/{id}`
Actualizar posición existente (campos opcionales).

**Request:**
```json
{
  "shares": 20.0,
  "notes": "Increased position"
}
```

**Response:** `200 OK` con objeto actualizado

---

#### `DELETE /api/investments/{id}`
Eliminar posición.

**Response:** `204 No Content`

---

## 🎨 Integración Frontend

### Servicio Simplificado
**Archivo:** `frontend/src/app/core/services/investment.service.ts`

**ANTES (duplicaba lógica):**
```typescript
searchStocks() → ❌ Llamaba directamente a Alpha Vantage
getStockQuote() → ❌ Llamaba directamente a Alpha Vantage  
enrichPositions() → ❌ Calculaba gains/losses localmente
```

**AHORA (thin client):**
```typescript
searchStocks(query: string): Observable<StockSearchResult[]>
  → GET /api/investments/search?q={query}

getInvestmentsWithSummary(): Observable<{positions, summary, insights}>
  → GET /api/investments
  → Retorna TODO ya calculado

getInvestment(id: string): Observable<EnrichedPosition>
  → GET /api/investments/{id}

addPosition(request): Observable<any>
  → POST /api/investments

updatePosition(id, request): Observable<any>
  → PATCH /api/investments/{id}

deletePosition(id): Observable<void>
  → DELETE /api/investments/{id}
```

**Eliminado:**
- Toda lógica de llamadas a Alpha Vantage
- Método `enrichPositions()` (backend lo hace)
- Generación de mock data
- Cálculos de gains/losses

---

### Componente Actualizado
**Archivo:** `frontend/src/app/features/investment/investment.component.ts`

**ANTES:**
```typescript
portfolioSummary = computed(() => {
  // ❌ Calculaba summary localmente
});

insights = computed(() => {
  // ❌ Generaba insights localmente
});

loadPositions() {
  getUserPositions()
    .pipe(switchMap(positions => enrichPositions(positions)))
    // ❌ Dos llamadas, enriquecimiento local
}
```

**AHORA:**
```typescript
summary = signal<PortfolioSummary>({...});
insights = signal<InvestmentInsight[]>([]);

loadPositions() {
  this.investmentService.getInvestmentsWithSummary().subscribe({
    next: (data) => {
      this.positions.set(data.positions);
      this.summary.set(data.summary);       // ✅ Del backend
      this.insights.set(data.insights);     // ✅ Del backend
    }
  });
}
```

**Ventajas:**
- Una sola llamada HTTP
- Sin duplicación de lógica
- Datos siempre consistentes con backend
- Cálculos garantizados correctos

---

## 🔐 Seguridad

### Autenticación
Todos los endpoints de `/api/investments/*` requieren:
```python
current_user: User = Depends(get_current_user)
```

### Rate Limiting
Protección contra abuso:
```python
_: None = Depends(check_rate_limit)
```
- 100 requests por ventana de 60 segundos (configurable)

### Validación
- Pydantic valida todos los inputs
- Símbolos convertidos a uppercase
- Decimales redondeados correctamente
- Fechas validadas

### Ownership
Todas las operaciones validan que el user_id de la inversión coincida con el usuario autenticado:
```python
if investment.user_id != current_user.id:
    raise HTTPException(status_code=404, detail="Investment not found")
```

---

## 🧪 Testing

### Tests Sugeridos

**Backend:**
```bash
# Endpoint de búsqueda
curl -H "Authorization: Bearer {token}" \
  "http://localhost:8000/api/investments/search?q=apple"

# Listar inversiones enriquecidas
curl -H "Authorization: Bearer {token}" \
  "http://localhost:8000/api/investments"

# Crear inversión
curl -X POST \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"TSLA","company_name":"Tesla Inc.","shares":10,"average_price":250,"purchase_date":"2024-12-30"}' \
  "http://localhost:8000/api/investments"
```

**Frontend:**
```typescript
// Test búsqueda
investmentService.searchStocks('apple').subscribe(console.log);

// Test carga completa
investmentService.getInvestmentsWithSummary().subscribe(data => {
  console.log('Positions:', data.positions);
  console.log('Summary:', data.summary);
  console.log('Insights:', data.insights);
});
```

---

## 📝 Modelos de Datos

### Frontend
**Archivo:** `frontend/src/app/core/models/investment.model.ts`

**Cambios importantes:**
- `UserPosition.id`: `number` → `string` (UUID)
- `UserPosition.userId`: `number` → `string` (UUID)

**Interfaces principales:**
- `StockSearchResult`: Resultado de búsqueda
- `UserPosition`: Posición básica del usuario
- `EnrichedPosition`: Posición + datos de mercado calculados
- `PortfolioSummary`: Resumen del portfolio
- `InvestmentInsight`: Recomendación/alerta
- `AddPositionRequest`: Request para crear
- `UpdatePositionRequest`: Request para actualizar

---

## 🚀 Despliegue

### Variables de Entorno Requeridas
```env
# Backend .env
ALPHA_VANTAGE_API_KEY=your_api_key_here
ALPHA_VANTAGE_BASE_URL=https://www.alphavantage.co/query

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/app_finance

# JWT
JWT_SECRET=your_secret_key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### Frontend Environment
```typescript
// frontend/src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api'
};
```

---

## 📊 Flujo de Usuario

1. **Usuario busca una acción**
   - Frontend: Input en search bar
   - Backend: `GET /api/investments/search?q=tesla`
   - Alpha Vantage: API call o mock fallback
   - Response: Lista de resultados

2. **Usuario selecciona acción y agrega posición**
   - Frontend: Modal con formulario (shares, price, date)
   - Backend: `POST /api/investments`
   - PostgreSQL: Insert en tabla investments
   - Response: Posición creada

3. **Usuario ve su portfolio**
   - Frontend: `loadPositions()`
   - Backend: `GET /api/investments`
   - Backend procesa:
     - Consulta DB para posiciones del usuario
     - Llama Alpha Vantage para cotizaciones actuales
     - Enriquece cada posición con cálculos
     - Agrega summary del portfolio
     - Genera insights
   - Response: `InvestmentsWithSummary` completo
   - Frontend: Muestra KPIs, tabla de posiciones, insights

4. **Usuario actualiza/elimina posición**
   - Frontend: `PATCH` o `DELETE /api/investments/{id}`
   - Backend: Valida ownership y actualiza DB
   - Frontend: Recarga portfolio

---

## 🔄 Próximas Mejoras Sugeridas

1. **Caché de cotizaciones**
   - Redis para almacenar quotes por 1-5 minutos
   - Reducir llamadas a Alpha Vantage (límite 5/min en plan gratuito)

2. **Histórico de precios**
   - Endpoint para gráficas de rendimiento temporal
   - Alpha Vantage TIME_SERIES_DAILY

3. **Alertas de precio**
   - Notificar cuando una acción alcanza cierto precio
   - WebSocket o push notifications

4. **Comparación con índices**
   - S&P 500, NASDAQ como benchmarks
   - Calcular alpha/beta del portfolio

5. **Exportación de datos**
   - PDF/Excel con reporte del portfolio
   - Útil para declaraciones fiscales

6. **Dividendos**
   - Tracking de dividendos recibidos
   - Cálculo de yield

---

## ✅ Checklist de Implementación Completada

- [x] Modelo ORM Investment con UUID
- [x] Relación Investment-User con cascade
- [x] Schemas Pydantic completos
- [x] Servicio Alpha Vantage con mock fallback
- [x] Servicio de lógica de negocio con todos los cálculos
- [x] Enriquecimiento de posiciones con datos de mercado
- [x] Cálculo de portfolio summary
- [x] Generación de insights automáticos
- [x] 5 endpoints REST (search, list, get, create, update, delete)
- [x] Autenticación y rate limiting
- [x] Frontend service simplificado
- [x] Frontend component actualizado
- [x] Modelos del frontend actualizados (UUID)
- [x] Template usando summary() del backend
- [x] Router registrado en main.py

---

## 📚 Documentación de Referencia

- **Alpha Vantage API**: https://www.alphavantage.co/documentation/
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Pydantic**: https://docs.pydantic.dev/

---

## 🆘 Troubleshooting

### Error: "Investment not found" al actualizar/eliminar
**Causa:** El user_id no coincide o el ID es incorrecto  
**Solución:** Verificar que el token JWT es del usuario correcto

### Error: "Rate limit exceeded"
**Causa:** Demasiadas peticiones en poco tiempo  
**Solución:** Esperar 60 segundos o aumentar límite en config

### Error: "Alpha Vantage API error"
**Causa:** API key inválida o límite de llamadas excedido  
**Solución:** Sistema usa mock data automáticamente como fallback

### Frontend muestra posiciones sin precios actuales
**Causa:** Error en Alpha Vantage service  
**Solución:** Revisar logs del backend, mock data debería funcionar

---

**Autor:** Implementación completada el 2024-12-30  
**Versión:** 1.0.0  
**Backend:** FastAPI + PostgreSQL + Alpha Vantage API  
**Frontend:** Angular 21 + TypeScript + RxJS
