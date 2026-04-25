# 📊 Endpoint: `/api/investments/quote` - Cotización en Tiempo Real

## Descripción

Endpoint para obtener la cotización en tiempo real de un ticker específico consultando directamente la API de Alpha Vantage (función `GLOBAL_QUOTE`).

Este endpoint es **independiente** del endpoint `/search` y está diseñado para:
- Actualizar precios en tiempo real de acciones ya almacenadas
- Refrescar la tabla de holdings sin hacer búsquedas
- Obtener datos completos de mercado (high, low, volume, etc.)

---

## 📍 Endpoint

```
GET /api/investments/quote
```

---

## 🔐 Autenticación

Requiere JWT token válido en el header:

```http
Authorization: Bearer {token}
```

---

## 📥 Parámetros de Query

| Parámetro | Tipo | Requerido | Descripción | Ejemplo |
|-----------|------|-----------|-------------|---------|
| `q` | string | ✅ Sí | Ticker de la acción (1-10 caracteres) | `ONON`, `AAPL`, `TSLA` |

---

## 📤 Respuesta Exitosa (200 OK)

### Formato JSON:

```json
{
  "symbol": "ONON",
  "name": "ONON",
  "price": 48.93,
  "change": -0.19,
  "changePercent": -0.39,
  "high": 50.29,
  "low": 47.89,
  "open": 48.50,
  "previousClose": 49.12,
  "volume": 4664389,
  "currency": "USD",
  "timestamp": "2026-01-12T00:00:00Z"
}
```

### Campos de la Respuesta:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `symbol` | string | Ticker de la acción |
| `name` | string | Nombre (igual al ticker en GLOBAL_QUOTE) |
| `price` | float | Precio actual (último precio negociado) |
| `change` | float | Cambio absoluto del día ($) |
| `changePercent` | float | Cambio porcentual del día (%) |
| `high` | float | Precio máximo del día |
| `low` | float | Precio mínimo del día |
| `open` | float | Precio de apertura |
| `previousClose` | float | Precio de cierre anterior |
| `volume` | integer | Volumen de transacciones |
| `currency` | string | Moneda (siempre "USD") |
| `timestamp` | datetime | Fecha/hora de la cotización |

---

## ❌ Respuestas de Error

### 404 Not Found

No se encontró cotización para el ticker:

```json
{
  "detail": "No se encontró cotización para el ticker 'INVALID'"
}
```

### 401 Unauthorized

Token JWT inválido o expirado:

```json
{
  "detail": "Could not validate credentials"
}
```

### 429 Too Many Requests

Rate limit excedido:

```json
{
  "detail": "Too many requests"
}
```

---

## 📚 Ejemplos de Uso

### cURL

