# 🗄️ Inicialización de Base de Datos

## 📋 Overview

El script `app/bbdd/schema_app_finance.sql` contiene el schema completo de la aplicación y se ejecuta **automáticamente** la primera vez que se crea la base de datos con Docker Compose.

---

## 🔄 Cómo funciona

PostgreSQL monta el script en `/docker-entrypoint-initdb.d/` del contenedor, que es un directorio especial donde todos los archivos `.sql` se ejecutan automáticamente durante la primera inicialización.

```yaml
# docker-compose.yml
volumes:
  - ./app/bbdd/schema_app_finance.sql:/docker-entrypoint-initdb.d/01_schema.sql:ro
```

**Importante:**
- ✅ Se ejecuta **SOLO** en la primera creación
- ✅ Si el volumen ya existe, **NO se re-ejecuta**
- ✅ Orden de ejecución por nombre de archivo (01_schema.sql)

---

## 🚀 Iniciar con schema limpio

### Primera vez (limpia)

```powershell
# Levantar todo
docker-compose up -d

# El script se ejecuta automáticamente
# Verificar que se creó correctamente
docker-compose exec db psql -U postgres -d app_finance -c "\dt"
```

### Re-inicializar (borrar todo)

Si necesitas **borrar la base de datos** y volver a crear el schema:

```powershell
# 1. Detener todo y BORRAR volúmenes (⚠️ BORRA DATOS)
docker-compose down -v

# 2. Levantar de nuevo (ejecutará schema_app_finance.sql)
docker-compose up -d

# 3. Verificar tablas
docker-compose exec db psql -U postgres -d app_finance -c "\dt"
```

---

## ✅ Verificar que el schema se aplicó

```powershell
# Ver todas las tablas
docker-compose exec db psql -U postgres -d app_finance -c "\dt"

# Ver extensiones
docker-compose exec db psql -U postgres -d app_finance -c "\dx"

# Ver tipos personalizados
docker-compose exec db psql -U postgres -d app_finance -c "\dT"

# Ver funciones
docker-compose exec db psql -U postgres -d app_finance -c "\df"
```

**Deberías ver:**
- ✅ Extensión `uuid-ossp`
- ✅ Tipo `investment_status` (ENUM)
- ✅ Función `calculate_account_balance()`
- ✅ Tablas: `users`, `accounts`, `categories`, `transactions`, etc.

---

## 🔧 Añadir más scripts de inicialización

Si necesitas ejecutar **múltiples scripts** en orden:

```
app/bbdd/
├── schema_app_finance.sql      ← Ya montado como 01_schema.sql
├── 02_seed_data.sql            ← Datos iniciales (opcional)
└── 03_test_users.sql           ← Usuarios de prueba (opcional)
```

Actualizar `docker-compose.yml`:

```yaml
volumes:
  - postgres-data:/var/lib/postgresql/data
  - ./app/bbdd/schema_app_finance.sql:/docker-entrypoint-initdb.d/01_schema.sql:ro
  - ./app/bbdd/02_seed_data.sql:/docker-entrypoint-initdb.d/02_seed.sql:ro
  - ./app/bbdd/03_test_users.sql:/docker-entrypoint-initdb.d/03_test_users.sql:ro
```

PostgreSQL los ejecutará en orden alfabético.

---

## 🆘 Troubleshooting

### El script no se ejecutó

```powershell
# Ver logs de PostgreSQL durante inicialización
docker-compose logs db | Select-String -Pattern "init"

# Verificar que el archivo está montado
docker-compose exec db ls -la /docker-entrypoint-initdb.d/
```

### Error en el script SQL

```powershell
# Ver logs completos
docker-compose logs db

# Errores típicos:
# - Sintaxis SQL incorrecta
# - Falta extensión (uuid-ossp)
# - Permisos insuficientes
```

**Solución:** Corregir el script y reinicializar con `docker-compose down -v`.

### Quiero ejecutar el script manualmente

```powershell
# Copiar script al contenedor
docker cp app/bbdd/schema_app_finance.sql finanzas-db:/tmp/

# Ejecutar manualmente
docker-compose exec db psql -U postgres -d app_finance -f /tmp/schema_app_finance.sql
```

---

## 📊 Conexión a la BD desde cliente externo

**DBeaver, pgAdmin, DataGrip, etc.:**

```
Host:     localhost
Port:     5433  ← Puerto mapeado en docker-compose
User:     postgres
Password: postgres
Database: app_finance
```

---

## 🔐 Seguridad en Producción

⚠️ **Para Cloud Run/Producción:**

1. **NO usar scripts de inicialización** en Docker
2. Usar **Cloud SQL** (managed PostgreSQL)
3. Ejecutar schema manualmente o con **migrations** (Alembic)
4. Cambiar credenciales por defecto

```powershell
# Ejemplo para Cloud SQL
gcloud sql instances create finanzas-db \
  --database-version=POSTGRES_15 \
  --region=europe-west1 \
  --tier=db-f1-micro

# Ejecutar schema
gcloud sql connect finanzas-db --user=postgres < app/bbdd/schema_app_finance.sql
```

---

## 📌 Resumen

| Acción | Comando |
|--------|---------|
| Iniciar limpio | `docker-compose up -d` |
| Resetear BD | `docker-compose down -v && docker-compose up -d` |
| Ver tablas | `docker-compose exec db psql -U postgres -d app_finance -c "\dt"` |
| Acceder a BD | `docker-compose exec db psql -U postgres -d app_finance` |
| Ver logs | `docker-compose logs db` |
