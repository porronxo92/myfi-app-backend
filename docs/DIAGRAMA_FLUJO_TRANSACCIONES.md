# Diagrama de Flujo - Transacciones con Categorías

## Arquitectura Visual

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENTE (Frontend)                          │
│                                                                     │
│  GET /api/transactions?page=1&page_size=20&type=expense            │
│  Authorization: Bearer JWT_TOKEN                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FASTAPI ROUTER (routes)                          │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ 1. Validar JWT (get_current_user)                         │     │
│  │ 2. Validar parámetros (Query, Pydantic)                   │     │
│  │ 3. Calcular paginación (skip = (page-1) * page_size)      │     │
│  └───────────────────────────────────────────────────────────┘     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 TRANSACTION SERVICE (services)                      │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ TransactionService.get_all()                              │     │
│  │                                                            │     │
│  │ query = db.query(Transaction)                             │     │
│  │   .join(Account)                                          │     │
│  │   .filter(Account.user_id == current_user.id)  ← SEGURIDAD│     │
│  │   .options(                                                │     │
│  │       joinedload(Transaction.account),     ← NO N+1       │     │
│  │       joinedload(Transaction.category)     ← NO N+1       │     │
│  │   )                                                        │     │
│  │   .filter(...)  ← Filtros dinámicos                       │     │
│  │   .order_by(Transaction.date.desc())                      │     │
│  │   .offset(skip).limit(page_size)                          │     │
│  └───────────────────────────────────────────────────────────┘     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   SQLALCHEMY ORM (models)                           │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ class Transaction:                                         │     │
│  │     id, date, amount, description, ...                     │     │
│  │     category_id (FK → categories.id)                       │     │
│  │                                                            │     │
│  │     category = relationship("Category")  ← Relación ORM   │     │
│  │     account = relationship("Account")    ← Relación ORM   │     │
│  └───────────────────────────────────────────────────────────┘     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      POSTGRESQL DATABASE                            │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ SELECT t.*, c.name, c.color, a.name                       │     │
│  │ FROM transactions t                                        │     │
│  │ LEFT JOIN categories c ON t.category_id = c.id            │     │
│  │ LEFT JOIN accounts a ON t.account_id = a.id               │     │
│  │ WHERE a.user_id = 'uuid-user'                             │     │
│  │ ORDER BY t.date DESC                                       │     │
│  │ LIMIT 20 OFFSET 0;                                         │     │
│  │                                                            │     │
│  │ ⭐ UNA SOLA CONSULTA SQL                                  │     │
│  └───────────────────────────────────────────────────────────┘     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RESULTADO (Lista de ORM)                         │
│  [                                                                  │
│    Transaction(id=..., category=Category(name="Supermercado")),    │
│    Transaction(id=..., category=Category(name="Transporte")),      │
│    Transaction(id=..., category=None),                             │
│  ]                                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PYDANTIC TRANSFORMATION (schemas)                      │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ TransactionResponse.model_validate(transaction)           │     │
│  │                                                            │     │
│  │ @model_validator(mode='before')                           │     │
│  │ def populate_relationships(data):                         │     │
│  │     return {                                               │     │
│  │         'id': data.id,                                     │     │
│  │         'description': data.description,                   │     │
│  │         'amount': data.amount,                             │     │
│  │         'account_name': data.account.name,  ← Extrae      │     │
│  │         'category_name': data.category.name, ← Extrae     │     │
│  │         'category_color': data.category.color ← Extrae    │     │
│  │     }                                                      │     │
│  └───────────────────────────────────────────────────────────┘     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      JSON RESPONSE (API)                            │
│  {                                                                  │
│    "items": [                                                       │
│      {                                                              │
│        "id": "uuid-1",                                              │
│        "description": "Mercadona",                                  │
│        "amount": -50.00,                                            │
│        "account_name": "Cuenta Bankinter", ⭐                       │
│        "category_name": "Supermercado",   ⭐                        │
│        "category_color": "#EF4444"        ⭐                        │
│      }                                                              │
│    ],                                                               │
│    "total": 150,                                                    │
│    "page": 1,                                                       │
│    "page_size": 20                                                  │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Problema N+1 - Comparación

### ❌ SIN joinedload() - Problema N+1

```
Query 1: SELECT * FROM transactions WHERE ... LIMIT 20
         → Devuelve 20 transacciones

Query 2: SELECT * FROM categories WHERE id = 'cat-1'
Query 3: SELECT * FROM categories WHERE id = 'cat-2'
Query 4: SELECT * FROM categories WHERE id = 'cat-3'
...
Query 21: SELECT * FROM categories WHERE id = 'cat-20'

Total: 21 consultas SQL
Tiempo: ~500ms (en red lenta)
```

### ✅ CON joinedload() - Solución óptima

```
Query única:
SELECT 
    t.*,
    c.id, c.name, c.color,
    a.id, a.name
FROM transactions t
LEFT JOIN categories c ON t.category_id = c.id
LEFT JOIN accounts a ON t.account_id = a.id
WHERE a.user_id = 'uuid-user'
ORDER BY t.date DESC
LIMIT 20;

Total: 1 consulta SQL
Tiempo: ~50ms
Reducción: 90% más rápido
```

---

## Flujo de Datos Simplificado

```
Usuario hace request
        ↓
    Valida JWT
        ↓
    Llama servicio
        ↓
    Query con JOINs (1 consulta)
        ↓
    ORM devuelve objetos con relaciones cargadas
        ↓
    Pydantic extrae datos de relaciones
        ↓
    JSON con category_name incluido
        ↓
    Frontend recibe todo en una respuesta
```

---

## Capas de Responsabilidad

| Capa       | Responsabilidad                                    | Archivos                          |
|------------|----------------------------------------------------|-----------------------------------|
| **Routes** | HTTP, autenticación, paginación, validación       | `routes/transactions.py`          |
| **Service**| Lógica de negocio, consultas optimizadas          | `services/transaction_service.py` |
| **Models** | Definición de tablas, relaciones ORM              | `models/transaction.py`           |
| **Schemas**| Validación, transformación, serialización         | `schemas/transaction.py`          |
| **Database**| Almacenamiento, índices, constraints             | PostgreSQL                        |

---

## Ventajas de la Arquitectura

| Aspecto          | Beneficio                                                   |
|------------------|-------------------------------------------------------------|
| **Rendimiento**  | 1 consulta vs N+1 consultas                                 |
| **Escalabilidad**| Soporta miles de transacciones sin degradación              |
| **Seguridad**    | Filtro por user_id impide acceso a datos de otros usuarios |
| **Mantenibilidad**| Cada capa tiene una responsabilidad clara                  |
| **Testabilidad** | Fácil de probar cada capa por separado                      |
| **Evolución**    | Agregar filtros/features sin romper compatibilidad          |

---

## Ejemplo de Código Real

```python
# En el frontend (Angular/TypeScript):
this.http.get<PaginatedResponse>('/api/transactions?page=1')
  .subscribe(response => {
    // response.items ya contiene category_name
    this.transactions = response.items;
    
    // Puedes usar directamente:
    transaction.category_name  // "Supermercado"
    transaction.category_color // "#EF4444"
    
    // Sin necesidad de:
    // ❌ this.categoryService.get(transaction.category_id)
  });
```

---

**Conclusión:** Tu arquitectura está perfectamente diseñada para este caso de uso.
