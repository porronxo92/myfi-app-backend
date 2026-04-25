# API de Finanzas Personal - Documentación de Seguridad

## Autenticación por API Key

### Configuración

1. **Generar API Key segura**: Cambiar el valor en `.env`
   ```bash
   API_KEY=tu-clave-super-secreta-aqui
   ```

2. **Habilitar/Deshabilitar autenticación**:
   ```bash
   ENABLE_API_KEY_AUTH=true  # Activar en producción
   ENABLE_API_KEY_AUTH=false # Solo desarrollo local
   ```

### Uso

Todas las peticiones a endpoints protegidos (excepto `/` y `/health`) requieren el header:

```bash
x-api-key: tu-clave-super-secreta-aqui
```

#### Ejemplo con cURL:
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "x-api-key: tu-clave-super-secreta-aqui" \
  -F "fichero=@documento.pdf"
```

#### Ejemplo con JavaScript:
```javascript
fetch('http://localhost:8000/api/upload', {
  method: 'POST',
  headers: {
    'x-api-key': 'tu-clave-super-secreta-aqui'
  },
  body: formData
});
```

#### Ejemplo con Postman:
1. En la pestaña **Headers**
2. Key: `x-api-key`
3. Value: `tu-clave-super-secreta-aqui`

---

## Medidas de Seguridad Implementadas

### 1. ✅ Autenticación por API Key
- Header `x-api-key` requerido en todos los endpoints protegidos
- Configurable por entorno (.env)
- Posibilidad de desactivar en desarrollo

### 2. ✅ Rate Limiting
- Límite de peticiones por cliente (100 req/60s por defecto)
- Bloqueo temporal tras exceder límite
- Identificación por API Key o IP
- Headers `Retry-After` en respuestas 429

### 3. ✅ CORS Restrictivo
- Solo orígenes permitidos en whitelist
- Configurable por entorno
- Protección contra peticiones cross-origin no autorizadas

### 4. ✅ Security Headers
- `X-Content-Type-Options: nosniff` - Previene MIME sniffing
- `X-Frame-Options: DENY` - Previene clickjacking
- `X-XSS-Protection: 1; mode=block` - Protección XSS
- `Strict-Transport-Security` - Fuerza HTTPS
- `X-Process-Time` - Monitoreo de rendimiento

### 5. ✅ Trusted Host Middleware
- Valida el header Host
- Previene ataques de Host Header Injection
- Lista blanca de hosts permitidos

### 6. ✅ Validación de Archivos
- Extensiones permitidas: PDF, XLSX, CSV, TXT
- Límite de tamaño configurable (10MB por defecto)
- Validación antes del procesamiento

### 7. ✅ Logging de Peticiones
- Registro de todas las peticiones entrantes
- Tiempo de procesamiento
- Status codes
- Útil para auditoría y detección de anomalías

### 8. ✅ Limpieza Automática
- Archivos temporales eliminados tras procesamiento
- Limpieza periódica del almacenamiento de rate limiting

---

## Recomendaciones Adicionales para Producción

### HTTPS Obligatorio
```python
# En main.py, añadir verificación HTTPS
@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if not request.url.scheme == "https" and settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=400,
            content={"detail": "HTTPS requerido"}
        )
    return await call_next(request)
```

### Base de Datos para Rate Limiting
- Usar Redis en lugar de memoria
- Permite escalado horizontal
- Persistencia entre reinicios

### Rotación de API Keys
- Implementar sistema de múltiples keys
- Expiración automática
- Logs de uso por key

### Monitoreo
- Integrar con servicios como Sentry
- Alertas por intentos de autenticación fallidos
- Dashboard de métricas

### Variables de Entorno
```bash
# Nunca commitear el archivo .env
# Usar secretos en CI/CD (GitHub Secrets, AWS Secrets Manager, etc.)
```

---

## Respuestas de Error

### 401 Unauthorized
```json
{
  "detail": "API Key no proporcionada. Incluya el header 'x-api-key'."
}
```

### 403 Forbidden
```json
{
  "detail": "API Key inválida"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Demasiadas peticiones. Reintente en 60 segundos."
}
```

---

## Testing

### Desactivar autenticación en tests:
```python
# En conftest.py
import os
os.environ["ENABLE_API_KEY_AUTH"] = "false"
```

### Probar rate limiting:
```bash
# Hacer 101 peticiones rápidas
for i in {1..101}; do
  curl -H "x-api-key: tu-key" http://localhost:8000/api/upload/allowed-extensions
done
```
