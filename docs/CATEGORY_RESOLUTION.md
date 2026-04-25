# 🔄 Resolución de Categorías por ID o Nombre

## 📌 Descripción

El endpoint `POST /api/transactions` ahora acepta el campo de categoría en **DOS FORMATOS**:
1. **UUID** (comportamiento original)
2. **Nombre de categoría** (nuevo)

Esto permite mayor flexibilidad al crear transacciones desde diferentes fuentes (frontend, importación de archivos, scripts, etc.).

---

## 🎯 Casos de Uso

### **Opción 1: Envío por UUID**
```json
POST /api/transactions
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "date": "2025-01-15",
  "amount": -50.00,
  "description": "Mercadona",
  "category_id": "660e8400-e29b-41d4-a716-446655440001",
  "type": "expense"
}
```
✅ **Comportamiento**: Valida que el UUID existe en la base de datos y crea la transacción

---

### **Opción 2: Envío por Nombre**
```json
POST /api/transactions
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "date": "2025-01-15",
  "amount": -50.00,
  "description": "Mercadona",
  "category_id": "Alimentación",
  "type": "expense"
}
```
✅ **Comportamiento**:
1. Detecta que `category_id` es un string
2. Busca la categoría por nombre (case-insensitive)
3. Resuelve el UUID correspondiente
4. Crea la transacción con el UUID resuelto

---

### **Opción 3: Campo Alternativo 'categoria'**
```json
POST /api/transactions
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "categoria": "Alimentación",
  "date": "2025-01-15",
  "amount": -50.00,
  "description": "Mercadona",
  "type": "expense"
}
```
✅ **Comportamiento**: El campo `categoria` tiene prioridad sobre `category_id`

---

## 🔍 Lógica de Resolución

### **1. Detección de Tipo**
```python
if isinstance(category_id, str):
    # Buscar por nombre
    category = CategoryService.get_by_name(db, category_id)
    resolved_category_id = category.id
else:
    # Usar UUID directamente
    resolved_category_id = category_id
```

### **2. Búsqueda Case-Insensitive**
La búsqueda por nombre **NO distingue mayúsculas/minúsculas**:

| Input | Match |
|-------|-------|
| `"Alimentación"` | ✅ |
| `"alimentación"` | ✅ |
| `"ALIMENTACIÓN"` | ✅ |
| `"  Alimentación  "` | ✅ (trim automático) |

### **3. Normalización**
Se aplica **automáticamente**:
- ✅ **Trim**: Se eliminan espacios en blanco al inicio y final
- ✅ **Case-insensitive**: No importan mayúsculas/minúsculas

---

## ⚠️ Manejo de Errores

### **Categoría No Encontrada (por nombre)**
```json
POST /api/transactions
{
  "category_id": "CategoríaInexistente",
  ...
}
```
**Response: 400 Bad Request**
```json
{
  "detail": "Categoría 'CategoríaInexistente' no encontrada"
}
```

---

### **UUID No Existe**
```json
POST /api/transactions
{
  "category_id": "999e8400-e29b-41d4-a716-446655440999",
  ...
}
```
**Response: 400 Bad Request**
```json
{
  "detail": "Error al crear transacción: ..."
}
```

---

## 📊 Tabla de Códigos de Error

| Código | Escenario | Mensaje |
|--------|-----------|---------|
| `201` | UUID válido | Transacción creada exitosamente |
| `201` | Nombre válido | Transacción creada exitosamente |
| `400` | Nombre no existe | `"Categoría '{nombre}' no encontrada"` |
| `400` | UUID inválido | `"Error al crear transacción"` |
| `400` | Campo vacío | Validación de Pydantic |
| `400` | Cuenta no pertenece al usuario | `"La cuenta no existe o no pertenece al usuario"` |

---

## 🔧 Implementación Técnica

### **Archivos Modificados**

1. **`backend/app/schemas/transaction.py`**
   - Campo `category_id` ahora es `Union[UUID4, str]`
   - Campo alternativo `categoria` agregado
   - Validadores para normalización y prioridad

