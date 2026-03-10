-- =============================================================
-- SCHEMA: app_finance
-- Generado: 2026-03-10 (limpio, sin datos)
-- PostgreSQL 15
-- =============================================================

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

-- =============================================================
-- EXTENSIONES
-- =============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;
COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


-- =============================================================
-- TIPOS PERSONALIZADOS (ENUM)
-- =============================================================

CREATE TYPE public.investment_status AS ENUM (
    'active',
    'sold',
    'watchlist',
    'pending'
);


-- =============================================================
-- FUNCIONES
-- =============================================================

CREATE FUNCTION public.calculate_account_balance(p_account_id uuid) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_balance NUMERIC;
BEGIN
    SELECT COALESCE(SUM(amount), 0)
    INTO v_balance
    FROM transactions
    WHERE account_id = p_account_id;
    
    RETURN v_balance;
END;
$$;
COMMENT ON FUNCTION public.calculate_account_balance(p_account_id uuid) IS 'Calcula el balance total de una cuenta sumando todas sus transacciones';


CREATE FUNCTION public.update_budgets_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


-- =============================================================
-- TABLAS
-- =============================================================

-- ------------------------------------------------------------
-- users
-- ------------------------------------------------------------
CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    username character varying(50),
    password_hash character varying(255) NOT NULL,
    full_name character varying(100),
    is_active boolean DEFAULT true NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    last_login timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    profile_picture text,
    email_encrypted text,
    full_name_encrypted text,
    profile_picture_encrypted text,
    CONSTRAINT valid_email_format CHECK (((email)::text ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'::text))
);

COMMENT ON TABLE public.users IS 'Usuarios del sistema de gestión financiera';
COMMENT ON COLUMN public.users.id IS 'Identificador único del usuario';
COMMENT ON COLUMN public.users.email IS 'Email del usuario (único)';
COMMENT ON COLUMN public.users.username IS 'Nombre de usuario (único, opcional)';
COMMENT ON COLUMN public.users.password_hash IS 'Hash de la contraseña (bcrypt)';
COMMENT ON COLUMN public.users.full_name IS '[DEPRECATED] Usar full_name_encrypted - Datos migrados a columna encriptada';
COMMENT ON COLUMN public.users.is_active IS 'Si el usuario está activo';
COMMENT ON COLUMN public.users.is_admin IS 'Si el usuario tiene permisos de administrador';
COMMENT ON COLUMN public.users.last_login IS 'Última fecha de login';
COMMENT ON COLUMN public.users.created_at IS 'Fecha de creación del registro';
COMMENT ON COLUMN public.users.updated_at IS 'Fecha de última actualización';
COMMENT ON COLUMN public.users.profile_picture IS '[DEPRECATED] Usar profile_picture_encrypted - Datos migrados a columna encriptada';
COMMENT ON COLUMN public.users.email_encrypted IS 'Email encriptado con AES-256-GCM para cumplimiento GDPR';
COMMENT ON COLUMN public.users.full_name_encrypted IS 'Nombre completo encriptado con AES-256-GCM';
COMMENT ON COLUMN public.users.profile_picture_encrypted IS 'Foto de perfil encriptada con AES-256-GCM';


-- ------------------------------------------------------------
-- accounts
-- ------------------------------------------------------------
CREATE TABLE public.accounts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(100) NOT NULL,
    type character varying(20) NOT NULL,
    balance numeric(12,2) DEFAULT 0.00 NOT NULL,
    currency character varying(3) DEFAULT 'EUR'::character varying NOT NULL,
    bank_name character varying(100),
    account_number character varying(50),
    is_active boolean DEFAULT true NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    user_id uuid,
    account_number_encrypted text,
    notes_encrypted text,
    balance_encrypted text,
    CONSTRAINT accounts_type_check CHECK (((type)::text = ANY ((ARRAY['checking'::character varying, 'savings'::character varying, 'investment'::character varying, 'credit_card'::character varying, 'cash'::character varying])::text[])))
);

