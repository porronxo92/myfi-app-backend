-- ==============================================
-- Migración: Crear tabla chat_sessions
-- Fecha: 2026-04-09
-- Descripción: Añade soporte para sesiones de chat del servidor
-- ==============================================

-- Crear tabla de sesiones de chat
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    history TEXT,  -- JSON encriptado con el historial de mensajes
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Índice para búsqueda rápida por usuario
CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions(user_id);

-- Índice para sesiones activas
CREATE INDEX IF NOT EXISTS ix_chat_sessions_active ON chat_sessions(user_id, is_active)
    WHERE is_active = TRUE;

-- Índice para limpieza de sesiones expiradas
CREATE INDEX IF NOT EXISTS ix_chat_sessions_expires ON chat_sessions(expires_at)
    WHERE is_active = TRUE;

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_chat_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_chat_sessions_timestamp ON chat_sessions;
CREATE TRIGGER update_chat_sessions_timestamp
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_sessions_updated_at();

-- Comentarios de documentación
COMMENT ON TABLE chat_sessions IS 'Sesiones de chat almacenadas en servidor para seguridad';
COMMENT ON COLUMN chat_sessions.history IS 'Historial de mensajes en JSON (encriptado)';
COMMENT ON COLUMN chat_sessions.expires_at IS 'Fecha de expiración automática de la sesión';
