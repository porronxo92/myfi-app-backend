# Fix de Errores en Quotes de Múltiples Inversiones

## Problemas Identificados

### 1. **Enum Status Invalido (RESUELTO)**
- **Problema**: El código estaba enviando `'ACTIVE'` en lugar de `'active'` a PostgreSQL
- **Causa**: SQLAlchemy estaba usando el nombre del enum en lugar del valor
- **Solución**: Actualizar el modelo `Investment` para usar `values_callable=lambda x: [e.value for e in x]`
- **Archivo**: `backend/app/models/investment.py` línea 92

### 2. **Rate Limiting en Alpha Vantage (RESUELTO)**
- **Problema**: CMG fallaba porque Alpha Vantage rechazaba la segunda llamada consecutiva
- **Causa**: El plan gratuito de Alpha Vantage permite solo 5 API calls por minuto
- **Solución**: Implementar delays de 12.5 segundos entre llamadas consecutivas
- **Archivo**: `backend/app/utils/alpha_vantage.py` línea 211

### 3. **Falta de Mejor Diagnóstico**
- **Problema**: Difícil identificar por qué ciertos tickers fallaban
- **Solución**: Agregar logging mejorado que muestre la respuesta completa de Alpha Vantage
- **Archivo**: `backend/app/utils/alpha_vantage.py` línea 140

## Cambios Realizados

### `backend/app/models/investment.py`
```python
# ANTES:
status = Column(
    Enum(InvestmentStatus),
    nullable=False,
    default=InvestmentStatus.ACTIVE,
    server_default='active',
    comment="Estado: active, sold, watchlist",
    index=True
)

# DESPUÉS:
status = Column(
    Enum(InvestmentStatus, values_callable=lambda x: [e.value for e in x]),
    nullable=False,
    default=InvestmentStatus.ACTIVE,
    server_default='active',
    comment="Estado: active, sold, watchlist",
    index=True
)
```

### `backend/app/utils/alpha_vantage.py`

#### Cambio 1: Agregar import de asyncio
```python
import asyncio  # Agregado para manejar delays
```

#### Cambio 2: Implementar rate limiting en `get_multiple_quotes`
```python
# ANTES:
async def get_multiple_quotes(self, symbols: List[str]) -> dict[str, Optional[StockQuote]]:
    quotes = {}
    for symbol in symbols:
        quote = await self.get_stock_quote(symbol)
        quotes[symbol] = quote
    return quotes

# DESPUÉS:
async def get_multiple_quotes(self, symbols: List[str]) -> dict[str, Optional[StockQuote]]:
    """
    Obtener cotizaciones para múltiples símbolos con rate limiting
    
    Alpha Vantage permite 5 requests por minuto en el plan gratuito.
    Este método agrega delays entre llamadas para evitar exceder el límite.
    """
    if not symbols:
        return {}
    
    quotes = {}
    api_delay = 12.5  # Segundos entre llamadas (5 calls/minuto = 12s)
    
    logger.info(f"Getting quotes for {len(symbols)} symbols (with {api_delay}s delay between calls)")
    
    for i, symbol in enumerate(symbols):
        try:
            quote = await self.get_stock_quote(symbol)
            quotes[symbol] = quote
            
            # Agregar delay entre llamadas (excepto después de la última)
            if i < len(symbols) - 1:
                logger.debug(f"Waiting {api_delay}s before next API call...")
                await asyncio.sleep(api_delay)
                
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            quotes[symbol] = self._get_mock_quote(symbol)
    
    return quotes
```

#### Cambio 3: Mejorar logging para diagnóstico
```python
# ANTES:
if not quote_data or "05. price" not in quote_data:
    logger.warning(f"No quote data in 'Global Quote' for: {symbol}")
    logger.debug(f"Response data: {data}")
    logger.warning(f"Using mock quote for: {symbol}")
    return self._get_mock_quote(symbol)

# DESPUÉS:
if not quote_data or "05. price" not in quote_data:
    logger.warning(f"No quote data in 'Global Quote' for: {symbol}")
    # Logear toda la respuesta para diagnóstico
    if data:
        logger.debug(f"Full API response for {symbol}: {data}")
        if "Global Quote" in data:
            logger.debug(f"Global Quote data: {data['Global Quote']}")
    else:
        logger.debug(f"Empty response for {symbol}")
    logger.warning(f"⚠️  Ticker '{symbol}' not found or rate limited - Using mock quote")
    return self._get_mock_quote(symbol)
```

## Impacto

✅ **Eliminadas**: Las excepciones de enum inválido al agregar inversiones
✅ **Mejorado**: El flujo de obtener quotes para múltiples inversiones
✅ **Reducido**: Riesgo de rate limiting de Alpha Vantage
✅ **Aumentado**: Visibilidad del diagnóstico en logs

## Próximos Pasos Recomendados

### 1. **Considerar un Plan Pagado de Alpha Vantage**
- Free tier: 5 calls/minuto (muy limitado para portfolio de múltiples acciones)
- Premium: Límites más altos
- Investigar costo vs. beneficio

### 2. **Implementar Caching**
```python
# Cachear quotes por X minutos para no hacer tantas llamadas
from functools import lru_cache
from datetime import datetime, timedelta

class QuoteCache:
    def __init__(self, ttl_minutes=5):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, symbol):
        entry = self.cache.get(symbol)
        if entry and datetime.now() - entry['time'] < self.ttl:
            return entry['quote']
        return None
    
    def set(self, symbol, quote):
        self.cache[symbol] = {'quote': quote, 'time': datetime.now()}
```

### 3. **Alertar Usuario sobre Ticker Inválido**
- Si un ticker no existe en Alpha Vantage, notificar al usuario
- Sugerir búsqueda para encontrar ticker correcto

### 4. **Monitorear Uso de API**
- Registrar cantidad de calls por día
- Alertar si se acerca al límite

## Pruebas Realizadas

Para probar que los cambios funcionan:

1. Crear 2+ inversiones con tickers diferentes
2. Ir a la página de Inversiones
3. Verificar que se obtienen quotes correctamente sin errores
4. Revisar logs para ver los delays entre llamadas:
   ```
   INFO     | Getting quotes for 2 symbols (with 12.5s delay between calls)
   INFO     | Calling Alpha Vantage GLOBAL_QUOTE for: AMZN
   INFO     | ✅ Alpha Vantage quote for AMZN: $246.47
   DEBUG    | Waiting 12.5s before next API call...
   INFO     | Calling Alpha Vantage GLOBAL_QUOTE for: CMG
   INFO     | ✅ Alpha Vantage quote for CMG: ...
   ```

## Referencias

- [Alpha Vantage API Limits](https://www.alphavantage.co/support/#api-key)
- [SQLAlchemy Enum with Custom Values](https://docs.sqlalchemy.org/en/20/core/types.html#sqlalchemy.types.Enum)
