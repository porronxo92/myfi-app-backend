# Implementación de Swing Trading - Historial de Ventas

## 📋 Resumen

Se ha implementado un sistema completo de **swing trading** que permite a los usuarios vender posiciones y mantener un historial de transacciones, en lugar de eliminar permanentemente los registros.

## 🎯 Características Implementadas

### 1. **Nuevos Campos en Base de Datos**

#### Enum `investment_status`
```sql
CREATE TYPE investment_status AS ENUM ('active', 'sold', 'watchlist');
```

#### Campos añadidos a tabla `investments`:
- **`status`** (investment_status, NOT NULL, DEFAULT 'active'): Estado de la inversión
- **`sale_price`** (DECIMAL(10,2), NULL): Precio de venta por acción
- **`sale_date`** (DATE, NULL): Fecha de venta

### 2. **Backend - Cambios Realizados**

#### Modelo (`backend/app/models/investment.py`)
✅ Añadido enum `InvestmentStatus` con valores: ACTIVE, SOLD, WATCHLIST  
✅ Añadidos campos: `status`, `sale_price`, `sale_date`  
✅ Índice automático en campo `status`

#### Schemas (`backend/app/schemas/investment.py`)
✅ Nuevo schema `InvestmentSell` para validar datos de venta:
```python
class InvestmentSell(BaseModel):
    sale_price: Decimal  # Precio de venta
    sale_date: date      # Fecha de venta (default: hoy)
    notes: Optional[str] # Notas sobre la venta
```

✅ Actualizado `InvestmentBase` con campos:
- `status`: Literal['active', 'sold', 'watchlist']
- `salePrice` / `sale_price` (con aliases camelCase)
- `saleDate` / `sale_date` (con aliases camelCase)

✅ Actualizado `InvestmentUpdate` para permitir modificar venta

#### Rutas (`backend/app/routes/investments.py`)
✅ **Nuevo endpoint**: `POST /api/investments/{id}/sell`
```python
{
  "salePrice": 185.50,
  "saleDate": "2026-01-13",
  "notes": "Venta por objetivo alcanzado"
}
```
- Marca posición como `status='sold'`
- Registra precio y fecha de venta
- **NO elimina el registro** (mantiene historial)
- Retorna: `InvestmentResponse` con datos actualizados

✅ **Modificado endpoint**: `DELETE /api/investments/{id}`
- Ahora elimina permanentemente (irreversible)
- Documentación actualizada advirtiendo usar `/sell` para mantener historial

#### Servicio (`backend/app/services/investment_service.py`)
✅ `get_user_investments()` ahora filtra solo inversiones activas:
```python
Investment.status == InvestmentStatus.ACTIVE
```

✅ `create_investment()` establece `status=ACTIVE` por defecto

### 3. **Frontend - Cambios Realizados**

#### Servicio (`frontend/src/app/core/services/investment.service.ts`)
✅ Nuevo método `sellPosition()`:
```typescript
sellPosition(id: string, salePrice: number, saleDate: string, notes?: string)
```

#### Componente (`investment.component.ts`)
✅ Nuevo state para modal de venta:
```typescript
showSellModal = signal<boolean>(false);
positionToSell = signal<EnrichedPosition | null>(null);
sellForm = signal({
  salePrice: 0,
  saleDate: string,
  notes: ''
});
```

✅ Nuevos métodos:
- `openSellModal(position)`: Abre modal prellenando precio actual
- `closeSellModal()`: Cierra modal y limpia formulario
- `confirmSell()`: Ejecuta venta y recarga posiciones

#### UI (`investment.component.html`)
✅ **Tabla de inversiones**:
- ❌ Eliminado: Icono de papelera (basura)
- ✅ Añadido: Icono de venta (💰 círculo con $)
- Diseño: Botón naranja al hover

✅ **Nuevo Modal de Venta**:

**Sección 1: Resumen de la Posición**
```
📊 Apple Inc. (AAPL)
Acciones: 10
Precio de Compra: $150.00
Precio Actual: $185.50
Inversión Total: $1,500.00
```

**Sección 2: Formulario de Venta**
- **Precio de Venta*** (number input, prellenado con precio actual)
- **Fecha de Venta*** (date input, prellenado con hoy)
- **Notas** (textarea, opcional)

**Sección 3: Preview de Resultado** (calculado en tiempo real)
```
📈 Resultado Proyectado:
Precio Venta: $185.50
Valor Total Venta: $1,855.00
Ganancia/Pérdida: +$355.00 (+23.67%)
```
- Color verde si ganancia
- Color rojo si pérdida
- Se actualiza automáticamente al cambiar precio

**Botones**:
- Cancelar (gris)
- Confirmar Venta (rojo, disabled si salePrice <= 0)

