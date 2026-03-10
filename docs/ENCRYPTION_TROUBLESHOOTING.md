# 🔧 Solución de Problemas - Script de Migración de Encriptación

## Problema: "ENCRYPTION_MASTER_KEY no configurada"

### Diagnóstico Rápido

Ejecuta el script de diagnóstico:

```bash
python scripts/test_encryption_config.py
```

Este script verificará:
- ✅ Si el archivo `.env` existe
- ✅ Si `ENCRYPTION_MASTER_KEY` está configurada
- ✅ Si Pydantic Settings la carga correctamente
- ✅ Si KeyManager puede inicializarse
- ✅ Si la encriptación/desencriptación funciona

---

## Soluciones Comunes

### 1. Verificar que el archivo `.env` existe

```bash
# Windows PowerShell
ls .env

# Si no existe, cópialo del ejemplo
cp .env.example .env
```

### 2. Verificar que ENCRYPTION_MASTER_KEY está en .env

Abre el archivo `.env` y verifica que existe la línea:

```dotenv
ENCRYPTION_MASTER_KEY=ZQ99bPowM2nW4JmgP8qMZGUxUaTou6lJpHsoG7W4mPo=
```

**⚠️ IMPORTANTE:** La clave debe estar en formato **base64** (no puede tener espacios).

### 3. Generar una nueva clave (si no tienes una)

```bash
# Generar clave base64 de 32 bytes
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

Copia la salida y pégala en tu `.env`:

```dotenv
ENCRYPTION_MASTER_KEY=<pega_aqui_la_clave_generada>
```

### 4. Verificar formato de la clave

La clave debe:
- ✅ Estar en formato base64
- ✅ Tener aproximadamente 44 caracteres
- ✅ Terminar con `=` o `==` (padding base64)
- ❌ NO tener espacios
- ❌ NO tener saltos de línea

**Ejemplo de clave válida:**
```
ENCRYPTION_MASTER_KEY=ZQ99bPowM2nW4JmgP8qMZGUxUaTou6lJpHsoG7W4mPo=
```

**Ejemplos de claves inválidas:**
```
ENCRYPTION_MASTER_KEY=mi clave secreta         # ❌ No está en base64
ENCRYPTION_MASTER_KEY=abc123                   # ❌ Muy corta
ENCRYPTION_MASTER_KEY=ZQ99bPowM2nW4JmgP8qMZ    # ❌ Formato incorrecto
```

### 5. Verificar que no hay caracteres ocultos

A veces los editores agregan caracteres invisibles. Verifica:

```bash
# Windows PowerShell
Get-Content .env | Select-String "ENCRYPTION_MASTER_KEY"
```

Asegúrate de que la línea se vea exactamente así:
```
ENCRYPTION_MASTER_KEY=ZQ99bPowM2nW4JmgP8qMZGUxUaTou6lJpHsoG7W4mPo=
```

### 6. Reiniciar el terminal

Después de modificar `.env`, cierra y vuelve a abrir tu terminal:

```bash
# Cerrar terminal y abrir uno nuevo
exit
```

---

## Verificación Manual Paso a Paso

### Paso 1: Verificar que tienes el archivo .env

```bash
# Windows PowerShell
Test-Path .env
# Debe retornar: True
```

### Paso 2: Ver el contenido de ENCRYPTION_MASTER_KEY

```bash
# Windows PowerShell
(Get-Content .env | Select-String "ENCRYPTION_MASTER_KEY").ToString()
```

### Paso 3: Probar cargar con Python

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Clave:', os.getenv('ENCRYPTION_MASTER_KEY')[:10] + '...' if os.getenv('ENCRYPTION_MASTER_KEY') else 'NO ENCONTRADA')"
```

Debe mostrar:
```
Clave: ZQ99bPowM2...
```

### Paso 4: Ejecutar el script de migración en dry-run

```bash
python scripts/migrate_encrypt_data.py --dry-run
```

---

## Errores Comunes y Soluciones

### Error: "ENCRYPTION_MASTER_KEY no es base64 válido"

**Causa:** La clave no está en formato base64.

**Solución:** Genera una nueva clave:
```bash
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

### Error: "ENCRYPTION_MASTER_KEY debe ser 32 bytes"

**Causa:** La clave decodificada no tiene 32 bytes.

**Solución:** Usa el comando de generación correcto (debe generar exactamente 32 bytes):
```bash
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

### Error: "KeyManager no puede inicializarse"

**Causa:** Problema con la importación de módulos o configuración.

**Solución:** Ejecuta el diagnóstico completo:
```bash
python scripts/test_encryption_config.py
```

---

## Ejemplo de .env Completo

```dotenv
# ============================================
# ENCRYPTION - PSD2 COMPLIANCE
# ============================================
ENCRYPTION_MASTER_KEY=ZQ99bPowM2nW4JmgP8qMZGUxUaTou6lJpHsoG7W4mPo=
ENCRYPTION_KEY_VERSION=1

# ============================================
# SECURITY & JWT
# ============================================
JWT_SECRET_KEY=QBdWFcian0pScKiuu7XLrD7qwk-qQpL162ioSYZxJ5zb6IhruQSpKzaAdB_4uTmK
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

REFRESH_TOKEN_SECRET_KEY=HYIcmkb1GlW0UAFjlMiHImz2wRwgR7Ji3s5Ad1UtAAmYjLWF53OuMgSs43oWBQM7
REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================
# ENVIRONMENT
# ============================================
ENVIRONMENT=development

# ============================================
# DATABASE
# ============================================
DATABASE_URL_LOCALHOST=postgresql://admin:rcruzd@localhost:30432/app_finance
DATABASE_URL_PROD=postgresql://neondb_owner:npg_6kU1KjbCclpY@ep-jolly-river-a93ithgb.gwc.azure.neon.tech/neondb
```

---

## Soporte Adicional

Si ninguna de estas soluciones funciona:

1. Ejecuta el diagnóstico completo:
   ```bash
   python scripts/test_encryption_config.py > diagnostico.txt
   ```

2. Revisa el archivo `diagnostico.txt` generado

3. Verifica los logs del sistema en `../logsBackend/`

---

## Cambios Realizados (2026-02-11)

### Modificaciones en `key_management.py`
- Ahora intenta cargar la clave primero desde Pydantic Settings
- Luego hace fallback a `os.getenv()`
- Mejor manejo de errores y logging

### Modificaciones en `migrate_encrypt_data.py`
- Carga explícita del archivo `.env` con `python-dotenv`
- Mejor diagnóstico y mensajes de error
- Muestra información de debug sobre la clave

### Nuevo script: `test_encryption_config.py`
- Diagnóstico completo de la configuración
- Verifica todos los pasos de carga de la clave
- Prueba la encriptación/desencriptación end-to-end
