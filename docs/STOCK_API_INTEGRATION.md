# Integración de APIs de Stocks con Finnhub + Alpha Vantage Fallback

## 🎯 Objetivo

Implementar un sistema robusto de consulta de datos bursátiles con **dos niveles de fallback automático**:

1. **Finnhub** (Prioridad 1) - 60 llamadas/minuto
2. **Alpha Vantage** (Fallback) - 25 llamadas/día

Esto garantiza alta disponibilidad y mejor experiencia de usuario en el módulo de inversiones.

---

## 🏗️ Arquitectura del Sistema

```
Frontend solicita datos de stock
        ↓
Backend: StockAPIService
        ↓
    ┌───────────────────┐
    │ 1. Intentar       │
    │    FINNHUB        │
    │ (60 calls/min)    │
    └───────────────────┘
        ↓
    ¿Éxito?
        │
    ┌───┴───┐
   SÍ       NO
    │        │
    │        ↓
    │   ┌───────────────────┐
    │   │ 2. Intentar       │
    │   │    ALPHA VANTAGE  │
    │   │ (25 calls/day)    │
    │   └───────────────────┘
    │        │
    │        ↓
    │    ¿Éxito?
    │        │
    └────────┴──────┐
                    │
                    ↓
            Devolver Datos
                o Error
```

---

## 📋 Configuración Inicial

### Paso 1: Variables de Entorno

En `backend/.env`:

```bash
# Finnhub API (Prioridad 1)
FINNHUB_API_KEY=your_finnhub_api_key_here
FINNHUB_MAX_CALLS_PER_MINUTE=60

# Alpha Vantage API (Fallback)
ALPHA_VANTAGE_API_KEY=KRJ5LLT4OZ0E0S8K
ALPHA_VANTAGE_BASE_URL=https://www.alphavantage.co/query
ALPHA_VANTAGE_MAX_CALLS_PER_DAY=25
```

### Paso 2: Obtener API Keys

- **Finnhub**: https://finnhub.io/ (Sign up for free)
- **Alpha Vantage**: https://www.alphavantage.co/support/#api-key

---

## 🔧 Estructura del Backend

### 1. Stock API Service

**Archivo**: `backend/app/services/stock_api_service.py`

```python
class StockAPIService:
    """Servicio unificado para APIs de stocks con fallback automático"""
    
    async def search_stocks(keywords: str) -> List[StockSearchResult]
    async def get_stock_quote(symbol: str) -> Optional[StockQuote]
    async def get_multiple_quotes(symbols: List[str]) -> Dict[str, Optional[StockQuote]]
    
    def get_api_status() -> Dict  # Para debugging
```

**Características**:
- ✅ Intenta Finnhub primero
- ✅ Fallback automático a Alpha Vantage
- ✅ Tracking de rate limits
- ✅ Respuestas normalizadas
- ✅ Logging detallado

### 2. Rutas de Inversiones Actualizadas

**Archivo**: `backend/app/routes/investments.py`

#### Endpoints principales:

```bash
GET /api/investments/search?q=AAPL
  └─ Buscar acciones con Finnhub + fallback

GET /api/investments/quote?q=AAPL
  └─ Obtener cotización con Finnhub + fallback

GET /api/investments/api-status
  └─ Ver estado de las APIs (debugging)
```

---

## 🌐 Frontend

### Actualización del Servicio

**Archivo**: `frontend/src/app/core/services/investment.service.ts`

```typescript
searchStocks(query: string): Observable<StockSearchResult[]>
getStockQuote(ticker: string): Observable<StockQuote>
```

El frontend continúa usando los mismos endpoints - la lógica de fallback está completamente en el backend.

---

## 📊 Rate Limiting

### Finnhub (Prioridad 1)
- **Límite**: 60 llamadas/minuto (API gratuita)
- **Ventaja**: Alta frecuencia, datos más frescos
- **Se usa cuando**: Disponible

### Alpha Vantage (Fallback)
- **Límite**: 25 llamadas/día (API gratuita)
- **Ventaja**: Información más completa cuando está disponible
- **Se usa cuando**: Finnhub falla o no está configurado

### Implementación