COMMENT ON TABLE public.accounts IS 'Cuentas bancarias y de inversión del usuario';
COMMENT ON COLUMN public.accounts.type IS 'Tipos: checking (corriente), savings (ahorro), investment (inversión), credit_card (tarjeta), cash (efectivo)';
COMMENT ON COLUMN public.accounts.balance IS '[DEPRECATED] Usar balance_encrypted - Datos migrados';
COMMENT ON COLUMN public.accounts.account_number IS '[DEPRECATED] Usar account_number_encrypted - Datos migrados';
COMMENT ON COLUMN public.accounts.notes IS '[DEPRECATED] Usar notes_encrypted - Datos migrados';
COMMENT ON COLUMN public.accounts.user_id IS 'Usuario propietario de la cuenta (FK a users.id)';
COMMENT ON COLUMN public.accounts.account_number_encrypted IS 'IBAN/Número de cuenta encriptado con AES-256-GCM (PSD2)';
COMMENT ON COLUMN public.accounts.notes_encrypted IS 'Notas adicionales encriptadas';
COMMENT ON COLUMN public.accounts.balance_encrypted IS 'Saldo encriptado con AES-256-GCM (PSD2 Art.95) - Dato financiero crítico';


-- ------------------------------------------------------------
-- categories
-- ------------------------------------------------------------
CREATE TABLE public.categories (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(100) NOT NULL,
    type character varying(20) NOT NULL,
    color character varying(7) DEFAULT '#6B7280'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT categories_type_check CHECK (((type)::text = ANY ((ARRAY['income'::character varying, 'expense'::character varying])::text[])))
);

COMMENT ON TABLE public.categories IS 'Categorías de ingresos y gastos';
COMMENT ON COLUMN public.categories.type IS 'Tipo: income (ingreso) o expense (gasto)';
COMMENT ON COLUMN public.categories.color IS 'Color hexadecimal para visualización';


-- ------------------------------------------------------------
-- transactions
-- ------------------------------------------------------------
CREATE TABLE public.transactions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    account_id uuid NOT NULL,
    date date NOT NULL,
    amount numeric(12,2) NOT NULL,
    description character varying(500) NOT NULL,
    type character varying(20) NOT NULL,
    transfer_account_id uuid,
    notes text,
    tags text[],
    external_id character varying(100),
    source character varying(50) DEFAULT 'manual'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    category_id uuid,
    amount_encrypted text,
    description_encrypted text,
    CONSTRAINT check_transfer_account CHECK (((((type)::text = 'transfer'::text) AND (transfer_account_id IS NOT NULL)) OR ((type)::text <> 'transfer'::text))),
    CONSTRAINT transactions_type_check CHECK (((type)::text = ANY ((ARRAY['income'::character varying, 'expense'::character varying, 'transfer'::character varying])::text[])))
);

COMMENT ON TABLE public.transactions IS 'Todas las transacciones financieras (ingresos, gastos, transferencias)';
COMMENT ON COLUMN public.transactions.amount IS '[DEPRECATED] Usar amount_encrypted - Datos migrados';
COMMENT ON COLUMN public.transactions.description IS '[DEPRECATED] Usar description_encrypted - Datos migrados';
COMMENT ON COLUMN public.transactions.type IS 'Tipo de movimiento: income (ingreso), expense (gasto), transfer (transferencia)';
COMMENT ON COLUMN public.transactions.transfer_account_id IS 'Cuenta destino si es una transferencia interna';
COMMENT ON COLUMN public.transactions.external_id IS 'ID único del banco para evitar duplicados en importaciones';
COMMENT ON COLUMN public.transactions.category_id IS 'Categoría de la transacción (FK a categories)';
COMMENT ON COLUMN public.transactions.amount_encrypted IS 'Importe encriptado con AES-256-GCM (PSD2 Art.95) - Revela patrones financieros';
COMMENT ON COLUMN public.transactions.description_encrypted IS 'Descripción encriptada con AES-256-GCM (GDPR Art.32) - Protege hábitos de gasto';


-- ------------------------------------------------------------
-- investments
-- ------------------------------------------------------------
CREATE TABLE public.investments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    symbol character varying(10) NOT NULL,
    company_name character varying(255) NOT NULL,
    shares numeric(10,4) NOT NULL,
    average_price numeric(10,2) NOT NULL,
    purchase_date date NOT NULL,
    sale_price numeric(10,2),
    sale_date date,
    status public.investment_status DEFAULT 'active'::public.investment_status NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    symbol_encrypted text,
    company_name_encrypted text,
    shares_encrypted text,
    average_price_encrypted text
);

