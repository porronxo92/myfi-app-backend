-- =====================================================
-- MIGRACIÓN: Crear tabla password_reset_tokens
-- =====================================================
-- Ejecutar este script en la base de datos PostgreSQL
-- para habilitar la funcionalidad de "Olvidé mi contraseña"
-- =====================================================

-- Crear extensión uuid-ossp si no existe (para uuid_generate_v4)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear la tabla password_reset_tokens
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Crear índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);

-- Agregar comentarios descriptivos
COMMENT ON TABLE password_reset_tokens IS 'Tokens temporales para restablecer contraseñas';
COMMENT ON COLUMN password_reset_tokens.id IS 'Identificador único del token';
COMMENT ON COLUMN password_reset_tokens.user_id IS 'ID del usuario que solicitó el reset';
COMMENT ON COLUMN password_reset_tokens.token IS 'Hash SHA-256 del token (el token real se envía por email)';
COMMENT ON COLUMN password_reset_tokens.expires_at IS 'Fecha de expiración del token';
COMMENT ON COLUMN password_reset_tokens.used IS 'Indica si el token ya fue utilizado';
COMMENT ON COLUMN password_reset_tokens.created_at IS 'Fecha de creación del token';

-- =====================================================
-- Verificación
-- =====================================================
-- Ejecuta esto para verificar que la tabla se creó correctamente:
-- SELECT * FROM information_schema.tables WHERE table_name = 'password_reset_tokens';