```python
# Tracking automático
self.finnhub_calls: List[datetime]      # Últimas 60 llamadas en 1 minuto
self.alpha_vantage_calls: List[datetime] # Últimas 25 llamadas en 24 horas

# Verificación antes de llamar
if _can_call_finnhub():  # True si < 60 llamadas en último minuto
    quote = await _get_quote_finnhub(symbol)
```

---

## 🔍 Respuestas Normalizadas

### Búsqueda de Stocks

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "type": "Common Stock",
  "region": "US",
  "currency": "USD"
}
```

### Cotización

```json
{
  "symbol": "AAPL",
  "name": "AAPL",
  "price": 175.50,
  "change": 2.35,
  "change_percent": 1.36,
  "high": 176.20,
  "low": 174.80,
  "open": 174.95,
  "previous_close": 173.15,
  "volume": 42563891,
  "currency": "USD",
  "timestamp": "2026-01-13T20:00:00"
}
```

---

## 🛠️ Debugging y Monitoreo

### Ver Estado de APIs

```bash
GET /api/investments/api-status
Authorization: Bearer {token}
```

**Respuesta**:

```json
{
  "finnhub": {
    "configured": true,
    "available": true,
    "calls_last_minute": 12,
    "limit_per_minute": 60,
    "remaining": 48
  },
  "alpha_vantage": {
    "configured": true,
    "available": true,
    "calls_last_day": 5,
    "limit_per_day": 25,
    "remaining": 20
  },
  "timestamp": "2026-01-13T20:00:00"
}
```

### Logs

Los logs muestran claramente qué API se utilizó:

```
[SEARCH] Intentando con Finnhub: AAPL
[SEARCH] ✓ Finnhub devolvió 1 resultados

[QUOTE] Intentando con Finnhub: AAPL
[QUOTE] ✓ Finnhub devolvió cotización para AAPL

[QUOTE] Fallback a Alpha Vantage: XYZ
[QUOTE] ✓ Alpha Vantage devolvió cotización para XYZ
```

---

## 🚀 Mejoras Futuras

### Corto Plazo
- [ ] Implementar caché con TTL de 1-5 minutos para quotes
- [ ] WebSocket para cotizaciones en tiempo real
- [ ] Alertas cuando una API alcanza límites

### Mediano Plazo
- [ ] Redis para compartir rate limiting entre instancias
- [ ] Tercera API de fallback (ej: yfinance, Polygon.io)
- [ ] Análisis histórico de precios

### Largo Plazo
- [ ] Migraciones a APIs premium si las gratuitas no son suficientes
- [ ] Machine learning para predicción de precios
- [ ] Comparativa de performance entre APIs

---

## ✅ Checklist de Verificación

### Backend
- ✅ Instalar dependencias: `pip install finnhub-client requests httpx`
- ✅ Actualizar `.env` con claves de API
- ✅ Crear `services/stock_api_service.py`
- ✅ Actualizar `routes/investments.py`
- ✅ Actualizar `services/investment_service.py`
- ✅ Agregar endpoint `/api-status`
- ✅ Verificar logs de fallback

### Frontend
- ✅ Servicios ya funcionan con nueva arquitectura
- ✅ No requiere cambios adicionales

### Testing
- ✅ Probar búsqueda: `GET /api/investments/search?q=AAPL`
- ✅ Probar quote: `GET /api/investments/quote?q=AAPL`
- ✅ Verificar status: `GET /api/investments/api-status`
- ✅ Revisar logs para confirmar fallback

---

## 📚 Referencias

- [Finnhub Documentation](https://finnhub.io/docs/api)
- [Alpha Vantage Documentation](https://www.alphavantage.co/documentation/)
- [httpx Documentation](https://www.python-httpx.org/)
- [Async/await en Python](https://docs.python.org/3/library/asyncio.html)

---

## 🔐 Consideraciones de Seguridad

- ✅ API keys en variables de entorno (nunca en código)
- ✅ Rate limiting implementado para proteger APIs externas
- ✅ Validación de entrada en queries
- ✅ Logging de todas las operaciones para auditoría
- ✅ Endpoints protegidos con JWT

---

**Sistema implementado y listo para producción.** 🎉