COMMENT ON COLUMN public.investments.symbol IS '[DEPRECATED] Usar symbol_encrypted - Datos migrados';
COMMENT ON COLUMN public.investments.company_name IS '[DEPRECATED] Usar company_name_encrypted - Datos migrados';
COMMENT ON COLUMN public.investments.shares IS '[DEPRECATED] Usar shares_encrypted - Datos migrados';
COMMENT ON COLUMN public.investments.average_price IS '[DEPRECATED] Usar average_price_encrypted - Datos migrados';
COMMENT ON COLUMN public.investments.symbol_encrypted IS 'Ticker encryptado con AES-256-GCM (PSD2 Art.95) - Protege estrategia de portafolio';
COMMENT ON COLUMN public.investments.company_name_encrypted IS 'Nombre empresa encriptado con AES-256-GCM (GDPR Art.32)';
COMMENT ON COLUMN public.investments.shares_encrypted IS 'Cantidad de acciones encriptada con AES-256-GCM (PSD2 Art.95) - Tamaño de posición sensible';
COMMENT ON COLUMN public.investments.average_price_encrypted IS 'Precio promedio encriptado con AES-256-GCM (PSD2 Art.95) - Costo de inversión sensible';


-- ------------------------------------------------------------
-- budgets
-- ------------------------------------------------------------
CREATE TABLE public.budgets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    month integer NOT NULL,
    year integer NOT NULL,
    total_budget numeric(12,2) DEFAULT 0 NOT NULL,
    name character varying(200),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_budgets_month CHECK (((month >= 1) AND (month <= 12))),
    CONSTRAINT chk_budgets_total_positive CHECK ((total_budget >= (0)::numeric)),
    CONSTRAINT chk_budgets_year CHECK (((year >= 2000) AND (year <= 2100)))
);

COMMENT ON TABLE public.budgets IS 'Presupuestos mensuales de usuarios';
COMMENT ON COLUMN public.budgets.id IS 'Identificador único del presupuesto (UUID)';
COMMENT ON COLUMN public.budgets.user_id IS 'Usuario propietario del presupuesto';
COMMENT ON COLUMN public.budgets.month IS 'Mes del presupuesto (1=Enero, 12=Diciembre)';
COMMENT ON COLUMN public.budgets.year IS 'Año del presupuesto';
COMMENT ON COLUMN public.budgets.total_budget IS 'Presupuesto total mensual (suma de todas las partidas)';
COMMENT ON COLUMN public.budgets.name IS 'Nombre opcional del presupuesto (ej: "Enero 2026 - Plan de ahorro")';
COMMENT ON COLUMN public.budgets.created_at IS 'Fecha y hora de creación del presupuesto';
COMMENT ON COLUMN public.budgets.updated_at IS 'Fecha y hora de última actualización';


-- ------------------------------------------------------------
-- budget_items
-- ------------------------------------------------------------
CREATE TABLE public.budget_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    budget_id uuid NOT NULL,
    category_id uuid NOT NULL,
    allocated_amount numeric(12,2) NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_budget_items_amount_positive CHECK ((allocated_amount >= (0)::numeric))
);

COMMENT ON TABLE public.budget_items IS 'Partidas individuales de presupuestos (asignación por categoría)';
COMMENT ON COLUMN public.budget_items.id IS 'Identificador único de la partida (UUID)';
COMMENT ON COLUMN public.budget_items.budget_id IS 'ID del presupuesto padre al que pertenece esta partida';
COMMENT ON COLUMN public.budget_items.category_id IS 'ID de la categoría de gasto asociada';
COMMENT ON COLUMN public.budget_items.allocated_amount IS 'Monto asignado a esta categoría en el presupuesto';
COMMENT ON COLUMN public.budget_items.notes IS 'Notas opcionales sobre esta partida (ej: "Incrementar por vacaciones")';
COMMENT ON COLUMN public.budget_items.created_at IS 'Fecha y hora de creación de la partida';
COMMENT ON COLUMN public.budget_items.updated_at IS 'Fecha y hora de última actualización';


-- =============================================================
-- VISTAS
-- =============================================================

CREATE VIEW public.v_accounts_summary AS
 SELECT a.id,
    a.name,
    a.type,
    a.bank_name,
    a.currency,
    a.is_active,
    COALESCE(sum(t.amount), (0)::numeric) AS calculated_balance,
    a.balance AS manual_balance,
    count(t.id) AS transaction_count,
    max(t.date) AS last_transaction_date
   FROM (public.accounts a
     LEFT JOIN public.transactions t ON ((a.id = t.account_id)))
  GROUP BY a.id, a.name, a.type, a.bank_name, a.currency, a.is_active, a.balance;

