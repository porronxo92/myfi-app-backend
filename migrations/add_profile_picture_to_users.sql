-- Migración: Añadir campo profile_picture a la tabla users
-- Fecha: 2026-01-17
-- Descripción: Añade columna para almacenar base64 de foto de perfil o URL

ALTER TABLE users
ADD COLUMN profile_picture TEXT;

COMMENT ON COLUMN users.profile_picture IS 'Base64 de la foto de perfil o URL';
