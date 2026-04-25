# 📚 Guía de Uso de API - Finanzas Personal

## 🔐 Autenticación

Todos los endpoints requieren autenticación mediante **API Key** en el header:

```
x-api-key: tu-api-key-secreta
```

**Configurar API Key:**
En el archivo `.env`:
```
API_KEY=tu-api-key-secreta
ENABLE_API_KEY_AUTH=true
```

---

## 🏦 CRUD: Accounts (Cuentas)

### 📋 1. Listar Cuentas (con paginación)

**Request:**
```http
GET http://localhost:8000/api/accounts?page=1&page_size=20&is_active=true
x-api-key: tu-api-key-secreta
```

**Response: 200 OK**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Cuenta Bankinter",
      "type": "checking",
      "balance": 2500.00,
      "currency": "EUR",
      "bank_name": "Bankinter",
      "account_number": "ES12 3456 7890 1234 5678 9012",
      "is_active": true,
      "notes": "Cuenta principal",
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-20T15:45:00"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### 🔍 2. Obtener Cuenta por ID

**Request:**
```http
GET http://localhost:8000/api/accounts/550e8400-e29b-41d4-a716-446655440000
x-api-key: tu-api-key-secreta
```

**Response: 200 OK**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Cuenta Bankinter",
  "type": "checking",
  "balance": 2500.00,
  "currency": "EUR",
  "bank_name": "Bankinter",
  "account_number": "ES12 3456 7890 1234 5678 9012",
  "is_active": true,
  "notes": "Cuenta principal",
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-20T15:45:00"
}
```

---

### ➕ 3. Crear Cuenta

**Request:**
```http
POST http://localhost:8000/api/accounts
x-api-key: tu-api-key-secreta
Content-Type: application/json

{
  "name": "Cuenta ING",
  "type": "savings",
  "balance": 5000.00,
  "currency": "EUR",
  "bank_name": "ING",
  "account_number": "ES98 7654 3210 9876 5432 1098",
  "is_active": true,
  "notes": "Cuenta de ahorro"
}
```

**Response: 201 Created**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "Cuenta ING",
  "type": "savings",
  "balance": 5000.00,
  "currency": "EUR",
  "bank_name": "ING",
  "account_number": "ES98 7654 3210 9876 5432 1098",
  "is_active": true,
  "notes": "Cuenta de ahorro",
  "created_at": "2025-01-21T12:00:00",
  "updated_at": "2025-01-21T12:00:00"
}
```

**Tipos de cuenta válidos:**
- `checking` (Cuenta corriente)
- `savings` (Cuenta de ahorro)
- `investment` (Inversión)
- `credit_card` (Tarjeta de crédito)
- `cash` (Efectivo)

---

### ✏️ 4. Actualizar Cuenta

**Request:**
```http
PUT http://localhost:8000/api/accounts/660e8400-e29b-41d4-a716-446655440001
x-api-key: tu-api-key-secreta
Content-Type: application/json

{
  "name": "Cuenta ING Personal",
  "notes": "Actualizado en enero 2025"
}
```

**Response: 200 OK**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "Cuenta ING Personal",
  "type": "savings",
  "balance": 5000.00,
  "currency": "EUR",
  "bank_name": "ING",
  "account_number": "ES98 7654 3210 9876 5432 1098",
  "is_active": true,
  "notes": "Actualizado en enero 2025",
  "created_at": "2025-01-21T12:00:00",
  "updated_at": "2025-01-21T14:30:00"
}
```

---

### 🗑️ 5. Eliminar Cuenta

**Request:**
```http
DELETE http://localhost:8000/api/accounts/660e8400-e29b-41d4-a716-446655440001
x-api-key: tu-api-key-secreta
```

**Response: 204 No Content**

⚠️ **ADVERTENCIA:** Esto eliminará también todas las transacciones asociadas (CASCADE).

---

### 📊 6. Resumen de Cuentas

**Request:**
```http
GET http://localhost:8000/api/accounts/stats/summary
x-api-key: tu-api-key-secreta
```

**Response: 200 OK**
```json
{
  "total_accounts": 5,
  "active_accounts": 4,
  "inactive_accounts": 1,
  "total_balance": 15234.50
}
```

---

## 🏷️ CRUD: Categories (Categorías)

### 📋 1. Listar Categorías

**Request:**
```http
GET http://localhost:8000/api/categories?page=1&page_size=20&type=expense
x-api-key: tu-api-key-secreta
```

**Query Parameters:**
- `page`: Número de página (default: 1)
- `page_size`: Registros por página (default: 20, max: 100)
- `type`: Filtrar por tipo (`income` o `expense`)

**Response: 200 OK**
```json
{
  "items": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "name": "Supermercado",
      "type": "expense",
      "color": "#EF4444",
      "created_at": "2025-01-10T09:00:00"
    },
    {
      "id": "880e8400-e29b-41d4-a716-446655440003",
      "name": "Transporte",
      "type": "expense",
      "color": "#3B82F6",
      "created_at": "2025-01-10T09:05:00"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### ➕ 2. Crear Categoría

**Request:**
```http
POST http://localhost:8000/api/categories
x-api-key: tu-api-key-secreta
Content-Type: application/json

{
  "name": "Salud",
  "type": "expense",
  "color": "#10B981"
}
```

**Tipos de categoría:**
- `income` (Ingreso)
- `expense` (Gasto)

**Formato de color:** Hexadecimal (`#RRGGBB`)

**Response: 201 Created**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "name": "Salud",
  "type": "expense",
  "color": "#10B981",
  "created_at": "2025-01-21T14:00:00"
}
```

---

### ✏️ 3. Actualizar Categoría

**Request:**
```http
PUT http://localhost:8000/api/categories/990e8400-e29b-41d4-a716-446655440004
x-api-key: tu-api-key-secreta
Content-Type: application/json