```bash
curl -X GET "http://localhost:8000/api/investments/quote?q=ONON" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### JavaScript (Fetch)

```javascript
const response = await fetch('http://localhost:8000/api/investments/quote?q=ONON', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const quote = await response.json();
console.log(`${quote.symbol}: $${quote.price} (${quote.changePercent}%)`);
```

### TypeScript (Angular Service)

```typescript
getStockQuote(ticker: string): Observable<StockQuote> {
  const params = new HttpParams().set('q', ticker.toUpperCase());
  return this.http.get<StockQuote>(`${this.apiUrl}/quote`, { params });
}

// Uso:
this.investmentService.getStockQuote('ONON').subscribe(quote => {
  console.log(`Current price: $${quote.price}`);
});
```

### Python (httpx)

```python
import httpx

async def get_quote(ticker: str, token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/investments/quote",
            params={"q": ticker},
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()

# Uso:
quote = await get_quote("ONON", "your_jwt_token")
print(f"{quote['symbol']}: ${quote['price']}")
```

---

## 🔄 Flujo de Datos

```
┌─────────────┐
│  Frontend   │
│  (Angular)  │
└──────┬──────┘
       │ GET /api/investments/quote?q=ONON
       │ Authorization: Bearer {token}
       ▼
┌─────────────────────────────────────────┐
│  Backend (FastAPI)                      │
│  routes/investments.py                  │
│                                         │
│  1. ✅ Validar JWT token                │
│  2. ✅ Verificar rate limit             │
│  3. ✅ Llamar alpha_vantage_service     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Alpha Vantage Service                  │
│  utils/alpha_vantage.py                 │
│                                         │
│  get_stock_quote(symbol)                │
└──────────────┬──────────────────────────┘
               │
               │ HTTPS Request
               ▼
┌─────────────────────────────────────────┐
│  Alpha Vantage API                      │
│  https://www.alphavantage.co/query      │
│                                         │
│  function=GLOBAL_QUOTE                  │
│  symbol=ONON                            │
│  apikey={API_KEY}                       │
└──────────────┬──────────────────────────┘
               │
               │ JSON Response:
               │ {
               │   "Global Quote": {
               │     "01. symbol": "ONON",
               │     "05. price": "48.9300",
               │     "09. change": "-0.1900",
               │     "10. change percent": "-0.3868%",
               │     ...
               │   }
               │ }
               ▼
┌─────────────────────────────────────────┐
│  Backend - Parseo y Mapeo               │
│                                         │
│  • Extrae "Global Quote"                │
│  • Mapea "05. price" → price            │
│  • Mapea "09. change" → change          │
│  • Mapea "10. change percent" → %       │
│  • Remueve "%" del string               │
│  • Convierte a float/int                │
│  • Crea StockQuote schema               │
└──────────────┬──────────────────────────┘
               │
               │ StockQuote {
               │   symbol: "ONON",
               │   price: 48.93,
               │   change: -0.19,
               │   changePercent: -0.39,
               │   ...
               │ }
               ▼
┌─────────────────────────────────────────┐
│  Frontend - Actualización UI            │
│                                         │
│  • Actualiza tabla de holdings          │
│  • Muestra precio en rojo/verde         │
│  • Calcula valor actual de posición     │
│  • Recalcula P&G no realizadas          │
└─────────────────────────────────────────┘
```

---

## 🎯 Diferencias con `/search`

| Aspecto | `/search` | `/quote` |
|---------|-----------|----------|
| **Función Alpha Vantage** | `SYMBOL_SEARCH` | `GLOBAL_QUOTE` |
| **Propósito** | Buscar tickers por nombre/símbolo | Obtener cotización actual |
| **Input** | Texto parcial ("app", "tesla") | Ticker exacto ("AAPL", "TSLA") |
| **Output** | Lista de coincidencias | Cotización única |
| **Cuándo usar** | Barra de búsqueda | Actualizar precios |
| **Datos devueltos** | Symbol, name, type, region | Price, change, volume, high/low |
| **Frecuencia recomendada** | Por búsqueda manual | Cada 5-15 minutos (auto-refresh) |

---

## ⚙️ Configuración

### Variables de Entorno (`.env`)

```env
ALPHA_VANTAGE_API_KEY=TU_API_KEY_AQUI
ALPHA_VANTAGE_BASE_URL=https://www.alphavantage.co/query
```

### Obtener API Key

1. Visita: https://www.alphavantage.co/support/#api-key
2. Ingresa tu email
3. Recibes la key instantáneamente (< 20 segundos)

### Rate Limits (Plan Gratuito)

- **5 requests/minuto**
- **500 requests/día**

💡 **Recomendación**: Implementar cache en frontend (5-15 min TTL) para no consumir todo el rate limit.

---

## 🧪 Testing

### Test Manual (Backend)

```bash
cd backend
python test_quote_endpoint.py
```

### Test con cURL (requiere token)

```bash
# 1. Login y obtener token
TOKEN=$(curl -X POST "http://localhost:8000/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | jq -r '.access_token')

# 2. Consultar cotización
curl "http://localhost:8000/api/investments/quote?q=ONON" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Test desde Frontend

```typescript
// En investment.component.ts
testQuoteEndpoint() {
  this.investmentService.getStockQuote('ONON').subscribe({
    next: (quote) => {
      console.log('✅ Quote received:', quote);
      console.log(`${quote.symbol}: $${quote.price} (${quote.changePercent}%)`);
    },
    error: (err) => {
      console.error('❌ Error:', err);
    }
  });
}
```

---

## 🚀 Casos de Uso

### 1. Auto-refresh de Tabla

```typescript
// Actualizar precios cada 10 minutos
setInterval(() => {
  this.positions().forEach(position => {
    this.investmentService.getStockQuote(position.symbol).subscribe(quote => {
      position.currentPrice = quote.price;
      position.changePercent = quote.changePercent;
      // Recalcular valores...
    });
  });
}, 10 * 60 * 1000); // 10 minutos
```

### 2. Botón de Refresh Manual

```html
<button (click)="refreshPrices()">
  🔄 Actualizar Precios
</button>
```

```typescript
refreshPrices() {
  this.loading.set(true);
  this.positions().forEach(position => {
    this.investmentService.getStockQuote(position.symbol).subscribe({
      next: (quote) => {
        // Actualizar precio...
      },
      complete: () => this.loading.set(false)
    });
  });
}
```

### 3. Pre-visualización al Agregar

```typescript
// Mostrar precio actual antes de comprar
selectStock(stock: StockSearchResult) {
  this.investmentService.getStockQuote(stock.symbol).subscribe(quote => {
    this.selectedStock.set(stock);
    this.currentPrice.set(quote.price);
    // Pre-llenar formulario con precio actual
    this.newPosition.update(pos => ({
      ...pos,
      averagePrice: quote.price
    }));
  });
}
```

---

## 📊 Ejemplo de Respuesta Real

### Request

```http
GET /api/investments/quote?q=ONON HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Response (200 OK)

```json
{
  "symbol": "ONON",
  "name": "ONON",
  "price": 48.93,
  "change": -0.19,
  "changePercent": -0.3868,
  "high": 50.29,
  "low": 47.89,
  "open": 48.5,
  "previousClose": 49.12,
  "volume": 4664389,
  "currency": "USD",
  "timestamp": "2026-01-12T16:00:00Z"
}
```

### Interpretación

- **ONON** cotiza a **$48.93**
- Bajó **$0.19** (-0.39%) respecto al cierre anterior ($49.12)
- Rango del día: **$47.89 - $50.29**
- Volumen: **4.6M acciones** negociadas
- Datos al cierre del **12 de enero de 2026**

---

## 🔒 Seguridad

- ✅ Requiere autenticación JWT
- ✅ Rate limiting aplicado
- ✅ API key en `.env` (no hardcoded)
- ✅ Validación de input (ticker 1-10 chars)
- ✅ Manejo de errores robusto
- ✅ Logs de auditoría

---

## 📝 Notas Importantes

1. **No confundir con `/search`**: Este endpoint obtiene cotización, no busca tickers
2. **Ticker exacto requerido**: Debe ser el símbolo exacto (ej: "AAPL", no "apple")
3. **Rate limits**: Respetar 5 req/min para evitar mock data fallback
4. **Horario de mercado**: Datos más actualizados durante horario de bolsa (9:30-16:00 EST)
5. **Caché recomendado**: No consultar en cada render, cachear 5-15 minutos

---

**Fecha de creación**: 2026-01-13  
**Versión**: 1.0  
**Autor**: Sistema de Inversiones AppFinanzas
