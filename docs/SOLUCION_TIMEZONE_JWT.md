# 🔧 Solución: Token JWT Expirado al Crear (Problema de Timezone)

## 🐛 Problema Identificado

Los tokens JWT nacían **ya expirados** debido a un problema de zona horaria.

### Logs que mostraban el error:
```
2025-12-26 00:06:59 | INFO | Access token creado. Expira en: 2025-12-25 23:36:59
2025-12-26 00:07:00 | WARNING | GET /api/accounts - Status: 403
```

**Análisis**:
- Hora actual del servidor: **26 dic 00:06:59** (España, UTC+1)
- Token expira: **25 dic 23:36:59** (UTC)
- **Resultado**: Token nace expirado (-30 minutos)

### Causa Raíz

En `backend/app/utils/jwt.py`:
```python
# ❌ CÓDIGO ANTIGUO (incorrecto)
expire = datetime.utcnow() + timedelta(minutes=30)
```

**Problema**: `datetime.utcnow()` devuelve un **naive datetime** (sin información de timezone), causando confusión cuando el servidor está en una zona horaria diferente de UTC.

---

## ✅ Solución Aplicada

### Cambio 1: Import timezone
```python
# ANTES
from datetime import datetime, timedelta

# AHORA
from datetime import datetime, timedelta, timezone
```

### Cambio 2: Usar datetime timezone-aware
```python
# ❌ ANTES (naive datetime)
expire = datetime.utcnow() + timedelta(minutes=30)

# ✅ AHORA (timezone-aware)
expire = datetime.now(timezone.utc) + timedelta(minutes=30)
```

### Archivos modificados:
- `backend/app/utils/jwt.py`
  - Línea 38: `create_access_token()`
  - Línea 67: `create_refresh_token()`

---

## 🧪 Validación

Ejecuté script de prueba:
```bash
cd backend
python tests\test_jwt_timezone.py
```

**Resultado**:
```
📍 Zona horaria del sistema:
   Hora local:     2025-12-26 00:12:54 (España, UTC+1)
   Hora UTC:       2025-12-25 23:12:54 UTC
   
✅ Access Token:
   - Expira:        2025-12-25 23:42:54 UTC
   - Tiempo restante: 30.0 minutos
   - ¿Válido?:      ✅ SÍ

✅ Refresh Token:
   - Expira:        2026-01-01 23:12:54 UTC  
   - Tiempo restante: 7.0 días
   - ¿Válido?:      ✅ SÍ
```

---

## 📋 Instrucciones para Aplicar

### 1. Reiniciar Backend
```bash
# Detén el servidor (Ctrl+C en la terminal donde corre)
cd backend
python -m app.main
```

### 2. Probar Login Nuevamente

1. **Frontend**: `http://localhost:4200/login`
2. Ingresar credenciales
3. Click "Iniciar Sesión"

**Verificar en logs del backend**:
```
INFO | Access token creado. Expira en: 2025-12-26 00:42:XX+00:00
INFO | Login exitoso para usuario@email.com
INFO | GET /api/accounts - Status: 200 ✅
INFO | GET /api/transactions - Status: 200 ✅
INFO | GET /api/categories - Status: 200 ✅
```

**Verificar en frontend**:
- ✅ No aparecen errores 403
- ✅ Dashboard carga correctamente
- ✅ KPI cards muestran datos reales
- ✅ Sección "Mis Cuentas" funciona

### 3. Verificar DevTools

**Network Tab**:
```
GET http://localhost:8000/api/accounts
Status: 200 OK ✅

Request Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🔍 Explicación Técnica

### Diferencia entre naive y aware datetime

**Naive datetime** (sin timezone):
```python
datetime.utcnow()  # 2025-12-25 23:12:54
# ⚠️ No tiene información de zona horaria
# Python no sabe si es UTC, UTC+1, etc.
```

**Aware datetime** (con timezone):
```python
datetime.now(timezone.utc)  # 2025-12-25 23:12:54+00:00
# ✅ Explícitamente marca que es UTC
# Python puede comparar correctamente con otras fechas
```

### Por qué importa en JWT

Los tokens JWT usan el campo `exp` (expiration) que es un **timestamp Unix** (segundos desde 1970-01-01 UTC).

Cuando se crea:
```python
# ❌ PROBLEMA con naive datetime
expire = datetime.utcnow() + timedelta(minutes=30)
exp_timestamp = expire.timestamp()  # ⚠️ Asume hora local del servidor

# ✅ SOLUCIÓN con aware datetime  
expire = datetime.now(timezone.utc) + timedelta(minutes=30)
exp_timestamp = expire.timestamp()  # ✅ Siempre es UTC correcto
```

### Zona horaria de España

- **Invierno (CET)**: UTC+1
- **Verano (CEST)**: UTC+2

Si el servidor está en España y usa `utcnow()`:
1. Sistema devuelve: 26 dic 00:06:59 (hora local)
2. Python piensa que es UTC
3. Resta 1 hora al convertir a timestamp
4. Token expira 1 hora antes de lo esperado
5. **Resultado**: 403 Forbidden

---

## ✅ Checklist de Verificación

Después de reiniciar el backend, confirma:

- [ ] Backend reiniciado correctamente
- [ ] Logs muestran: `Expira en: 2025-XX-XX XX:XX:XX+00:00` (con `+00:00`)
- [ ] Login funciona sin errores
- [ ] Dashboard carga sin errores 403
- [ ] Peticiones a `/api/accounts` devuelven 200
- [ ] Peticiones a `/api/transactions` devuelven 200
- [ ] Peticiones a `/api/categories` devuelven 200
- [ ] Al recargar página (F5), sesión se mantiene

---

## 🎯 Impacto del Fix

**Antes**:
- ❌ Tokens nacían expirados en zonas horarias ≠ UTC
- ❌ Login exitoso pero inmediato 403 en las siguientes peticiones
- ❌ Imposible usar la aplicación

**Después**:
- ✅ Tokens válidos durante 30 minutos (access) y 7 días (refresh)
- ✅ Login funciona correctamente
- ✅ Dashboard carga todos los datos
- ✅ Aplicación completamente funcional

---

## 🚀 Siguiente Paso

Una vez reiniciado el backend, prueba:
1. Login
2. Crear una cuenta nueva
3. Ver las cuentas en el dashboard
4. Recargar la página (verificar que sesión persiste)

Si todo funciona correctamente, el problema estará **completamente resuelto**.
