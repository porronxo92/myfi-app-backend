# Fix: Error de Encriptación con Tipos de Datos Mixtos

**Fecha:** 2026-02-28  
**Autor:** Backend Fix  
**Versión:** 1.0.0

## Problema

Al intentar hacer login u operaciones que involucran carga de modelos con relaciones (User → accounts, Transaction, Investment), se producía el siguiente error:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for UserResponse
account_count
  Error extracting attribute: TypeError: argument of type 'decimal.Decimal' is not iterable
```

## Causa Raíz

La migración de encriptación (migraciones 002-004) creó columnas adicionales con sufijo `_encrypted` (ej: `balance_encrypted`, `amount_encrypted`) pero la migración 004, que elimina las columnas originales y renombra las encriptadas, **NO fue ejecutada**.

Esto resultó en:
- Base de datos con AMBAS columnas: `balance` (tipo `numeric`) y `balance_encrypted` (tipo `text`)
- Modelo SQLAlchemy definiendo `balance = Column(EncryptedNumeric, ...)` apuntando a la columna `numeric` original
- `EncryptedNumeric.process_result_value()` recibiendo un `Decimal` pero esperando un `string`

El error ocurría porque:
```python
# En EncryptedNumeric.process_result_value():
if decrypt_field and ':' in value and value.count(':') == 3:
#                     ^^^^^^^^^^^^
# `value` es Decimal, no string, causando TypeError
```

## Solución Aplicada

Se modificó `app/models/encrypted_fields.py` para que `EncryptedNumeric` sea tolerante a recibir valores `Decimal` directamente (caso de columnas no migradas):

```python
def process_result_value(self, value, dialect):
    """Desencripta y convierte a Decimal"""
    from decimal import Decimal, InvalidOperation
    
    if value is None:
        return value
    
    # NUEVO: Si ya es un Decimal (columna numeric no migrada), devolverlo directamente
    if isinstance(value, Decimal):
        return value
    
    # NUEVO: Si es un número (int, float), convertir a Decimal
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    
    _, decrypt_field, _ = _get_encryption_module()
    
    # Verificar si está encriptado (solo para strings)
    if isinstance(value, str) and decrypt_field and ':' in value and value.count(':') == 3:
        try:
            value = decrypt_field(value)
        except Exception as e:
            logger.warning(f"Error desencriptando numérico: {e}")
    
    # Convertir a Decimal
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        logger.error(f"Valor numérico inválido: {value}")
        return None
```

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `app/models/encrypted_fields.py` | Añadida compatibilidad con valores `Decimal` en `EncryptedNumeric.process_result_value()` |

## Estado de la Base de Datos

Actualmente la BD tiene un estado "híbrido" con columnas originales Y encriptadas:

| Tabla | Columnas Originales | Columnas Encriptadas |
|-------|---------------------|---------------------|
| `users` | `email`, `full_name`, `profile_picture` | `email_encrypted`, `full_name_encrypted`, `profile_picture_encrypted` |
| `accounts` | `balance` (numeric), `account_number`, `notes` | `balance_encrypted`, `account_number_encrypted`, `notes_encrypted` |
| `transactions` | `amount` (numeric), `description` | `amount_encrypted`, `description_encrypted` |
| `investments` | `symbol`, `company_name`, `shares`, `average_price` | `symbol_encrypted`, `company_name_encrypted`, `shares_encrypted`, `average_price_encrypted` |

## Próximos Pasos (Opcional)

Si se desea completar la migración a encriptación total:

1. **Ejecutar migración de datos** (si no se hizo):
   ```bash
   python scripts/migrate_encrypt_data.py
   ```

2. **Ejecutar migración 004** para eliminar columnas originales:
   ```bash
   psql -U admin -d app_finance -f migrations/004_encryption_only_fields.sql
   ```

3. **Verificar** que la aplicación funciona correctamente después de la migración.

> **⚠️ IMPORTANTE:** Hacer backup de la base de datos ANTES de ejecutar migraciones destructivas.

## Tests Realizados

Se verificó el correcto funcionamiento con pruebas directas a la BD:

```
TEST SUMMARY
============================================================
Passed: 4/4
  [PASS] users - Carga usuarios y cuenta de cuentas (account_count)
  [PASS] accounts - Carga cuentas con balance Decimal
  [PASS] transactions - Carga transacciones con amount Decimal  
  [PASS] investments - Carga inversiones con shares/price Decimal
```

El endpoint de login también funciona correctamente (retorna 401 por credenciales incorrectas, no por error de modelo).