COMMENT ON VIEW public.v_accounts_summary IS 'Resumen de cuentas con balance calculado y estadísticas básicas';


-- =============================================================
-- PRIMARY KEYS
-- =============================================================

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.investments
    ADD CONSTRAINT investments_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT budgets_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.budget_items
    ADD CONSTRAINT budget_items_pkey PRIMARY KEY (id);


-- =============================================================
-- UNIQUE CONSTRAINTS
-- =============================================================

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_name_key UNIQUE (name);

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT uq_budgets_user_period UNIQUE (user_id, month, year);

ALTER TABLE ONLY public.budget_items
    ADD CONSTRAINT uq_budget_items_budget_category UNIQUE (budget_id, category_id);


-- =============================================================
-- ÍNDICES
-- =============================================================

-- users
CREATE INDEX idx_users_email ON public.users USING btree (email);
CREATE INDEX idx_users_username ON public.users USING btree (username);
CREATE INDEX idx_users_is_active ON public.users USING btree (is_active);

-- accounts
CREATE INDEX idx_accounts_type ON public.accounts USING btree (type);
CREATE INDEX idx_accounts_active ON public.accounts USING btree (is_active);
CREATE INDEX idx_accounts_user_id ON public.accounts USING btree (user_id);

-- categories
CREATE INDEX idx_categories_type ON public.categories USING btree (type);
CREATE INDEX idx_categories_name ON public.categories USING btree (name);

-- transactions
CREATE INDEX idx_transactions_account_id ON public.transactions USING btree (account_id);
CREATE INDEX idx_transactions_date ON public.transactions USING btree (date DESC);
CREATE INDEX idx_transactions_type ON public.transactions USING btree (type);
CREATE INDEX idx_transactions_date_account ON public.transactions USING btree (date DESC, account_id);
CREATE INDEX idx_transactions_category_id ON public.transactions USING btree (category_id);
CREATE INDEX idx_transactions_external_id ON public.transactions USING btree (external_id) WHERE (external_id IS NOT NULL);
CREATE UNIQUE INDEX idx_transactions_unique_import ON public.transactions USING btree (account_id, date, amount, description) WHERE ((source)::text = 'import'::text);

-- investments
CREATE INDEX idx_investments_status ON public.investments USING btree (status);
CREATE INDEX idx_investments_history ON public.investments USING btree (user_id, status) WHERE (status = 'sold'::public.investment_status);

-- budgets
CREATE INDEX idx_budgets_user_id ON public.budgets USING btree (user_id);
CREATE INDEX idx_budgets_period ON public.budgets USING btree (year DESC, month DESC);
CREATE INDEX idx_budgets_user_period ON public.budgets USING btree (user_id, year DESC, month DESC);

-- budget_items
CREATE INDEX idx_budget_items_budget_id ON public.budget_items USING btree (budget_id);
CREATE INDEX idx_budget_items_category_id ON public.budget_items USING btree (category_id);
CREATE INDEX idx_budget_items_budget_category ON public.budget_items USING btree (budget_id, category_id);


-- =============================================================
-- FOREIGN KEYS
-- =============================================================

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT fk_accounts_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_transfer_account_id_fkey FOREIGN KEY (transfer_account_id) REFERENCES public.accounts(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.investments
    ADD CONSTRAINT investments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT fk_budgets_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.budget_items
    ADD CONSTRAINT fk_budget_items_budget FOREIGN KEY (budget_id) REFERENCES public.budgets(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.budget_items
    ADD CONSTRAINT fk_budget_items_category FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE RESTRICT;


-- =============================================================
-- TRIGGERS
-- =============================================================

CREATE TRIGGER update_accounts_updated_at
    BEFORE UPDATE ON public.accounts
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at
    BEFORE UPDATE ON public.transactions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER trg_budgets_updated_at
    BEFORE UPDATE ON public.budgets
    FOR EACH ROW EXECUTE FUNCTION public.update_budgets_updated_at();

CREATE TRIGGER trg_budget_items_updated_at
    BEFORE UPDATE ON public.budget_items
    FOR EACH ROW EXECUTE FUNCTION public.update_budgets_updated_at();


-- =============================================================
-- FIN DEL SCHEMA
-- =============================================================