{
  "color": "#059669"
}
```

**Response: 200 OK**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "name": "Salud",
  "type": "expense",
  "color": "#059669",
  "created_at": "2025-01-21T14:00:00"
}
```

---

### 🗑️ 4. Eliminar Categoría

**Request:**
```http
DELETE http://localhost:8000/api/categories/990e8400-e29b-41d4-a716-446655440004
x-api-key: tu-api-key-secreta
```

**Response: 204 No Content**

ℹ️ **NOTA:** Las transacciones asociadas quedarán con `category_id=NULL` (SET NULL).

---

## 💰 CRUD: Transactions (Transacciones)

### 📋 1. Listar Transacciones (con filtros)

**Request:**
```http
GET http://localhost:8000/api/transactions?page=1&page_size=20&type=expense&date_from=2025-01-01&date_to=2025-01-31&account_id=550e8400-e29b-41d4-a716-446655440000
x-api-key: tu-api-key-secreta
```

**Query Parameters:**
- `page`: Número de página
- `page_size`: Registros por página (max: 100)
- `account_id`: UUID de la cuenta
- `category_id`: UUID de la categoría
- `type`: Tipo (`income` / `expense` / `transfer`)
- `date_from`: Fecha inicio (YYYY-MM-DD)
- `date_to`: Fecha fin (YYYY-MM-DD)
- `min_amount`: Monto mínimo
- `max_amount`: Monto máximo

**Response: 200 OK**
```json
{
  "items": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440005",
      "account_id": "550e8400-e29b-41d4-a716-446655440000",
      "date": "2025-01-15",
      "amount": -50.00,
      "description": "Mercadona - Compra semanal",
      "category_id": "770e8400-e29b-41d4-a716-446655440002",
      "type": "expense",
      "notes": "Productos de limpieza incluidos",
      "tags": ["alimentación", "hogar"],
      "source": "manual",
      "created_at": "2025-01-15T18:30:00",
      "account_name": "Cuenta Bankinter",
      "category_name": "Supermercado",
      "category_color": "#EF4444"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

---

### ➕ 2. Crear Transacción (Gasto)

**Request:**
```http
POST http://localhost:8000/api/transactions
x-api-key: tu-api-key-secreta
Content-Type: application/json

{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "date": "2025-01-21",
  "amount": -75.50,
  "description": "Restaurante La Tagliatella",
  "category_id": "770e8400-e29b-41d4-a716-446655440002",
  "type": "expense",
  "notes": "Cena familiar",
  "tags": ["restaurantes", "ocio"]
}
```

**Validaciones:**
- `amount` != 0 ✅
- `date` no puede ser futura ✅
- Si `type=transfer`, requiere `transfer_account_id` ✅

**Response: 201 Created**
```json
{
  "id": "bb0e8400-e29b-41d4-a716-446655440006",
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "date": "2025-01-21",
  "amount": -75.50,
  "description": "Restaurante La Tagliatella",
  "category_id": "770e8400-e29b-41d4-a716-446655440002",
  "type": "expense",
  "notes": "Cena familiar",
  "tags": ["restaurantes", "ocio"],
  "source": "manual",
  "created_at": "2025-01-21T19:00:00",
  "account_name": "Cuenta Bankinter",
  "category_name": "Supermercado",
  "category_color": "#EF4444"
}
```

⚡ **NOTA:** El balance de la cuenta se actualiza automáticamente.

---

### ➕ 3. Crear Transacción (Ingreso)

**Request:**
```http
POST http://localhost:8000/api/transactions
x-api-key: tu-api-key-secreta
Content-Type: application/json

