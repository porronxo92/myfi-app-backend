-- ============================================
-- SCRIPT SQL: Creación de tabla USERS
-- Base de datos: app_finance (PostgreSQL)
-- ============================================

-- Crear la tabla users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(50) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_email_format CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- Crear índices para optimizar búsquedas
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Comentarios en la tabla y columnas
COMMENT ON TABLE users IS 'Usuarios del sistema de gestión financiera';
COMMENT ON COLUMN users.id IS 'Identificador único del usuario';
COMMENT ON COLUMN users.email IS 'Email del usuario (único)';
COMMENT ON COLUMN users.username IS 'Nombre de usuario (único, opcional)';
COMMENT ON COLUMN users.password_hash IS 'Hash de la contraseña (bcrypt)';
COMMENT ON COLUMN users.full_name IS 'Nombre completo del usuario';
COMMENT ON COLUMN users.is_active IS 'Si el usuario está activo';
COMMENT ON COLUMN users.is_admin IS 'Si el usuario tiene permisos de administrador';
COMMENT ON COLUMN users.last_login IS 'Última fecha de login';
COMMENT ON COLUMN users.created_at IS 'Fecha de creación del registro';
COMMENT ON COLUMN users.updated_at IS 'Fecha de última actualización';

-- ============================================
-- MODIFICAR tabla ACCOUNTS para agregar relación con USERS
-- ============================================

-- Agregar columna user_id a la tabla accounts
ALTER TABLE accounts 
ADD COLUMN user_id UUID;

-- Agregar foreign key constraint
ALTER TABLE accounts
ADD CONSTRAINT fk_accounts_user 
FOREIGN KEY (user_id) 
REFERENCES users(id) 
ON DELETE CASCADE;

-- Crear índice para optimizar JOINs
CREATE INDEX idx_accounts_user_id ON accounts(user_id);

-- Comentario en la columna
COMMENT ON COLUMN accounts.user_id IS 'Usuario propietario de la cuenta (FK a users.id)';

-- ============================================
-- DATOS DE EJEMPLO (OPCIONAL)
-- ============================================

-- Crear usuario de prueba
-- Password: "Test123!" (hasheado con bcrypt)
INSERT INTO users (email, username, password_hash, full_name, is_active, is_admin)
VALUES (
    'admin@example.com',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIpKLKFyXe', -- Password: Test123!
    'Administrador del Sistema',
    TRUE,
    TRUE
);

-- Crear usuario regular de prueba
-- Password: "User123!" (hasheado con bcrypt)
INSERT INTO users (email, username, password_hash, full_name, is_active, is_admin)
VALUES (
    'user@example.com',
    'usuario',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- Password: User123!
    'Usuario Regular',
    TRUE,
    FALSE
);

-- Opcional: Asignar cuentas existentes al usuario admin
-- (Solo si ya tienes cuentas en la tabla accounts)
-- UPDATE accounts SET user_id = (SELECT id FROM users WHERE email = 'admin@example.com' LIMIT 1);

-- ============================================
-- VERIFICACIÓN
-- ============================================

-- Verificar que la tabla se creó correctamente
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;

-- Verificar constraints
SELECT
    tc.constraint_name,
    tc.constraint_type,
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'users';

-- Contar usuarios creados
SELECT COUNT(*) as total_users FROM users;

-- Ver usuarios de ejemplo
SELECT id, email, username, full_name, is_active, is_admin, created_at 
FROM users;
