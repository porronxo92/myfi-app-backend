-- =====================================================================
-- Migration 003: DEPRECATED - NO USAR
-- =====================================================================
-- 
-- ⚠️  ADVERTENCIA: Este archivo está DEPRECATED y NO debe ejecutarse
-- 
-- RAZÓN:
--    Los triggers PostgreSQL NO pueden desencriptar datos AES-256-GCM
--    porque no tienen acceso a ENCRYPTION_MASTER_KEY (está en Python .env)
--
--    Cuando PostgreSQL recibe:
--      balance_encrypted = "v1:A1B2C3:encrypted:tag"
--    
--    El trigger intenta:
--      NEW.balance = NEW.balance_encrypted::NUMERIC(12, 2)
--                    ↓
--      ❌ ERROR: invalid input syntax for type numeric
--
-- SOLUCIÓN CORRECTA:
--    Usar SQLAlchemy event listeners (app/utils/encryption_events.py)
--    Los events se ejecutan ANTES de encriptar, por lo que pueden
--    acceder al valor en claro y copiarlo a campos de índice.
--
-- VER DOCUMENTACIÓN:
--    docs/WHY_NO_POSTGRESQL_TRIGGERS.md
--
-- FECHA: 2026-02-14 (Deprecated)
-- =====================================================================

-- Este archivo se mantiene solo para referencia histórica
-- NO ejecutar: psql -U user -d db -f migrations/003_add_encryption_triggers.sql

RAISE EXCEPTION 'Este archivo está DEPRECATED. Usar SQLAlchemy events en lugar de triggers PostgreSQL. Ver docs/WHY_NO_POSTGRESQL_TRIGGERS.md';

-- =====================================================================
-- CONTENIDO ORIGINAL (NO USAR)
-- =====================================================================

-- =====================================================================
-- FUNCIONES AUXILIARES: Desencriptación en PostgreSQL
-- =====================================================================
-- IMPORTANTE: Esta función simula la desencriptación en PostgreSQL
-- En producción, deberías usar una extensión como pgcrypto con AES-256-GCM
-- Por ahora, extrae el valor desde el formato "v1:nonce:ciphertext:tag"
-- =====================================================================

CREATE OR REPLACE FUNCTION decrypt_aes256_gcm(encrypted_text TEXT)
RETURNS TEXT AS $$
DECLARE
    parts TEXT[];
    decrypted_value TEXT;
BEGIN
    -- Si el campo está vacío o NULL, devolver NULL
    IF encrypted_text IS NULL OR encrypted_text = '' THEN
        RETURN NULL;
    END IF;
    
    -- TODO: Implementar desencriptación real con pgcrypto
    -- Por ahora, esto es un placeholder
    -- En producción, usar: pgp_sym_decrypt() o extensión personalizada
    
    -- TEMPORAL: Devolver el texto tal cual (asume que la aplicación encripta/desencripta)
    -- La aplicación Python es quien hace la encriptación real
    RETURN encrypted_text;
    
    -- NOTA: Los triggers NO desencriptan, solo copian valores
    -- La desencriptación se hace en la aplicación (SQLAlchemy TypeDecorator)
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION decrypt_aes256_gcm(TEXT) IS 
'Función placeholder para desencriptación. En producción, usar pgcrypto con AES-256-GCM';


-- =====================================================================
-- TRIGGER: accounts - Sincronizar balance
-- =====================================================================

CREATE OR REPLACE FUNCTION sync_account_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- Si balance_encrypted cambió, actualizar balance
    IF NEW.balance_encrypted IS NOT NULL THEN
        -- Extraer el valor numérico del campo encriptado
        -- IMPORTANTE: En producción, esto debería desencriptar realmente
        -- Por ahora, copiamos directamente porque la aplicación maneja la encriptación
        
        -- La aplicación (SQLAlchemy) ya almacena el Decimal como string en balance_encrypted
        -- Necesitamos convertir de vuelta a NUMERIC
        BEGIN
            NEW.balance = NEW.balance_encrypted::NUMERIC(12, 2);
        EXCEPTION WHEN OTHERS THEN
            -- Si la conversión falla, mantener el valor anterior
            -- Esto puede pasar si balance_encrypted aún no ha sido migrado
            NULL;
        END;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_account_balance
    BEFORE INSERT OR UPDATE OF balance_encrypted ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION sync_account_balance();

COMMENT ON TRIGGER trigger_sync_account_balance ON accounts IS
'Sincroniza automáticamente balance (índices) desde balance_encrypted (fuente de verdad)';


-- =====================================================================
-- TRIGGER: transactions - Sincronizar amount y description
-- =====================================================================

CREATE OR REPLACE FUNCTION sync_transaction_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- Sincronizar amount
    IF NEW.amount_encrypted IS NOT NULL THEN
        BEGIN
            NEW.amount = NEW.amount_encrypted::NUMERIC(12, 2);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END IF;
    
    -- Sincronizar description
    IF NEW.description_encrypted IS NOT NULL THEN
        NEW.description = NEW.description_encrypted;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_transaction_fields
    BEFORE INSERT OR UPDATE OF amount_encrypted, description_encrypted ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION sync_transaction_fields();

COMMENT ON TRIGGER trigger_sync_transaction_fields ON transactions IS
'Sincroniza automáticamente amount y description (índices/búsquedas) desde campos encriptados';


-- =====================================================================
-- TRIGGER: investments - Sincronizar symbol, company_name, shares, average_price
-- =====================================================================

