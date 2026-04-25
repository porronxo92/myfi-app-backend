-- ============================================
-- MIGRACIÓN: Agregar campos encriptados (PSD2/GDPR) - EXPANDED
-- ============================================
-- Fecha: 2026-02-11 (Updated)
-- Descripción: Añade columnas encriptadas para TODOS los datos sensibles
-- 
-- ALCANCE AMPLIADO:
--   - users: email, full_name, profile_picture
--   - accounts: account_number, balance, notes
--   - transactions: amount, description
--   - investments: symbol, company_name, shares, average_price
--
-- IMPORTANTE: Ejecutar en este orden:
-- 1. Ejecutar este script SQL para crear las columnas
-- 2. Ejecutar el script Python migrate_encrypt_data.py para migrar datos
-- ============================================

-- ============================================
-- TABLA: users
-- ============================================

-- Columna para email encriptado (aunque el email plano se mantiene para índice único)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS email_encrypted TEXT;

COMMENT ON COLUMN users.email_encrypted IS 'Email encriptado con AES-256-GCM para cumplimiento GDPR';

-- Columna para nombre encriptado
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS full_name_encrypted TEXT;

COMMENT ON COLUMN users.full_name_encrypted IS 'Nombre completo encriptado con AES-256-GCM';

-- Columna para foto de perfil encriptada
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS profile_picture_encrypted TEXT;

COMMENT ON COLUMN users.profile_picture_encrypted IS 'Foto de perfil encriptada con AES-256-GCM';

-- Actualizar comentarios de columnas deprecadas
COMMENT ON COLUMN users.full_name IS '[DEPRECATED] Usar full_name_encrypted - Datos migrados a columna encriptada';
COMMENT ON COLUMN users.profile_picture IS '[DEPRECATED] Usar profile_picture_encrypted - Datos migrados a columna encriptada';

-- ============================================
-- TABLA: accounts
-- ============================================

-- Columna para número de cuenta encriptado
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS account_number_encrypted TEXT;

COMMENT ON COLUMN accounts.account_number_encrypted IS 'IBAN/Número de cuenta encriptado con AES-256-GCM (PSD2)';

-- Columna para notas encriptadas
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS notes_encrypted TEXT;

COMMENT ON COLUMN accounts.notes_encrypted IS 'Notas adicionales encriptadas';

-- Columna para balance encriptado (información financiera crítica)
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS balance_encrypted TEXT;

COMMENT ON COLUMN accounts.balance_encrypted IS 'Saldo encriptado con AES-256-GCM (PSD2 Art.95) - Dato financiero crítico';

-- Actualizar comentarios de columnas deprecadas
COMMENT ON COLUMN accounts.account_number IS '[DEPRECATED] Usar account_number_encrypted - Datos migrados';
COMMENT ON COLUMN accounts.notes IS '[DEPRECATED] Usar notes_encrypted - Datos migrados';
COMMENT ON COLUMN accounts.balance IS '[DEPRECATED] Usar balance_encrypted - Datos migrados';

-- ============================================
-- TABLA: transactions
-- ============================================

-- Columna para importe encriptado
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS amount_encrypted TEXT;

COMMENT ON COLUMN transactions.amount_encrypted IS 'Importe encriptado con AES-256-GCM (PSD2 Art.95) - Revela patrones financieros';

-- Columna para descripción encriptada
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS description_encrypted TEXT;

COMMENT ON COLUMN transactions.description_encrypted IS 'Descripción encriptada con AES-256-GCM (GDPR Art.32) - Protege hábitos de gasto';

-- Actualizar comentarios de columnas deprecadas
COMMENT ON COLUMN transactions.amount IS '[DEPRECATED] Usar amount_encrypted - Datos migrados';
COMMENT ON COLUMN transactions.description IS '[DEPRECATED] Usar description_encrypted - Datos migrados';

-- ============================================
-- TABLA: investments
-- ============================================

-- Columna para ticker/símbolo encriptado
ALTER TABLE investments 
ADD COLUMN IF NOT EXISTS symbol_encrypted TEXT;

COMMENT ON COLUMN investments.symbol_encrypted IS 'Ticker encryptado con AES-256-GCM (PSD2 Art.95) - Protege estrategia de portafolio';

