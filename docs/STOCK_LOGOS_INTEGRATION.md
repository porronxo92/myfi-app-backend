# Stock Logos Integration - Brandfetch API

## 📋 Resumen

Sistema de integración con Brandfetch API para obtener los logos de las empresas/stocks en la aplicación de finanzas.

## 🎯 Características

- **Endpoint REST**: `/api/investments/logo?q={TICKER}`
- **API utilizada**: Brandfetch CDN
- **Autenticación**: Requiere JWT token
- **Rate limiting**: Protegido con rate limit general

## 🔧 Configuración

### 1. Obtener Client ID de Brandfetch

1. Visita [https://brandfetch.com/](https://brandfetch.com/)
2. Regístrate o inicia sesión
3. Obtén tu `client-id`

### 2. Configurar Variables de Entorno

Añade en tu archivo `.env`:

```env
# ============================================
# BRANDFETCH API (Stock Logos)
# ============================================
BRANDFETCH_CLIENT_ID=tu_client_id_aqui
```

## 📡 Uso del Endpoint

### Obtener Logo de una Acción

**Request:**
```http
GET /api/investments/logo?q=AAPL HTTP/1.1
Authorization: Bearer {token}
```

**Response Exitosa (200):**
```json
{
  "ticker": "AAPL",
  "logo_url": "https://cdn.brandfetch.io/AAPL?c=YOUR_CLIENT_ID",
  "available": true,
  "content_type": "image/png"
}
```

**Response cuando no está disponible (200):**
```json
{
  "ticker": "AAPL",
  "logo_url": null,
  "available": false,
  "message": "Logo not available for AAPL"
}
```

**Error - Service Not Configured (503):**
```json
{
  "detail": "Logo service not configured"
}
```

**Error - Timeout (504):**
```json
{
  "detail": "Logo service timeout"
}
```

## 💻 Ejemplos de Uso

### cURL

```bash
curl -X GET "http://localhost:8000/api/investments/logo?q=AAPL" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### JavaScript/TypeScript (Angular)

```typescript
// service
getStockLogo(ticker: string): Observable<LogoResponse> {
  return this.http.get<LogoResponse>(
    `${this.apiUrl}/investments/logo?q=${ticker}`
  );
}

// component
this.investmentService.getStockLogo('AAPL').subscribe({
  next: (response) => {
    if (response.available) {
      this.logoUrl = response.logo_url;
    } else {
      this.logoUrl = 'assets/default-stock-logo.png';
    }
  },
  error: (error) => {
    console.error('Error fetching logo:', error);
    this.logoUrl = 'assets/default-stock-logo.png';
  }
});
```

### Python

```python
import httpx

async def get_stock_logo(ticker: str, token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/investments/logo?q={ticker}",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()

# Uso
logo_data = await get_stock_logo("AAPL", "your_jwt_token")
if logo_data["available"]:
    print(f"Logo URL: {logo_data['logo_url']}")
```

## 🏗️ Arquitectura

### Flujo de Datos

```
Usuario → Frontend → Backend API → Brandfetch CDN
                                       ↓
                                   Logo Image
```

### Componentes Modificados

1. **`backend/app/config.py`**
   - Añadida variable `BRANDFETCH_CLIENT_ID`

2. **`backend/app/services/stock_api_service.py`**
   - Añadido método `get_stock_logo(ticker: str)`
   - Configuración de Brandfetch en `__init__`

3. **`backend/app/routes/investments.py`**
   - Nuevo endpoint `GET /api/investments/logo`

4. **`backend/.env.example`**
   - Documentación de `BRANDFETCH_CLIENT_ID`

## 🔒 Seguridad

- ✅ Autenticación JWT requerida
- ✅ Rate limiting aplicado
- ✅ Validación de parámetros
- ✅ Timeout de 10 segundos
- ✅ Manejo de errores robusto

## ⚡ Performance

- **Timeout**: 10 segundos
- **Cache**: Se recomienda implementar cache en el frontend
- **CDN**: Brandfetch utiliza CDN para servir los logos

## 📝 Notas Importantes

1. **Formato de URL de Brandfetch:**
   ```
   https://cdn.brandfetch.io/{TICKER}?c={CLIENT_ID}
   ```

2. **Tickers soportados:**
   - La disponibilidad del logo depende de Brandfetch
   - No todos los tickers tienen logo disponible
   - El endpoint devuelve `available: false` si no hay logo

3. **Mejoras futuras recomendadas:**
   - Implementar cache en Redis/memoria para logos frecuentes
   - Fallback a otras APIs de logos (Clearbit, Google, etc.)
   - Almacenar URLs de logos en base de datos

## 🧪 Testing

```bash
# Test manual
curl -X GET "http://localhost:8000/api/investments/logo?q=AAPL" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Tickers para probar
# - AAPL (Apple)
# - MSFT (Microsoft)
# - GOOGL (Google)
# - TSLA (Tesla)
# - ONON (On Running)
```

## 📊 Logging

El servicio genera logs para:
- Solicitudes de logos
- Logos encontrados
- Logos no disponibles
- Errores y timeouts

Ejemplo:
```
[INFO] [LOGO] Fetching logo for AAPL from Brandfetch
[INFO] [LOGO] ✓ Logo found for AAPL
```

## 🔗 Referencias

- [Brandfetch API Documentation](https://brandfetch.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [httpx Documentation](https://www.python-httpx.org/)

---

**Fecha de implementación:** 13 de enero de 2026  
**Versión:** 1.0.0
