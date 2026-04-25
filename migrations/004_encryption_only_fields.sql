-- =============================================================================
-- MIGRACIÓN: Encriptación Total - Solo Campos Encriptados
-- =============================================================================
-- Autor: Security Team
-- Fecha: 2026-02-14
-- Descripción: Elimina columnas en claro y renombra *_encrypted → nombre original
--
-- IMPORTANTE: 
-- 1. Hacer BACKUP antes de ejecutar
-- 2. Verificar que migrate_encrypt_data.py se ejecutó (datos ya migrados)
-- 3. Ejecutar en entorno de pruebas primero
--
-- Orden de ejecución:
-- 1. psql -U usuario -d appfinanzas -f 004_encryption_only_fields.sql
-- =============================================================================

-- Iniciar transacción
BEGIN;

-- =============================================================================
-- TABLA: accounts
-- =============================================================================

-- 1. Verificar que balance_encrypted tiene datos (si no, abortar)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM accounts WHERE balance_encrypted IS NOT NULL LIMIT 1
    ) AND EXISTS (
        SELECT 1 FROM accounts WHERE balance IS NOT NULL LIMIT 1
    ) THEN
        RAISE EXCEPTION 'ERROR: balance_encrypted está vacío pero balance tiene datos. Ejecutar migrate_encrypt_data.py primero.';
    END IF;
END $$;

-- 2. Eliminar constraint de balance >= 0 (ya no aplica a texto encriptado)
ALTER TABLE accounts DROP CONSTRAINT IF EXISTS positive_balance;

-- 3. Eliminar columnas en claro
ALTER TABLE accounts DROP COLUMN IF EXISTS balance;
ALTER TABLE accounts DROP COLUMN IF EXISTS account_number;
ALTER TABLE accounts DROP COLUMN IF EXISTS notes;

-- 4. Renombrar columnas encriptadas
ALTER TABLE accounts RENAME COLUMN balance_encrypted TO balance;
ALTER TABLE accounts RENAME COLUMN account_number_encrypted TO account_number;
ALTER TABLE accounts RENAME COLUMN notes_encrypted TO notes;

-- 5. Hacer NOT NULL el balance (ya que es requerido)
-- Convertir NULLs a '0' encriptado (se hará en Python al arrancar)
-- ALTER TABLE accounts ALTER COLUMN balance SET NOT NULL;

RAISE NOTICE 'accounts: Migración completada';

-- =============================================================================
-- TABLA: transactions
-- =============================================================================

-- 1. Verificar datos
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM transactions WHERE amount_encrypted IS NOT NULL LIMIT 1
    ) AND EXISTS (
        SELECT 1 FROM transactions WHERE amount IS NOT NULL LIMIT 1
    ) THEN
        RAISE EXCEPTION 'ERROR: amount_encrypted está vacío pero amount tiene datos. Ejecutar migrate_encrypt_data.py primero.';
    END IF;
END $$;

-- 2. Eliminar constraint de amount != 0
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS non_zero_amount;

-- 3. Eliminar columnas en claro
ALTER TABLE transactions DROP COLUMN IF EXISTS amount;
ALTER TABLE transactions DROP COLUMN IF EXISTS description;

-- 4. Renombrar columnas encriptadas
ALTER TABLE transactions RENAME COLUMN amount_encrypted TO amount;
ALTER TABLE transactions RENAME COLUMN description_encrypted TO description;

RAISE NOTICE 'transactions: Migración completada';

-- =============================================================================
-- TABLA: investments
-- =============================================================================

-- 1. Eliminar columnas en claro
ALTER TABLE investments DROP COLUMN IF EXISTS symbol;
ALTER TABLE investments DROP COLUMN IF EXISTS company_name;
ALTER TABLE investments DROP COLUMN IF EXISTS shares;
ALTER TABLE investments DROP COLUMN IF EXISTS average_price;

-- 2. Renombrar columnas encriptadas
ALTER TABLE investments RENAME COLUMN symbol_encrypted TO symbol;
ALTER TABLE investments RENAME COLUMN company_name_encrypted TO company_name;
ALTER TABLE investments RENAME COLUMN shares_encrypted TO shares;
ALTER TABLE investments RENAME COLUMN average_price_encrypted TO average_price;

RAISE NOTICE 'investments: Migración completada';

-- =============================================================================
-- TABLA: users
-- =============================================================================
-- NOTA: email se mantiene en claro para login

-- 1. Eliminar columnas en claro (excepto email)
ALTER TABLE users DROP COLUMN IF EXISTS full_name;
ALTER TABLE users DROP COLUMN IF EXISTS profile_picture;

-- 2. Renombrar columnas encriptadas
ALTER TABLE users RENAME COLUMN full_name_encrypted TO full_name;
ALTER TABLE users RENAME COLUMN profile_picture_encrypted TO profile_picture;

RAISE NOTICE 'users: Migración completada';

-- =============================================================================
-- VERIFICACIÓN FINAL
-- =============================================================================

-- Mostrar estructura de tablas actualizadas
DO $$
DECLARE
    account_cols TEXT;
    transaction_cols TEXT;
    investment_cols TEXT;
    user_cols TEXT;
BEGIN
    SELECT string_agg(column_name, ', ') INTO account_cols
    FROM information_schema.columns 
    WHERE table_name = 'accounts' AND table_schema = 'public';
    
    SELECT string_agg(column_name, ', ') INTO transaction_cols
    FROM information_schema.columns 
    WHERE table_name = 'transactions' AND table_schema = 'public';
    
    SELECT string_agg(column_name, ', ') INTO investment_cols
    FROM information_schema.columns 
    WHERE table_name = 'investments' AND table_schema = 'public';
    
    SELECT string_agg(column_name, ', ') INTO user_cols
    FROM information_schema.columns 
    WHERE table_name = 'users' AND table_schema = 'public';
    
    RAISE NOTICE '=== ESTRUCTURA FINAL ===';
    RAISE NOTICE 'accounts: %', account_cols;
    RAISE NOTICE 'transactions: %', transaction_cols;
    RAISE NOTICE 'investments: %', investment_cols;
    RAISE NOTICE 'users: %', user_cols;
END $$;

-- Confirmar transacción
COMMIT;

-- =============================================================================
-- VERIFICACIÓN MANUAL RECOMENDADA
-- =============================================================================
-- Después de ejecutar, verificar:
--
-- SELECT column_name, data_type FROM information_schema.columns 
-- WHERE table_name = 'accounts' ORDER BY ordinal_position;
--
-- SELECT id, name, balance FROM accounts LIMIT 1;
-- (balance debería mostrar: "1:nonce:ciphertext:tag")
-- =============================================================================