{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "date": "2025-01-25",
  "amount": 2500.00,
  "description": "Nómina enero 2025",
  "category_id": "cc0e8400-e29b-41d4-a716-446655440007",
  "type": "income",
  "notes": "Salario mensual"
}
```

**Response: 201 Created**

---

### 🔄 4. Crear Transferencia entre Cuentas

**Request:**
```http
POST http://localhost:8000/api/transactions
x-api-key: tu-api-key-secreta
Content-Type: application/json

{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "transfer_account_id": "660e8400-e29b-41d4-a716-446655440001",
  "date": "2025-01-21",
  "amount": 500.00,
  "description": "Transferencia a cuenta de ahorro",
  "type": "transfer"
}
```

**Efecto:**
- Cuenta origen (`account_id`): +500.00
- Cuenta destino (`transfer_account_id`): -500.00

**Response: 201 Created**

---

### ✏️ 5. Actualizar Transacción

**Request:**
```http
PUT http://localhost:8000/api/transactions/bb0e8400-e29b-41d4-a716-446655440006
x-api-key: tu-api-key-secreta
Content-Type: application/json

{
  "amount": -80.00,
  "notes": "Cena familiar - precio actualizado"
}
```

**Response: 200 OK**

⚡ **NOTA:** Si cambias el `amount`, el balance de la cuenta se ajusta automáticamente.

---

### 🗑️ 6. Eliminar Transacción

**Request:**
```http
DELETE http://localhost:8000/api/transactions/bb0e8400-e29b-41d4-a716-446655440006
x-api-key: tu-api-key-secreta
```

**Response: 204 No Content**

⚡ **NOTA:** El balance de la cuenta se ajusta automáticamente (revierte el monto).

---

### 📊 7. Resumen de Transacciones

**Request:**
```http
GET http://localhost:8000/api/transactions/stats/summary?date_from=2025-01-01&date_to=2025-01-31
x-api-key: tu-api-key-secreta
```

**Response: 200 OK**
```json
{
  "total_income": 3500.00,
  "total_expense": 2150.50,
  "balance": 1349.50
}
```

**Filtrar por cuenta:**
```http
GET http://localhost:8000/api/transactions/stats/summary?account_id=550e8400-e29b-41d4-a716-446655440000&date_from=2025-01-01&date_to=2025-01-31
```

---

## 🚀 Endpoints Públicos (Sin Autenticación)

### 1. Root

**Request:**
```http
GET http://localhost:8000/
```

**Response: 200 OK**
```json
{
  "message": "Finanzas Personal API",
  "version": "1.0.0",
  "docs": "/docs",
  "auth_required": true
}
```

---

### 2. Health Check

**Request:**
```http
GET http://localhost:8000/health
```

**Response: 200 OK**
```json
{
  "status": "healthy",
  "database": "connected",
  "llm_provider": "gemini",
  "auth_enabled": true
}
```

---

## 🔥 Rate Limiting

- **Límite:** 100 peticiones por 60 segundos (configurable en `.env`)
- **Response si se excede:**

```json
{
  "detail": "Rate limit exceeded. Try again later."
}
```

**Status Code:** 429 Too Many Requests

---

## ⚠️ Manejo de Errores

### 400 Bad Request
```json
{
  "detail": "El monto no puede ser cero"
}
```

### 401 Unauthorized
```json
{
  "detail": "Missing or invalid API Key"
}
```

### 404 Not Found
```json
{
  "detail": "Cuenta 550e8400-e29b-41d4-a716-446655440000 no encontrada"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "amount"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 📖 Documentación Interactiva

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 🧪 Colección de Postman

Puedes importar esta colección JSON en Postman:

[Ver archivo: POSTMAN_COLLECTION.json](#)

---

## 🎯 Ejemplos de Uso Prácticos

### Caso de Uso 1: Crear Cuenta y Registrar Gastos

```bash
# 1. Crear cuenta
POST /api/accounts
{
  "name": "Cuenta BBVA",
  "type": "checking",
  "balance": 1000.00,
  "currency": "EUR"
}

# 2. Crear categoría
POST /api/categories
{
  "name": "Compras Online",
  "type": "expense",
  "color": "#F59E0B"
}

# 3. Registrar gasto
POST /api/transactions
{
  "account_id": "<uuid-cuenta>",
  "date": "2025-01-21",
  "amount": -49.99,
  "description": "Amazon - Libros",
  "category_id": "<uuid-categoria>",
  "type": "expense"
}

# 4. Ver resumen
GET /api/transactions/stats/summary?date_from=2025-01-01&date_to=2025-01-31
```

### Caso de Uso 2: Transferencia entre Cuentas

```bash
# Transferir 200€ de Cuenta A a Cuenta B
POST /api/transactions
{
  "account_id": "<uuid-cuenta-a>",
  "transfer_account_id": "<uuid-cuenta-b>",
  "date": "2025-01-21",
  "amount": 200.00,
  "description": "Ahorro mensual",
  "type": "transfer"
}
```

---

**¡Listo para usar! 🎉**