-- Columna para nombre de empresa encriptado
ALTER TABLE investments 
ADD COLUMN IF NOT EXISTS company_name_encrypted TEXT;

COMMENT ON COLUMN investments.company_name_encrypted IS 'Nombre empresa encriptado con AES-256-GCM (GDPR Art.32)';

-- Columna para cantidad de acciones encriptada
ALTER TABLE investments 
ADD COLUMN IF NOT EXISTS shares_encrypted TEXT;

COMMENT ON COLUMN investments.shares_encrypted IS 'Cantidad de acciones encriptada con AES-256-GCM (PSD2 Art.95) - Tamaño de posición sensible';

-- Columna para precio promedio encriptado
ALTER TABLE investments 
ADD COLUMN IF NOT EXISTS average_price_encrypted TEXT;

COMMENT ON COLUMN investments.average_price_encrypted IS 'Precio promedio encriptado con AES-256-GCM (PSD2 Art.95) - Costo de inversión sensible';

-- Actualizar comentarios de columnas deprecadas
COMMENT ON COLUMN investments.symbol IS '[DEPRECATED] Usar symbol_encrypted - Datos migrados';
COMMENT ON COLUMN investments.company_name IS '[DEPRECATED] Usar company_name_encrypted - Datos migrados';
COMMENT ON COLUMN investments.shares IS '[DEPRECATED] Usar shares_encrypted - Datos migrados';
COMMENT ON COLUMN investments.average_price IS '[DEPRECATED] Usar average_price_encrypted - Datos migrados';

-- ============================================
-- ÍNDICES (Opcional, para búsquedas en campos encriptados)
-- ============================================

-- No se crean índices en campos encriptados ya que no son buscables
-- Las búsquedas se hacen por campos no encriptados (email, id)

-- ============================================
-- VERIFICACIÓN
-- ============================================

-- Verificar que las columnas fueron creadas
DO $$
BEGIN
    -- Verificar columnas de users
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'email_encrypted'
    ) THEN
        RAISE EXCEPTION 'Columna users.email_encrypted no fue creada';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'full_name_encrypted'
    ) THEN
        RAISE EXCEPTION 'Columna users.full_name_encrypted no fue creada';
    END IF;
    
    -- Verificar columnas de accounts
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'accounts' AND column_name = 'account_number_encrypted'
    ) THEN
        RAISE EXCEPTION 'Columna accounts.account_number_encrypted no fue creada';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'accounts' AND column_name = 'balance_encrypted'
    ) THEN
        RAISE EXCEPTION 'Columna accounts.balance_encrypted no fue creada';
    END IF;
    
    -- Verificar columnas de transactions
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'amount_encrypted'
    ) THEN
        RAISE EXCEPTION 'Columna transactions.amount_encrypted no fue creada';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'description_encrypted'
    ) THEN
        RAISE EXCEPTION 'Columna transactions.description_encrypted no fue creada';
    END IF;
    
    -- Verificar columnas de investments
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'investments' AND column_name = 'symbol_encrypted'
    ) THEN
        RAISE EXCEPTION 'Columna investments.symbol_encrypted no fue creada';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'investments' AND column_name = 'shares_encrypted'
    ) THEN
        RAISE EXCEPTION 'Columna investments.shares_encrypted no fue creada';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'investments' AND column_name = 'average_price_encrypted'
    ) THEN
        RAISE EXCEPTION 'Columna investments.average_price_encrypted no fue creada';
    END IF;
    
    RAISE NOTICE '✅ Todas las columnas encriptadas fueron creadas correctamente (users, accounts, transactions, investments)';
END $$;

-- ============================================
-- NOTA POST-MIGRACIÓN
-- ============================================
-- 
-- Después de ejecutar el script Python de migración de datos,
-- ejecutar el siguiente comando para limpiar los datos originales:
--
-- UPDATE users SET 
--     full_name = NULL, 
--     profile_picture = NULL 
-- WHERE full_name_encrypted IS NOT NULL OR profile_picture_encrypted IS NOT NULL;
--
-- UPDATE accounts SET 
--     account_number = NULL, 
--     notes = NULL 
-- WHERE account_number_encrypted IS NOT NULL OR notes_encrypted IS NOT NULL;
--
-- ============================================
