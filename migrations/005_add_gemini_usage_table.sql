-- Migration: 005_add_gemini_usage_table.sql
-- Description: Add gemini_usage table for per-user Gemini API quota tracking
-- Date: 2026-04-01
-- Author: Claude AI

-- ============================================
-- Tabla para tracking de uso de Gemini API
-- ============================================

-- Crear tabla gemini_usage
CREATE TABLE IF NOT EXISTS gemini_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    request_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Restricción única: un registro por usuario por día
    CONSTRAINT unique_user_date UNIQUE (user_id, usage_date)
);

-- Índice para búsquedas rápidas por usuario y fecha
CREATE INDEX IF NOT EXISTS idx_gemini_usage_user_date ON gemini_usage(user_id, usage_date);

-- Comentarios de documentación
COMMENT ON TABLE gemini_usage IS 'Rastrea el uso diario de la API de Gemini por usuario para control de cuotas';
COMMENT ON COLUMN gemini_usage.id IS 'Identificador único del registro';
COMMENT ON COLUMN gemini_usage.user_id IS 'Usuario propietario (FK a users.id)';
COMMENT ON COLUMN gemini_usage.usage_date IS 'Fecha del uso (para reset diario automático)';
COMMENT ON COLUMN gemini_usage.request_count IS 'Número de peticiones a Gemini en este día';
COMMENT ON COLUMN gemini_usage.created_at IS 'Fecha de creación del registro';
COMMENT ON COLUMN gemini_usage.updated_at IS 'Fecha de última actualización';

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_gemini_usage_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_gemini_usage_updated_at ON gemini_usage;
CREATE TRIGGER trigger_gemini_usage_updated_at
    BEFORE UPDATE ON gemini_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_gemini_usage_updated_at();

-- ============================================
-- Verificación
-- ============================================
-- Verificar que la tabla se creó correctamente
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'gemini_usage') THEN
        RAISE NOTICE 'Migración 005: Tabla gemini_usage creada correctamente';
    ELSE
        RAISE EXCEPTION 'Error: La tabla gemini_usage no se creó';
    END IF;
END $$;