#### Estilos (`investment.component.scss`)
✅ `.action-buttons`: Contenedor flex para botones de acción  
✅ `.btn-sell`: Botón naranja con icono de moneda  
✅ `.sell-summary`: Tarjeta de resumen de posición  
✅ `.profit-preview`: Preview con colores dinámicos (verde/rojo)  
✅ `.btn-danger`: Botón rojo para confirmar venta

## 📊 Flujo de Trabajo

### Escenario: Vender posición de Apple

1. **Usuario ve tabla de inversiones**
   - Encuentra su posición de AAPL (10 acciones @ $150, valor actual $185.50)
   - Click en icono 💰 (venta)

2. **Se abre Modal de Venta**
   - Muestra resumen completo de la posición
   - Precio de venta prellenado: $185.50 (precio actual)
   - Fecha prellenada: 2026-01-13
   - Preview: "+$355.00 (+23.67%)" en verde

3. **Usuario ajusta (opcional)**
   - Cambia precio a $190.00
   - Preview se actualiza: "+$400.00 (+26.67%)"
   - Añade nota: "Venta por objetivo alcanzado"

4. **Confirma venta**
   - Click en "Confirmar Venta"
   - Backend:
     ```sql
     UPDATE investments SET
       status = 'sold',
       sale_price = 190.00,
       sale_date = '2026-01-13',
       notes = 'Venta por objetivo alcanzado'
     WHERE id = '...'
     ```

5. **Resultado**
   - Modal se cierra
   - Posición desaparece de la tabla (filtrada: `status = 'active'`)
   - Registro permanece en BD con historial completo

## 🗄️ Migración de Base de Datos

**Archivo**: `backend/migrations/add_swing_trading_fields.sql`

**Pasos**:
1. Crear enum `investment_status`
2. Añadir columnas: `status`, `sale_price`, `sale_date`
3. Crear índices para optimizar consultas
4. Actualizar registros existentes a `status='active'`

**Ejecutar**:
```bash
psql -U admin -d app_finance -f backend/migrations/add_swing_trading_fields.sql
```

**Rollback incluido** para deshacer cambios si es necesario.

## 🔍 Índices Creados

```sql
-- Historial de ventas (WHERE clause index)
CREATE INDEX idx_investments_history 
ON investments(user_id, status) 
WHERE status = 'sold';

-- Consultas por estado
CREATE INDEX idx_investments_status 
ON investments(status);
```

## 🎨 Diseño UI

### Icono de Venta
- SVG: Círculo con símbolo de dólar ($)
- Color normal: Gris claro
- Hover: Naranja (#f59e0b) con fondo suave
- Transición suave 0.2s

### Modal de Venta
- Fondo overlay oscuro
- Card centrada con padding generoso
- Colores dinámicos según ganancia/pérdida:
  - Verde: `rgba(7, 136, 59, 0.05)` fondo, `#07883b` texto
  - Rojo: `rgba(185, 28, 28, 0.05)` fondo, `#b91c1c` texto

### Botón de Confirmación
- Rojo peligro (#b91c1c)
- Hover: Más oscuro con elevación
- Disabled: Opacidad 50%

## 📝 Validaciones

### Backend
✅ `sale_price` > 0 (validador Pydantic)  
✅ `sale_date` es fecha válida  
✅ Solo el propietario puede vender su posición  
✅ Actualización atómica con commit/rollback

### Frontend
✅ Precio de venta requerido y > 0  
✅ Fecha requerida  
✅ Botón disabled hasta completar campos obligatorios  
✅ Confirmación visual antes de ejecutar

## 🚀 Ventajas del Sistema

1. **Historial Completo**: No se pierde información de transacciones
2. **Análisis de Performance**: Se puede calcular ROI histórico
3. **Reportes**: Generar informes de ganancias/pérdidas
4. **Auditoría**: Trazabilidad de todas las operaciones
5. **Watchlist**: Futuro seguimiento de acciones sin posición

## 🔮 Futuras Mejoras Sugeridas

- [ ] Vista de historial de ventas (`status='sold'`)
- [ ] Dashboard con métricas de swing trading (win rate, average profit, etc.)
- [ ] Exportar historial a CSV/Excel
- [ ] Gráficos de rendimiento temporal
- [ ] Watchlist activa (`status='watchlist'`)
- [ ] Alertas de precio para watchlist
- [ ] Cálculo automático de impuestos sobre ganancias

## ✅ Testing Recomendado

1. **Crear inversión** → Verificar `status='active'`
2. **Vender posición** → Verificar campos poblados correctamente
3. **Listar posiciones** → Verificar que vendidas no aparecen
4. **Consulta directa BD** → Verificar registro existe con `status='sold'`
5. **Intentar vender posición ya vendida** → Debe fallar (404)
6. **Preview de ganancia/pérdida** → Verificar cálculos correctos

---

**Implementación completada** ✨  
**Fecha**: 2026-01-13  
**Estado**: Listo para producción (requiere migración de BD)
