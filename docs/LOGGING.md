# Logging Configuration

## Directorio de Logs

Todos los logs se guardan en:
```
C:\Users\rcruzd\OneDrive - Indra\Documentos\Workspace VS\AppFinanzas\logsBackend
```

## Archivos de Log

### 1. `app.log`
- **Descripción**: Log principal de la aplicación
- **Nivel**: INFO
- **Contenido**: Eventos generales, inicio/fin de procesos, información de configuración
- **Rotación**: Por tamaño (10MB), mantiene 5 backups

### 2. `errors.log`
- **Descripción**: Log solo de errores
- **Nivel**: ERROR
- **Contenido**: Excepciones, errores críticos, stack traces
- **Rotación**: Por tamaño (10MB), mantiene 5 backups

### 3. `access.log`
- **Descripción**: Log de acceso HTTP
- **Nivel**: INFO
- **Contenido**: Todas las peticiones HTTP con IP, método, path, user-agent
- **Rotación**: Diaria a medianoche, mantiene 90 días

### 4. `security.log`
- **Descripción**: Log de eventos de seguridad
- **Nivel**: WARNING
- **Contenido**: Fallos de autenticación, rate limiting, intentos de acceso inválidos
- **Rotación**: Por tamaño (10MB), mantiene 5 backups

### 5. `upload.log`
- **Descripción**: Log específico de uploads de archivos
- **Nivel**: INFO
- **Contenido**: Procesamiento de archivos, validaciones, errores de parsing
- **Rotación**: Por tamaño (10MB), mantiene 5 backups

## Formato de Logs

```
2025-12-21 15:30:45 | INFO     | app.main | log_requests:62 | GET /api/upload/allowed-extensions - Status: 200 - Time: 0.003s
```

**Componentes:**
- `Timestamp`: Fecha y hora exacta
- `Nivel`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `Logger`: Nombre del módulo que genera el log
- `Función:Línea`: Función y línea de código
- `Mensaje`: Descripción del evento

## Uso en el Código

### Importar logger

```python
from app.utils.logger import get_logger, upload_logger, security_logger

# Logger específico del módulo
logger = get_logger("app.routes.mi_modulo")
```

### Niveles de Logging

```python
# DEBUG - Información detallada para debugging
logger.debug("Variable x tiene valor: {x}")

# INFO - Eventos normales del sistema
logger.info("Usuario autenticado correctamente")

# WARNING - Situaciones anormales pero no críticas
logger.warning("Archivo muy grande, procesamiento lento")

# ERROR - Errores que impiden operaciones específicas
logger.error("No se pudo conectar a la base de datos")

# CRITICAL - Errores críticos que pueden detener la aplicación
logger.critical("Sistema sin memoria, cerrando aplicación")
```

### Logging de Excepciones

```python
from app.utils.logger import log_exception

try:
    # código que puede fallar
    procesar_archivo()
except Exception as e:
    log_exception(logger, e, "procesar_archivo")
    raise
```

## Configuración

### Variables de Entorno (.env)

```bash
# Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Tamaño máximo antes de rotar (MB)
LOG_ROTATION_SIZE_MB=10

# Número de archivos de backup
LOG_BACKUP_COUNT=5
```

### Cambiar Directorio de Logs

En `config.py`:
```python
LOGS_DIR: Path = Path(r"C:\ruta\a\tus\logs")
```

## Características

✅ **Rotación Automática**
- Por tamaño (10MB por defecto)
- Diaria para access logs
- Mantiene backups configurables

✅ **Colores en Consola**
- DEBUG: Cyan
- INFO: Verde
- WARNING: Amarillo
- ERROR: Rojo
- CRITICAL: Magenta

✅ **Salida Dual**
- Archivo: Logs persistentes en disco
- Consola: Output en tiempo real con colores

✅ **UTF-8 Encoding**
- Soporte completo de caracteres especiales

✅ **Thread-Safe**
- Seguro para aplicaciones concurrentes

## Monitoreo de Logs

### Tail en PowerShell
```powershell
Get-Content -Path "C:\...\logsBackend\app.log" -Wait -Tail 50
```

### Filtrar por nivel
```powershell
Select-String -Path "C:\...\logsBackend\*.log" -Pattern "ERROR"
```

### Ver últimos errores
```powershell
Get-Content "C:\...\logsBackend\errors.log" -Tail 20
```

## Logs por Módulo

Cada módulo puede tener su propio archivo de log:

```python
logger = get_logger("app.database")  # Crea database.log
logger = get_logger("app.services.payment")  # Crea services_payment.log
```

## Limpieza de Logs

Los archivos de log se mantienen según la configuración:
- **access.log**: 90 días de historial
- **Otros logs**: 5 archivos de backup (50MB total aprox.)

Para limpiar manualmente:
```powershell
Remove-Item "C:\...\logsBackend\*.log.*"  # Elimina backups
```

## Troubleshooting

### Los logs no se crean
1. Verificar permisos de escritura en el directorio
2. Asegurar que el directorio existe
3. Revisar configuración de `LOGS_DIR` en `config.py`

### Logs muy grandes
1. Reducir `LOG_LEVEL` a WARNING o ERROR
2. Disminuir `LOG_BACKUP_COUNT`
3. Implementar limpieza programada

### No aparecen en consola
1. Verificar `console_output=True` en `setup_logger`
2. Revisar nivel de logging del handler de consola