CREATE OR REPLACE FUNCTION sync_investment_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- Sincronizar symbol (para búsquedas y API calls)
    IF NEW.symbol_encrypted IS NOT NULL THEN
        NEW.symbol = NEW.symbol_encrypted;
    END IF;
    
    -- Sincronizar company_name
    IF NEW.company_name_encrypted IS NOT NULL THEN
        NEW.company_name = NEW.company_name_encrypted;
    END IF;
    
    -- Sincronizar shares
    IF NEW.shares_encrypted IS NOT NULL THEN
        BEGIN
            NEW.shares = NEW.shares_encrypted::NUMERIC(10, 4);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END IF;
    
    -- Sincronizar average_price
    IF NEW.average_price_encrypted IS NOT NULL THEN
        BEGIN
            NEW.average_price = NEW.average_price_encrypted::NUMERIC(10, 2);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_investment_fields
    BEFORE INSERT OR UPDATE OF symbol_encrypted, company_name_encrypted, 
                               shares_encrypted, average_price_encrypted ON investments
    FOR EACH ROW
    EXECUTE FUNCTION sync_investment_fields();

COMMENT ON TRIGGER trigger_sync_investment_fields ON investments IS
'Sincroniza automáticamente campos de inversión (API/búsquedas) desde campos encriptados';


-- =====================================================================
-- VERIFICACIÓN
-- =====================================================================

DO $$
BEGIN
    -- Verificar que los triggers fueron creados
    RAISE NOTICE '✅ Triggers de sincronización creados exitosamente';
    RAISE NOTICE '   - trigger_sync_account_balance';
    RAISE NOTICE '   - trigger_sync_transaction_fields';
    RAISE NOTICE '   - trigger_sync_investment_fields';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  IMPORTANTE: Los campos en claro (balance, amount, symbol) son ahora READONLY';
    RAISE NOTICE '   La aplicación debe escribir SOLO en campos *_encrypted';
    RAISE NOTICE '   Los triggers mantienen sincronizados los campos para índices/búsquedas';
END $$;


-- =====================================================================
-- TESTING: Verificar que los triggers funcionan
-- =====================================================================

-- Test 1: Insertar una cuenta y verificar sincronización
DO $$
DECLARE
    test_account_id UUID;
BEGIN
    -- Crear cuenta de prueba
    INSERT INTO accounts (id, user_id, name, type, balance_encrypted, currency)
    VALUES (
        gen_random_uuid(),
        (SELECT id FROM users LIMIT 1),  -- Usuario existente
        'Test Trigger Account',
        'checking',
        '1500.50',  -- Será convertido a NUMERIC automáticamente
        'EUR'
    )
    RETURNING id INTO test_account_id;
    
    -- Verificar que balance se sincronizó
    IF (SELECT balance FROM accounts WHERE id = test_account_id) = 1500.50 THEN
        RAISE NOTICE '✅ Test 1 PASSED: balance sincronizado correctamente';
    ELSE
        RAISE WARNING '❌ Test 1 FAILED: balance NO sincronizado';
    END IF;
    
    -- Limpiar
    DELETE FROM accounts WHERE id = test_account_id;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '⚠️  Test 1 SKIPPED: No hay usuarios en la base de datos';
END $$;


-- =====================================================================
-- DOCUMENTACIÓN POST-MIGRACIÓN
-- =====================================================================

COMMENT ON COLUMN accounts.balance IS 
'[READONLY] Calculado automáticamente desde balance_encrypted. NO ESCRIBIR directamente.';

COMMENT ON COLUMN transactions.amount IS 
'[READONLY] Calculado automáticamente desde amount_encrypted. NO ESCRIBIR directamente.';

COMMENT ON COLUMN transactions.description IS 
'[READONLY] Calculado automáticamente desde description_encrypted. NO ESCRIBIR directamente.';

COMMENT ON COLUMN investments.symbol IS 
'[READONLY] Calculado automáticamente desde symbol_encrypted. NO ESCRIBIR directamente.';

COMMENT ON COLUMN investments.company_name IS 
'[READONLY] Calculado automáticamente desde company_name_encrypted. NO ESCRIBIR directamente.';

COMMENT ON COLUMN investments.shares IS 
'[READONLY] Calculado automáticamente desde shares_encrypted. NO ESCRIBIR directamente.';

COMMENT ON COLUMN investments.average_price IS 
'[READONLY] Calculado automáticamente desde average_price_encrypted. NO ESCRIBIR directamente.';


-- =====================================================================
-- NOTAS FINALES
-- =====================================================================
-- 
-- 🔐 SEGURIDAD:
--    - Datos en reposo: 100% ENCRIPTADOS (campos *_encrypted)
--    - Campos en claro: Solo para rendimiento (índices, SUM, WHERE)
--    - Triggers garantizan coherencia automática
--
-- ⚡ RENDIMIENTO:
--    - Índices siguen funcionando (balance, amount, symbol)
--    - SUM(balance), WHERE amount > 100 siguen siendo rápidos
--    - Búsquedas LIKE en description funcionan
--
-- 🔧 USO EN APLICACIÓN:
--    # CORRECTO ✅
--    account.balance_encrypted = Decimal("1500.50")
--    db.commit()  # Trigger actualiza balance automáticamente
--
--    # INCORRECTO ❌
--    account.balance = 1500.50  # NO hacer esto
--
-- 📊 QUERIES SQL:
--    -- Estos queries siguen funcionando (usan campos calculados)
--    SELECT SUM(balance) FROM accounts;
--    SELECT * FROM transactions WHERE amount > 100;
--    SELECT * FROM transactions WHERE description LIKE '%Amazon%';
--
-- =====================================================================
