# Database Migration - Budgets Tables

## SQL Script to Create Budget Tables

Run this SQL script in your PostgreSQL database to create the necessary tables for the Budget module:

```sql
-- ============================================
-- TABLA: budgets
-- ============================================
CREATE TABLE IF NOT EXISTS budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
    year INTEGER NOT NULL CHECK (year >= 2000 AND year <= 2100),
    total_budget DECIMAL(12, 2) NOT NULL DEFAULT 0 CHECK (total_budget >= 0),
    name VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Constraint: Un solo presupuesto por mes/año por usuario
    CONSTRAINT unique_budget_per_month UNIQUE (user_id, month, year)
);

-- Índices para mejorar performance
CREATE INDEX idx_budgets_user_id ON budgets(user_id);
CREATE INDEX idx_budgets_period ON budgets(year, month);

-- Comentarios
COMMENT ON TABLE budgets IS 'Presupuestos mensuales de usuarios';
COMMENT ON COLUMN budgets.id IS 'Identificador único del presupuesto';
COMMENT ON COLUMN budgets.user_id IS 'Usuario propietario del presupuesto';
COMMENT ON COLUMN budgets.month IS 'Mes del presupuesto (1-12)';
COMMENT ON COLUMN budgets.year IS 'Año del presupuesto';
COMMENT ON COLUMN budgets.total_budget IS 'Presupuesto total mensual (suma de todas las partidas)';
COMMENT ON COLUMN budgets.name IS 'Nombre opcional del presupuesto';

-- ============================================
-- TABLA: budget_items
-- ============================================
CREATE TABLE IF NOT EXISTS budget_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    budget_id UUID NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    allocated_amount DECIMAL(12, 2) NOT NULL CHECK (allocated_amount >= 0),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Constraint: Cada categoría aparece solo una vez por presupuesto
    CONSTRAINT unique_category_per_budget UNIQUE (budget_id, category_id)
);

-- Índices para mejorar performance
CREATE INDEX idx_budget_items_budget_id ON budget_items(budget_id);
CREATE INDEX idx_budget_items_category_id ON budget_items(category_id);

-- Comentarios
COMMENT ON TABLE budget_items IS 'Partidas individuales de presupuestos';
COMMENT ON COLUMN budget_items.id IS 'Identificador único de la partida';
COMMENT ON COLUMN budget_items.budget_id IS 'ID del presupuesto padre';
COMMENT ON COLUMN budget_items.category_id IS 'ID de la categoría de gasto';
COMMENT ON COLUMN budget_items.allocated_amount IS 'Cantidad asignada a esta partida';
COMMENT ON COLUMN budget_items.notes IS 'Notas opcionales sobre esta partida';

-- ============================================
-- TRIGGER: Actualizar updated_at automáticamente
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para budgets
CREATE TRIGGER update_budgets_updated_at 
    BEFORE UPDATE ON budgets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger para budget_items
CREATE TRIGGER update_budget_items_updated_at 
    BEFORE UPDATE ON budget_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- DATOS DE PRUEBA (Opcional)
-- ============================================
/*
-- Ejemplo de presupuesto de prueba
-- Reemplaza 'YOUR_USER_ID' con un ID de usuario válido
-- Reemplaza 'CATEGORY_ID_X' con IDs de categorías válidas

INSERT INTO budgets (user_id, month, year, name, total_budget)
VALUES 
    ('YOUR_USER_ID', 1, 2026, 'Enero 2026 - Plan de Ahorro', 2500.00);

-- Obtener el ID del presupuesto recién creado
WITH new_budget AS (
    SELECT id FROM budgets 
    WHERE user_id = 'YOUR_USER_ID' 
    AND month = 1 
    AND year = 2026
)
INSERT INTO budget_items (budget_id, category_id, allocated_amount, notes)
VALUES 
    ((SELECT id FROM new_budget), 'CATEGORY_ID_1', 500.00, 'Alimentación y supermercado'),
    ((SELECT id FROM new_budget), 'CATEGORY_ID_2', 300.00, 'Transporte'),
    ((SELECT id FROM new_budget), 'CATEGORY_ID_3', 800.00, 'Vivienda y servicios'),
    ((SELECT id FROM new_budget), 'CATEGORY_ID_4', 200.00, 'Ocio y entretenimiento'),
    ((SELECT id FROM new_budget), 'CATEGORY_ID_5', 700.00, 'Ahorro e inversión');
*/
```

## Verificación de la Instalación

Para verificar que las tablas se crearon correctamente:

```sql
-- Ver estructura de la tabla budgets
\d budgets

-- Ver estructura de la tabla budget_items
\d budget_items

-- Contar registros (debe ser 0 inicialmente)
SELECT COUNT(*) FROM budgets;
SELECT COUNT(*) FROM budget_items;

-- Verificar constraints
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid IN ('budgets'::regclass, 'budget_items'::regclass);
```

## Rollback (Si es necesario deshacer)

```sql
-- CUIDADO: Esto eliminará todas las tablas y datos del módulo de presupuestos
DROP TRIGGER IF EXISTS update_budget_items_updated_at ON budget_items;
DROP TRIGGER IF EXISTS update_budgets_updated_at ON budgets;
DROP TABLE IF EXISTS budget_items CASCADE;
DROP TABLE IF EXISTS budgets CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column();
```

## Notas Importantes

1. **Dependencias**: Estas tablas requieren que existan previamente:
   - Tabla `users` (para la relación user_id)
   - Tabla `categories` (para la relación category_id)

2. **Permisos**: Asegúrate de que el usuario de la aplicación tenga permisos para:
   - SELECT, INSERT, UPDATE, DELETE en ambas tablas
   - Ejecutar las funciones de trigger

3. **Cascada**: 
   - Si se elimina un presupuesto, se eliminan automáticamente todas sus partidas (CASCADE)
   - Si se elimina un usuario, se eliminan todos sus presupuestos y partidas
   - NO se puede eliminar una categoría si está siendo usada en alguna partida (RESTRICT)

4. **Unique Constraints**:
   - Un usuario solo puede tener UN presupuesto por mes/año
   - Dentro de un presupuesto, cada categoría puede aparecer solo UNA vez

## Alembic Migration (Alternativa)

Si prefieres usar Alembic para las migraciones:

```bash
# Crear nueva migración
alembic revision --autogenerate -m "Add budgets and budget_items tables"

# Aplicar migración
alembic upgrade head

# Revertir migración (si es necesario)
alembic downgrade -1
```

El modelo SQLAlchemy ya está definido en `backend/app/models/budget.py` y `backend/app/models/budget_item.py`, así que Alembic lo detectará automáticamente.
