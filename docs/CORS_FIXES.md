# CORS Fixes - Resolución de Errores de CORS

## Problemas Identificados

Los errores de CORS se podían deber a varios factores:

1. **Headers de seguridad bloqueando CORS**
   - `X-Frame-Options: DENY` es demasiado restrictivo para CORS
   - Debería ser `SAMEORIGIN`

2. **Falta de `withCredentials: true` en todas las peticiones**
   - El interceptor CORS no estaba garantizando esto en todas las peticiones
   - Algunos servicios lo tenían, pero no todas las peticiones

3. **Headers CORS no expuestos correctamente**
   - Los headers de CORS no estaban en la lista `expose_headers`
   - El middleware no estaba asegurando headers CORS en respuestas

4. **Strict-Transport-Security en desarrollo**
   - Este header causa problemas en localhost HTTP
   - Debería aplicarse solo en producción

## Cambios Realizados

### 1. Backend: `backend/app/main.py`

#### CORS Middleware mejorado
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,  # ← Permite cookies HTTP-only
    allow_methods=["*"],      # Permitir todos los métodos HTTP
    allow_headers=["*"],      # Permitir todos los headers
    expose_headers=[
        "Set-Cookie",
        "Authorization",
        "X-Process-Time",
        "Access-Control-Allow-Credentials",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Origin",
    ],
    max_age=3600,  # Cache de CORS por 1 hora
)
```

**Mejoras:**
- Agregados los headers CORS a `expose_headers`
- Agregado `max_age=3600` para cachear OPTIONS requests
- Más explícito en la intención

#### Headers de seguridad ajustados
```python
# Usar SAMEORIGIN en lugar de DENY para permitir CORS
response.headers["X-Frame-Options"] = "SAMEORIGIN"

# No usar Strict-Transport-Security en desarrollo (localhost)
if settings.ENVIRONMENT == "production":
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

# Asegurarse de que los headers CORS están presentes
if "Access-Control-Allow-Origin" not in response.headers:
    origin = request.headers.get("origin")
    if origin and origin in settings.CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
```

**Mejoras:**
- `X-Frame-Options` ahora es `SAMEORIGIN` (menos restrictivo pero seguro)
- STS solo en producción
- Verificación extra que headers CORS estén presentes

### 2. Frontend: Nuevo Interceptor CORS

#### Archivo: `frontend/src/app/core/interceptors/cors.interceptor.ts`
```typescript
import { HttpInterceptorFn } from '@angular/common/http';

export const corsInterceptor: HttpInterceptorFn = (req, next) => {
  const corsReq = req.clone({
    withCredentials: true
  });
  return next(corsReq);
};
```

**Propósito:**
- Garantiza que TODAS las peticiones HTTP tengan `withCredentials: true`
- Permite que funcione CORS con credenciales

### 3. Frontend: Actualizar configuración

#### Archivo: `frontend/src/app/app.config.ts`
```typescript
provideHttpClient(
  withInterceptors([corsInterceptor, authInterceptor])
)
```

**Orden importa:**
1. `corsInterceptor` primero: agrega `withCredentials: true`
2. `authInterceptor` segundo: agrega `Authorization` header

## Cómo Verificar que Funciona

### En el navegador (DevTools)
1. Abre Chrome DevTools → Network
2. Haz una petición a la API
3. Verifica que la petición tiene:
   - Header `Cookie: ...`
   - Response tiene `Access-Control-Allow-Credentials: true`
   - Response tiene `Access-Control-Allow-Origin: http://localhost:4200`

### En la consola
```javascript
// Debería mostrar el origin correcto
console.log(window.location.origin);

// Si ves errores CORS en rojo, significa que el servidor no permitió la petición
```

### Comando para probar desde cURL
```bash
# Con credentials
curl -i \
  -H "Origin: http://localhost:4200" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization" \
  http://localhost:8000/api/investments

# Buscar estos headers en la respuesta:
# Access-Control-Allow-Origin: http://localhost:4200
# Access-Control-Allow-Credentials: true
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
# Access-Control-Allow-Headers: *
```

## Checklist de Verificación

- ✅ CORSMiddleware tiene `allow_credentials=True`
- ✅ Backend tiene `X-Frame-Options: SAMEORIGIN` (no DENY)
- ✅ Backend expone headers CORS
- ✅ Backend no usa STS en desarrollo
- ✅ Frontend tiene `corsInterceptor` antes que `authInterceptor`
- ✅ Frontend aplica `withCredentials: true` globalmente
- ✅ Endpoints de inversiones responden con Status 200 para OPTIONS
- ✅ Las peticiones POST/GET no retornan CORS blocked errors

## Debugging Adicional

Si aún hay problemas:

1. **Revisar que CORS_ORIGINS está correcto en .env**
   ```
   CORS_ORIGINS=http://localhost:4200,http://localhost:3000,http://127.0.0.1:5173,...
   ```

2. **Revisar que el frontend usa la URL correcta**
   - Debe ser `http://localhost:4200` (sin trailing slash)
   - El backend debe tener esa URL en CORS_ORIGINS

3. **Limpiar caché y cookies**
   ```javascript
   // En DevTools
   localStorage.clear();
   sessionStorage.clear();
   // F12 → Application → Cookies → Delete All
   ```

4. **Reiniciar ambos servidores**
   - Backend: Ctrl+C en terminal, luego `python -m uvicorn app.main:app --reload`
   - Frontend: Ctrl+C en terminal, luego `ng serve`

5. **Revisar logs del backend**
   ```
   2026-01-13 XX:XX:XX | OPTIONS /api/investments - Status: 200
   ```
   Si es 403 o 401, hay un problema con CORS

## Referencias

- [MDN - CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [FastAPI - CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [Angular - HttpClient](https://angular.io/api/common/http/HttpClient)