2. **`backend/app/services/category_service.py`**
   - Método `get_by_name()` mejorado con búsqueda case-insensitive
   - Logging detallado

3. **`backend/app/services/transaction_service.py`**
   - Lógica de resolución automática en `create()`
   - Detección de tipo (UUID vs string)
   - Validación y error handling

4. **`backend/app/routes/transactions.py`**
   - Documentación actualizada en docstring del endpoint

---

## ✅ Validaciones Implementadas

- [x] Acepta `category_id` como UUID
- [x] Acepta `category_id` como string (nombre)
- [x] Acepta campo alternativo `categoria`
- [x] Búsqueda case-insensitive
- [x] Trim automático
- [x] Errores descriptivos y específicos
- [x] Retrocompatibilidad garantizada
- [x] Logging detallado

---

## 🧪 Ejemplos de Prueba

### **Test 1: Por UUID (comportamiento original)**
```bash
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "550e8400-e29b-41d4-a716-446655440000",
    "date": "2025-01-15",
    "amount": -50.00,
    "description": "Test UUID",
    "category_id": "660e8400-e29b-41d4-a716-446655440001",
    "type": "expense"
  }'
```

### **Test 2: Por Nombre**
```bash
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "550e8400-e29b-41d4-a716-446655440000",
    "date": "2025-01-15",
    "amount": -30.00,
    "description": "Test Nombre",
    "category_id": "Alimentación",
    "type": "expense"
  }'
```

### **Test 3: Con Campo 'categoria'**
```bash
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "550e8400-e29b-41d4-a716-446655440000",
    "categoria": "Transporte",
    "date": "2025-01-15",
    "amount": -25.00,
    "description": "Test Campo Alternativo",
    "type": "expense"
  }'
```

### **Test 4: Nombre con Mayúsculas**
```bash
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "550e8400-e29b-41d4-a716-446655440000",
    "category_id": "ALIMENTACIÓN",
    "date": "2025-01-15",
    "amount": -40.00,
    "description": "Test Case Insensitive",
    "type": "expense"
  }'
```

### **Test 5: Nombre con Espacios**
```bash
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "550e8400-e29b-41d4-a716-446655440000",
    "category_id": "  Alimentación  ",
    "date": "2025-01-15",
    "amount": -35.00,
    "description": "Test Trim",
    "type": "expense"
  }'
```

### **Test 6: Categoría No Existe**
```bash
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "550e8400-e29b-41d4-a716-446655440000",
    "category_id": "CategoríaInexistente",
    "date": "2025-01-15",
    "amount": -20.00,
    "description": "Test Error",
    "type": "expense"
  }'
```
**Expected**: `400 Bad Request` con mensaje `"Categoría 'CategoríaInexistente' no encontrada"`

---

## 📝 Notas Importantes

1. **Retrocompatibilidad**: ✅ Las integraciones existentes que usan UUID siguen funcionando sin cambios

2. **Performance**: La búsqueda por nombre usa índices de base de datos (si existen en la columna `name`)

3. **Unicidad**: Si hay múltiples categorías con nombres similares, usa coincidencia exacta (case-insensitive)

4. **Logging**: Todas las operaciones de resolución están logueadas para debugging

---

## 🔐 Consideraciones de Seguridad

- ✅ La búsqueda por nombre NO expone categorías de otros usuarios
- ✅ Las validaciones se aplican en el backend (no se confía en el frontend)
- ✅ Los errores NO revelan información sensible de la base de datos

---

## 📅 Fecha de Implementación

**31 de Diciembre de 2025**

---

## 🎉 Beneficios

1. **Flexibilidad**: Permite crear transacciones desde múltiples fuentes
2. **UX Mejorada**: Los usuarios pueden usar nombres legibles
3. **Importación Simplificada**: Al importar archivos CSV/Excel, se pueden usar nombres directamente
4. **Backward Compatible**: No rompe código existente
5. **Case-Insensitive**: Menos errores por diferencias de capitalización
