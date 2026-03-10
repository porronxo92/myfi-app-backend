--
-- PostgreSQL database dump
--

\restrict uoNbxZ9aCgbmbujvsSSbw0mSCVaa7vmiz6hIY9ke5B1HL0BdkpRRy9ZV5tALhlT

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg13+1)
-- Dumped by pg_dump version 16.11

-- Started on 2026-03-09 15:32:09

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

DROP DATABASE app_finance;
--
-- TOC entry 3559 (class 1262 OID 16384)
-- Name: app_finance; Type: DATABASE; Schema: -; Owner: admin
--

CREATE DATABASE app_finance WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'en_US.utf8';


ALTER DATABASE app_finance OWNER TO admin;

\unrestrict uoNbxZ9aCgbmbujvsSSbw0mSCVaa7vmiz6hIY9ke5B1HL0BdkpRRy9ZV5tALhlT
\connect app_finance
\restrict uoNbxZ9aCgbmbujvsSSbw0mSCVaa7vmiz6hIY9ke5B1HL0BdkpRRy9ZV5tALhlT

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

--
-- TOC entry 2 (class 3079 OID 16389)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 3560 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- TOC entry 873 (class 1247 OID 32822)
-- Name: investment_status; Type: TYPE; Schema: public; Owner: admin
--

CREATE TYPE public.investment_status AS ENUM (
    'active',
    'sold',
    'watchlist',
    'pending'
);


ALTER TYPE public.investment_status OWNER TO admin;

--
-- TOC entry 233 (class 1255 OID 16449)
-- Name: calculate_account_balance(uuid); Type: FUNCTION; Schema: public; Owner: admin
--

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


ALTER FUNCTION public.calculate_account_balance(p_account_id uuid) OWNER TO admin;

--
-- TOC entry 3561 (class 0 OID 0)
-- Dependencies: 233
-- Name: FUNCTION calculate_account_balance(p_account_id uuid); Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON FUNCTION public.calculate_account_balance(p_account_id uuid) IS 'Calcula el balance total de una cuenta sumando todas sus transacciones';


--
-- TOC entry 235 (class 1255 OID 41009)
-- Name: update_budgets_updated_at(); Type: FUNCTION; Schema: public; Owner: admin
--

CREATE FUNCTION public.update_budgets_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_budgets_updated_at() OWNER TO admin;

--
-- TOC entry 234 (class 1255 OID 16446)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: admin
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 215 (class 1259 OID 16400)
-- Name: accounts; Type: TABLE; Schema: public; Owner: admin
--

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


ALTER TABLE public.accounts OWNER TO admin;

--
-- TOC entry 3562 (class 0 OID 0)
-- Dependencies: 215
-- Name: TABLE accounts; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.accounts IS 'Cuentas bancarias y de inversión del usuario';


--
-- TOC entry 3563 (class 0 OID 0)
-- Dependencies: 215
-- Name: COLUMN accounts.type; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.accounts.type IS 'Tipos: checking (corriente), savings (ahorro), investment (inversión), credit_card (tarjeta), cash (efectivo)';


--
-- TOC entry 3564 (class 0 OID 0)
-- Dependencies: 215
-- Name: COLUMN accounts.balance; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.accounts.balance IS '[DEPRECATED] Usar balance_encrypted - Datos migrados';


--
-- TOC entry 3565 (class 0 OID 0)
-- Dependencies: 215
-- Name: COLUMN accounts.account_number; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.accounts.account_number IS '[DEPRECATED] Usar account_number_encrypted - Datos migrados';


--
-- TOC entry 3566 (class 0 OID 0)
-- Dependencies: 215
-- Name: COLUMN accounts.notes; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.accounts.notes IS '[DEPRECATED] Usar notes_encrypted - Datos migrados';


--
-- TOC entry 3567 (class 0 OID 0)
-- Dependencies: 215
-- Name: COLUMN accounts.user_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.accounts.user_id IS 'Usuario propietario de la cuenta (FK a users.id)';


--
-- TOC entry 3568 (class 0 OID 0)
-- Dependencies: 215
-- Name: COLUMN accounts.account_number_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.accounts.account_number_encrypted IS 'IBAN/Número de cuenta encriptado con AES-256-GCM (PSD2)';


--
-- TOC entry 3569 (class 0 OID 0)
-- Dependencies: 215
-- Name: COLUMN accounts.notes_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.accounts.notes_encrypted IS 'Notas adicionales encriptadas';


--
-- TOC entry 3570 (class 0 OID 0)
-- Dependencies: 215
-- Name: COLUMN accounts.balance_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.accounts.balance_encrypted IS 'Saldo encriptado con AES-256-GCM (PSD2 Art.95) - Dato financiero crítico';


--
-- TOC entry 222 (class 1259 OID 40983)
-- Name: budget_items; Type: TABLE; Schema: public; Owner: admin
--

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


ALTER TABLE public.budget_items OWNER TO admin;

--
-- TOC entry 3571 (class 0 OID 0)
-- Dependencies: 222
-- Name: TABLE budget_items; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.budget_items IS 'Partidas individuales de presupuestos (asignación por categoría)';


--
-- TOC entry 3572 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.id IS 'Identificador único de la partida (UUID)';


--
-- TOC entry 3573 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.budget_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.budget_id IS 'ID del presupuesto padre al que pertenece esta partida';


--
-- TOC entry 3574 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.category_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.category_id IS 'ID de la categoría de gasto asociada';


--
-- TOC entry 3575 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.allocated_amount; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.allocated_amount IS 'Monto asignado a esta categoría en el presupuesto';


--
-- TOC entry 3576 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.notes; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.notes IS 'Notas opcionales sobre esta partida (ej: "Incrementar por vacaciones")';


--
-- TOC entry 3577 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.created_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.created_at IS 'Fecha y hora de creación de la partida';


--
-- TOC entry 3578 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.updated_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.updated_at IS 'Fecha y hora de última actualización';


--
-- TOC entry 221 (class 1259 OID 40961)
-- Name: budgets; Type: TABLE; Schema: public; Owner: admin
--

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


ALTER TABLE public.budgets OWNER TO admin;

--
-- TOC entry 3579 (class 0 OID 0)
-- Dependencies: 221
-- Name: TABLE budgets; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.budgets IS 'Presupuestos mensuales de usuarios';


--
-- TOC entry 3580 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.id IS 'Identificador único del presupuesto (UUID)';


--
-- TOC entry 3581 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.user_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.user_id IS 'Usuario propietario del presupuesto';


--
-- TOC entry 3582 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.month; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.month IS 'Mes del presupuesto (1=Enero, 12=Diciembre)';


--
-- TOC entry 3583 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.year; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.year IS 'Año del presupuesto';


--
-- TOC entry 3584 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.total_budget; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.total_budget IS 'Presupuesto total mensual (suma de todas las partidas)';


--
-- TOC entry 3585 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.name; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.name IS 'Nombre opcional del presupuesto (ej: "Enero 2026 - Plan de ahorro")';


--
-- TOC entry 3586 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.created_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.created_at IS 'Fecha y hora de creación del presupuesto';


--
-- TOC entry 3587 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.updated_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.updated_at IS 'Fecha y hora de última actualización';


--
-- TOC entry 218 (class 1259 OID 16456)
-- Name: categories; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.categories (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(100) NOT NULL,
    type character varying(20) NOT NULL,
    color character varying(7) DEFAULT '#6B7280'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT categories_type_check CHECK (((type)::text = ANY ((ARRAY['income'::character varying, 'expense'::character varying])::text[])))
);


ALTER TABLE public.categories OWNER TO admin;

--
-- TOC entry 3588 (class 0 OID 0)
-- Dependencies: 218
-- Name: TABLE categories; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.categories IS 'Categorías de ingresos y gastos';


--
-- TOC entry 3589 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN categories.type; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.categories.type IS 'Tipo: income (ingreso) o expense (gasto)';


--
-- TOC entry 3590 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN categories.color; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.categories.color IS 'Color hexadecimal para visualización';


--
-- TOC entry 220 (class 1259 OID 32847)
-- Name: investments; Type: TABLE; Schema: public; Owner: admin
--

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


ALTER TABLE public.investments OWNER TO admin;

--
-- TOC entry 3591 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN investments.symbol; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.investments.symbol IS '[DEPRECATED] Usar symbol_encrypted - Datos migrados';


--
-- TOC entry 3592 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN investments.company_name; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.investments.company_name IS '[DEPRECATED] Usar company_name_encrypted - Datos migrados';


--
-- TOC entry 3593 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN investments.shares; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.investments.shares IS '[DEPRECATED] Usar shares_encrypted - Datos migrados';


--
-- TOC entry 3594 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN investments.average_price; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.investments.average_price IS '[DEPRECATED] Usar average_price_encrypted - Datos migrados';


--
-- TOC entry 3595 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN investments.symbol_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.investments.symbol_encrypted IS 'Ticker encryptado con AES-256-GCM (PSD2 Art.95) - Protege estrategia de portafolio';


--
-- TOC entry 3596 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN investments.company_name_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.investments.company_name_encrypted IS 'Nombre empresa encriptado con AES-256-GCM (GDPR Art.32)';


--
-- TOC entry 3597 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN investments.shares_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.investments.shares_encrypted IS 'Cantidad de acciones encriptada con AES-256-GCM (PSD2 Art.95) - Tamaño de posición sensible';


--
-- TOC entry 3598 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN investments.average_price_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.investments.average_price_encrypted IS 'Precio promedio encriptado con AES-256-GCM (PSD2 Art.95) - Costo de inversión sensible';


--
-- TOC entry 216 (class 1259 OID 16416)
-- Name: transactions; Type: TABLE; Schema: public; Owner: admin
--

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


ALTER TABLE public.transactions OWNER TO admin;

--
-- TOC entry 3599 (class 0 OID 0)
-- Dependencies: 216
-- Name: TABLE transactions; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.transactions IS 'Todas las transacciones financieras (ingresos, gastos, transferencias)';


--
-- TOC entry 3600 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.amount; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.amount IS '[DEPRECATED] Usar amount_encrypted - Datos migrados';


--
-- TOC entry 3601 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.description; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.description IS '[DEPRECATED] Usar description_encrypted - Datos migrados';


--
-- TOC entry 3602 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.type; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.type IS 'Tipo de movimiento: income (ingreso), expense (gasto), transfer (transferencia)';


--
-- TOC entry 3603 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.transfer_account_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.transfer_account_id IS 'Cuenta destino si es una transferencia interna';


--
-- TOC entry 3604 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.external_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.external_id IS 'ID único del banco para evitar duplicados en importaciones';


--
-- TOC entry 3605 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.category_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.category_id IS 'Categoría de la transacción (FK a categories)';


--
-- TOC entry 3606 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.amount_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.amount_encrypted IS 'Importe encriptado con AES-256-GCM (PSD2 Art.95) - Revela patrones financieros';


--
-- TOC entry 3607 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.description_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.description_encrypted IS 'Descripción encriptada con AES-256-GCM (GDPR Art.32) - Protege hábitos de gasto';


--
-- TOC entry 219 (class 1259 OID 24577)
-- Name: users; Type: TABLE; Schema: public; Owner: admin
--

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


ALTER TABLE public.users OWNER TO admin;

--
-- TOC entry 3608 (class 0 OID 0)
-- Dependencies: 219
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.users IS 'Usuarios del sistema de gestión financiera';


--
-- TOC entry 3609 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.id IS 'Identificador único del usuario';


--
-- TOC entry 3610 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.email; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.email IS 'Email del usuario (único)';


--
-- TOC entry 3611 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.username; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.username IS 'Nombre de usuario (único, opcional)';


--
-- TOC entry 3612 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.password_hash; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.password_hash IS 'Hash de la contraseña (bcrypt)';


--
-- TOC entry 3613 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.full_name; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.full_name IS '[DEPRECATED] Usar full_name_encrypted - Datos migrados a columna encriptada';


--
-- TOC entry 3614 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.is_active; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.is_active IS 'Si el usuario está activo';


--
-- TOC entry 3615 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.is_admin; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.is_admin IS 'Si el usuario tiene permisos de administrador';


--
-- TOC entry 3616 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.last_login; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.last_login IS 'Última fecha de login';


--
-- TOC entry 3617 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.created_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.created_at IS 'Fecha de creación del registro';


--
-- TOC entry 3618 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.updated_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.updated_at IS 'Fecha de última actualización';


--
-- TOC entry 3619 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.profile_picture; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.profile_picture IS '[DEPRECATED] Usar profile_picture_encrypted - Datos migrados a columna encriptada';


--
-- TOC entry 3620 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.email_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.email_encrypted IS 'Email encriptado con AES-256-GCM para cumplimiento GDPR';


--
-- TOC entry 3621 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.full_name_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.full_name_encrypted IS 'Nombre completo encriptado con AES-256-GCM';


--
-- TOC entry 3622 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.profile_picture_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.profile_picture_encrypted IS 'Foto de perfil encriptada con AES-256-GCM';


--
-- TOC entry 217 (class 1259 OID 16450)
-- Name: v_accounts_summary; Type: VIEW; Schema: public; Owner: admin
--

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


ALTER VIEW public.v_accounts_summary OWNER TO admin;

--
-- TOC entry 3623 (class 0 OID 0)
-- Dependencies: 217
-- Name: VIEW v_accounts_summary; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON VIEW public.v_accounts_summary IS 'Resumen de cuentas con balance calculado y estadísticas básicas';


--
-- TOC entry 3547 (class 0 OID 16400)
-- Dependencies: 215
-- Data for Name: accounts; Type: TABLE DATA; Schema: public; Owner: admin
--

COPY public.accounts (id, name, type, balance, currency, bank_name, account_number, is_active, notes, created_at, updated_at, user_id, account_number_encrypted, notes_encrypted, balance_encrypted) FROM stdin;
1405a2b1-5a95-4ac8-956d-4b707372d231	Principal	checking	12255.06	EUR	Bankinter	\N	t		2025-12-26 00:34:39.441663+00	2026-02-11 22:54:29.551271+00	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	1:fOuOjQI2zFPmlfq2:hguZXyAHtqaZeR7Jjy+ydRNSuA==:VYqqRiVsIEfOYnxXFK10rQ==	\N	1:z5DzNAk9x2hffaEf:+Euseh9v+GY=:Tkr1xgUOJBaGA+k7HtDQxw==
1e1a4596-f1f0-42ba-860a-50a21c2aa005	IB - Inversion	investment	15718.00	EUR	Interactive Brokers	\N	t		2025-12-28 23:32:23.46171+00	2026-02-11 22:54:29.551271+00	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	1:d0rLlRuxZO2fhfvI:FyQwSUn/BuZg0vXlp1VOOM7VQi1HNBgO:uXvdcoVtQ02NNmaN9pX9XA==	\N	1:Vdo/uvGmnbikMMOo:JFF/GoYwsdI=:ZOTOXeIk2OQxt0TrKRfCrg==
4e629dd0-cab6-4783-87b4-6673483fc3d0	Revolut	checking	252.55	EUR	Revolut	\N	t		2025-12-28 23:31:53.809442+00	2026-02-11 22:54:29.551271+00	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	1:aG1iqjpHhMvCGVX4:OJ5C2gmlXsw66M9rCX3yvBNg36rpTnky:dIGH/WbzOfksUvuHHtdQQg==	\N	1:wP3XyZW8onjD1+43:o4TGf3QX:RkdKueHHVsC2kE5Kxx4J6w==
5741fca9-7352-41a6-bb0e-ad31c15f588d	Bankinter	checking	11500.00	EUR	Bankinter	\N	t		2025-12-30 18:29:21.38843+00	2026-02-11 22:54:29.551271+00	2b3c618a-dbbc-4e9d-bf47-ee909c6b79c9	1:Imok9YYDbBtPfj60:xBaEW8v4L/Ux6twQ+8YOWGXCPADxVbcL:mOaT1CrcgGOvD9EtOQ1b7Q==	\N	1:DeDgnslab5Hov57w:YnCc15GLlJg=:S2LRHFn9ROHioF0BIQSvVg==
7d76d928-55d7-4401-8ee0-ab8eec344e34	BBVA - prueba	checking	8337.25	EUR	BBVA	\N	t		2025-12-28 18:18:03.298426+00	2026-02-11 22:54:29.551271+00	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	1:p89iCmphtYihYbVE:4YfdoyPhtQuuXtX9rTVErg==:GU+8X1haqObeEmY3oPsWNQ==	\N	1:nH2vZq0XhRBDZqQ2:6MmQTDTRUQ==:gMn0fJ9C342ANVepUULENw==
7f65a306-10aa-434c-b92d-4a6fde2a5692	Rand	savings	13367.19	EUR	Rand	\N	t		2025-12-30 01:00:49.443013+00	2026-02-11 22:54:29.551271+00	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	1:ONxvh+rKn/W0OLfJ:flxfD0a6tiFSwNBBvhambEZ7QhGcIwFn:S+hjvqcdoBixczjsNzSPsg==	\N	1:n/m4F86EhfvdcNJp:HXmO/6rANuQ=:Di23LKJNbHRAFx9fXMVdQw==
904ca456-5ded-458b-8425-60752a032519	Compartida con Gema	checking	1000.00	EUR	Banco Sabadell	\N	t		2026-01-17 02:15:59.508199+00	2026-02-11 22:54:29.551271+00	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	1:UjofuAr/TkvFhFVv:t4vGMuxtXodKq7Ngbg/9d6u9tCxgdw/Y:GsnQbNGimHvBaLpzvKIeJw==	\N	1:7iwwHAGqEVBH19yh:ENwbLXvHhA==:YOMgkPyyw12mKZeEq0QhKQ==
74c71e0a-81a9-49e2-8d70-b96cb61b638d	Prueba	checking	11538.00	EUR	Bankinter	\N	t	\N	2025-12-22 00:30:33.174306+00	2026-02-14 18:23:07.994028+00	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	1:gcjtUPIIJoLH/MmX:1eMzCZ97i5p4vSb0XfY8BreM:ctXhj9gF5f4q+vlEV9FQ5A==	1:Ir/e67sXtexoZvvj:oPYxhq06Wee9FI427MZIiA==:ZIqRrr4Qyntb4MWgZG9F0Q==	1:mm24rDpELOaSUoAP:MJR4EHMJODU=:+5GYcMx/1jObv+kt09lKXA==
\.


--
-- TOC entry 3553 (class 0 OID 40983)
-- Dependencies: 222
-- Data for Name: budget_items; Type: TABLE DATA; Schema: public; Owner: admin
--

COPY public.budget_items (id, budget_id, category_id, allocated_amount, notes, created_at, updated_at) FROM stdin;
281a4766-c6cc-4e00-a4a5-191caaeda6c0	5cd57528-de35-42ff-abee-5e216d0f8ace	d307ec0c-3908-4ff7-b13c-ea71619f768f	500.00	\N	2026-01-17 11:35:20.985097+00	2026-01-17 11:35:20.985097+00
5141cf7d-36b6-4f41-814c-d3a3cdc3f067	5cd57528-de35-42ff-abee-5e216d0f8ace	fff297ad-6016-41ec-8639-b3939bfa6745	50.00	\N	2026-01-17 11:35:20.985097+00	2026-01-17 11:35:20.985097+00
7a8b0759-43f2-4f91-92cc-a831ac5c9bf9	5cd57528-de35-42ff-abee-5e216d0f8ace	ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef	700.00	\N	2026-01-17 11:35:20.985097+00	2026-01-17 11:35:20.985097+00
e38e0061-fc0d-4521-a4e2-c399e10bf04f	43c1554e-1480-410d-9fbc-e3c0fdd1533c	d307ec0c-3908-4ff7-b13c-ea71619f768f	200.00	cosas de supermercado mias	2026-01-17 11:50:37.252249+00	2026-01-17 11:50:37.252249+00
e2826c05-3f06-4f08-8245-06b7d4be04e0	43c1554e-1480-410d-9fbc-e3c0fdd1533c	f14e7ce4-e65d-45de-8fb9-9185c0d91f34	43.00	\N	2026-01-17 11:50:37.252249+00	2026-01-17 11:50:37.252249+00
e17fa5f6-3089-4a08-893d-e1012d76000f	43c1554e-1480-410d-9fbc-e3c0fdd1533c	fff297ad-6016-41ec-8639-b3939bfa6745	50.00	\N	2026-01-17 11:50:37.252249+00	2026-01-17 11:50:37.252249+00
ab9f948b-fd88-43ef-a96f-e143562051ec	43c1554e-1480-410d-9fbc-e3c0fdd1533c	ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef	650.00	Alquiler del mes	2026-01-17 11:50:37.252249+00	2026-01-17 11:50:37.252249+00
5c180b9f-330f-445f-9884-58432a3e3801	43c1554e-1480-410d-9fbc-e3c0fdd1533c	e97bb263-2d15-43c3-9256-79938404834e	100.00	\N	2026-01-17 11:50:37.252249+00	2026-01-17 11:50:37.252249+00
dcf80f47-7af9-4829-9ee2-e124f77a3580	df9584cd-0998-4140-befb-c85e22b8fdd9	d307ec0c-3908-4ff7-b13c-ea71619f768f	500.00	\N	2026-01-17 12:30:49.857695+00	2026-01-17 12:30:49.857695+00
064a1463-f6bc-445e-a746-316e30ee2eef	df9584cd-0998-4140-befb-c85e22b8fdd9	fff297ad-6016-41ec-8639-b3939bfa6745	50.00	\N	2026-01-17 12:30:49.857695+00	2026-01-17 12:30:49.857695+00
069e2d8c-831a-4935-adee-90c2de913458	df9584cd-0998-4140-befb-c85e22b8fdd9	ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef	700.00	\N	2026-01-17 12:30:49.857695+00	2026-01-17 12:30:49.857695+00
d21fa3ee-0e06-4633-bb93-b45e38868fb8	df9584cd-0998-4140-befb-c85e22b8fdd9	0c5118f0-05ed-4da0-bcb2-383d265e46b1	25.00	\N	2026-01-17 12:30:49.857695+00	2026-01-17 12:30:49.857695+00
\.


--
-- TOC entry 3552 (class 0 OID 40961)
-- Dependencies: 221
-- Data for Name: budgets; Type: TABLE DATA; Schema: public; Owner: admin
--

COPY public.budgets (id, user_id, month, year, total_budget, name, created_at, updated_at) FROM stdin;
43c1554e-1480-410d-9fbc-e3c0fdd1533c	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	1	2026	943.00	Enero 2026	2026-01-16 22:03:58.020213+00	2026-01-17 01:58:28.980856+00
5cd57528-de35-42ff-abee-5e216d0f8ace	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	2	2026	1250.00	Febrero 2026	2026-01-17 11:35:20.985097+00	2026-01-17 11:35:20.985097+00
df9584cd-0998-4140-befb-c85e22b8fdd9	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	3	2026	1250.00	Febrero 2026	2026-01-17 11:37:09.827612+00	2026-01-17 11:37:09.827612+00
\.


--
-- TOC entry 3549 (class 0 OID 16456)
-- Dependencies: 218
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: admin
--

COPY public.categories (id, name, type, color, created_at) FROM stdin;
d307ec0c-3908-4ff7-b13c-ea71619f768f	Supermercado	expense	#10B981	2025-12-21 13:31:20.24344+00
2d854969-3a82-4436-bc2f-e5393fc236a6	Restaurantes	expense	#F59E0B	2025-12-21 13:31:20.24344+00
1960f361-abb2-4c4b-a8be-87aca42cb1d6	Transporte	expense	#3B82F6	2025-12-21 13:31:20.24344+00
e75ee282-4e27-4c80-b6e1-667cf1e8a9d3	Coche	expense	#6366F1	2025-12-21 13:31:20.24344+00
f14e7ce4-e65d-45de-8fb9-9185c0d91f34	Bicicleta	expense	#14B8A6	2025-12-21 13:31:20.24344+00
34ff018a-6826-4ab8-826f-ef22e629791e	Compras Online	expense	#EC4899	2025-12-21 13:31:20.24344+00
fff297ad-6016-41ec-8639-b3939bfa6745	Amazon	expense	#FF9900	2025-12-21 13:31:20.24344+00
ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef	Alquiler	expense	#EF4444	2025-12-21 13:31:20.24344+00
e97bb263-2d15-43c3-9256-79938404834e	Ocio/Deporte	expense	#06B6D4	2025-12-21 13:31:20.24344+00
48e4d0cd-6292-4c58-bf10-2379b8c5d3b2	Viajes	expense	#0EA5E9	2025-12-21 13:31:20.24344+00
b0ce5d72-ad4a-44f2-bf0a-c629e17759dd	Salud/Cuidados	expense	#DC2626	2025-12-21 13:31:20.24344+00
275d2d2c-2901-40a4-807f-01b6b0a89998	Gastos Fijos	expense	#6B7280	2025-12-21 13:31:20.24344+00
64445688-c033-4eaa-85cf-935c18fa6db4	Inversión	expense	#059669	2025-12-21 13:31:20.24344+00
0c5118f0-05ed-4da0-bcb2-383d265e46b1	Bizum	expense	#0891B2	2025-12-21 13:31:20.24344+00
7203913a-2b15-45dc-83c2-c5880caa6121	Regalos	expense	#EC4899	2025-12-21 13:31:20.24344+00
20113046-6b5f-4a6c-9536-6b473f6582cc	Gastos Personales	expense	#DB2777	2025-12-21 13:31:20.24344+00
f107f866-accf-4c57-8276-669fc2f31004	Sin Categorizar	expense	#94A3B8	2025-12-21 13:31:20.24344+00
313d81c7-4346-46ec-98ea-672e8cd31a1c	Freelance	income	#14B8A6	2025-12-21 13:31:20.259445+00
b545d5c3-3cdd-4198-868c-58cb7873c49b	Inversiones	income	#059669	2025-12-21 13:31:20.259445+00
fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	Ingreso - Bizum	income	#22C55E	2025-12-21 13:31:20.259445+00
a66db8ff-825b-46bf-9d71-5e769daea823	Intereses	income	#059669	2025-12-21 13:32:56.377826+00
88d52b3c-9d8f-4008-bb51-5adb398ac4de	Transferencia	expense	#2738F5	2025-12-30 00:06:18.297+00
94c7e01f-ee86-4684-9bb8-37e8a4d378e0	Ingreso	income	#2738F5	2025-12-21 13:31:20.259445+00
056a82ec-cebe-46a2-89e8-56f6118f7283	Salario	income	#3b82f6	2025-12-21 13:31:20.259445+00
\.


--
-- TOC entry 3551 (class 0 OID 32847)
-- Dependencies: 220
-- Data for Name: investments; Type: TABLE DATA; Schema: public; Owner: admin
--

COPY public.investments (id, user_id, symbol, company_name, shares, average_price, purchase_date, sale_price, sale_date, status, notes, created_at, updated_at, symbol_encrypted, company_name_encrypted, shares_encrypted, average_price_encrypted) FROM stdin;
01dc07f9-1fd1-4b10-b809-d75138dac5af	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	AS	AMER SPORTS INC	22.0000	39.15	2026-01-13	\N	\N	active	\N	2026-01-13 22:13:03.166848+00	2026-02-11 22:54:29.675328+00	1:79tJweCM7Sd7Du3m:qS4=:+87Rdc6ROkP/PGZ5fBQp3A==	1:v2BmsFxxTASalEUW:6C//FYC0n0pqQGvlHtk0:vUd07OqgSgxTWHgWHd3fTw==	1:1yuytxLvXf6ojyhT:/4qct78JUg==:n0PqSBv4jseOwMUhw36D8Q==	1:hO3zoFU9zqGRTp49:kHjxrVI=:U2eAHXfX5VkbILEEtrbrMg==
0a61ea83-383c-4f77-b76a-f42ec626f51a	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	CMG	Chipotle Mexican Grill	91.0000	55.75	2026-01-13	\N	\N	active	\N	2026-01-13 17:18:05.979319+00	2026-02-11 22:54:29.675328+00	1:DaAhNB3GVmulJoWL:74XL:S6xiIsB9MhDPP83Aa8sJlA==	1:effFW6QphB4gsJpe:GD6t7zzccalzUXZNDbXsaIEVjXPwDg==:oXYNZiRl/Y8J6H11cdp2rQ==	1:ovfeQmF3BHiWGfiO:rp2tKv0dTw==:DQ+VArxuSF04kM2jwZQ8Rg==	1:x7Sp3Crl/Z8LR+vo:gYkX3T8=:mb4M+frns3Uqg9oiiFPeuw==
4a35fb03-a507-44f6-aa8d-0ee86598744b	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	MMM	3M CO	6.0000	166.83	2026-01-13	\N	\N	sold	Presenta resultados el martes 20/01	2026-01-13 22:13:59.995049+00	2026-02-11 22:54:29.675328+00	1:6qx9eVnZcfT2z8V6:ZzoQ:HBwqdg81fY34bV/1pVIOgA==	1:CYpu1wkOGjoTE1Va:61L7V/Q=:ougOEKB/vAIhH/Hc5Out/Q==	1:VpmP3qMyEvAJ8N6Q:sMmez8Ng:30MWA6iNLRI00hk6ZOBtqA==	1:37UljsBc1IFDhMNZ:rq1Xh8qi:XUSqpDa2iv6hJqJYeDjU8w==
5904a77a-563d-4284-aa89-456f198e6f1e	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	AMZN	Amazon.com Inc	12.0000	191.73	2024-06-12	\N	\N	active	\N	2026-01-13 17:23:52.697622+00	2026-02-11 22:54:29.675328+00	1:CddITxXLjaUm5CVg:GvF61Q==:FDxFSu01OoUgvNmJPoknaQ==	1:Wmfmyqi/vwonGxR5:gLjN+hXKU7Zr2LUFAYs=:QJG7JyiELkDHKKFVPKU56Q==	1:SzoXLTXWnW0DiCVn:kssMOjMjXw==:Ki9BmovYT36NfFpsGsKcDw==	1:anBVQ1ACBk+OhTht:ubjAkgc3:4lFSlAvp7FEkYXd5c8CcCA==
a52c7a7c-ae61-43ed-948d-72aa4eea4258	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	ZETA	ZETA GLOBAL HOLDINGS CORP-A	40.0000	23.52	2026-01-13	\N	\N	active	\N	2026-01-13 22:13:30.48413+00	2026-02-11 22:54:29.675328+00	1:AF1q6Erqnat6HHXM:HL6qpw==:nAUpd18rW46bBTQhr/ki5A==	1:b2y411y7Kjrl3wSH:f5Txa+q20dOlCWtcYQ4kPogor9HPblWxOBFV:qUIkh5MVlGmzpmoY8PthtA==	1:OIswaYFEiJwMjvH5:Ciiv+sAYnQ==:OVHYO1PvRtB2vmyVp8YIDA==	1:XrxlnWsy9t9Wybnv:57zkrNc=:k7aCXSFCg4J6xJrFCrhRyw==
a876c593-4697-4610-abde-68fcaf4f27b9	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	TSLA	TESLA INC	4.0000	438.00	2026-01-17	\N	\N	sold		2026-01-17 11:44:09.724049+00	2026-02-11 22:54:29.675328+00	1:sQVffaG0A+Fkw7xY:UVdKyg==:vPQXdmTeOnZqZizql5MUfQ==	1:ugGi4rnkNQzcwKp8:z1mS66bPYC7g:nsxJhww0uou/FXt74L9KTQ==	1:kTxynarWrl+ygeYi:ofBRjcrB:mZnpwkoULrYLOJkA84X82A==	1:+6/8VFGyF1TCrOUk:OceNy3EV:R8jsba6J8WrDJLcnlzvWwg==
cac0e2f1-834e-49a9-a2d1-c1adcc8a5fd8	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	META	META PLATFORMS INC-CLASS A	1.0000	643.87	2025-11-12	\N	\N	active	\N	2026-01-13 22:07:27.842229+00	2026-02-11 22:54:29.675328+00	1:YMR0J08uyvVVL5Hu:+GX/ng==:j2DxgbqLk9VNXE3+wJ604w==	1:WYHr+uVlakqqEhup:Wz69vt4Okhe3QhJD2LJDqKCIgfVMhp+rmQM=:Xi4s5n1RZzw/DqfBJ2U5DQ==	1:bSXtlbLJ2n+SqXSN:4yVQVpVa:nJxYFXQNuF3IyN3VPg/Clw==	1:z92t35dj0tPX5C6R:7cjBKmAR:9UkK4n3ZteXrGoOF3EvChg==
db5639f0-92d5-4c99-bbf4-ee30df9feabd	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	ONON	On Holding AG Class A	23.0000	45.11	2026-01-13	\N	\N	active	\N	2026-01-13 17:46:28.121439+00	2026-02-11 22:54:29.675328+00	1:ZHMQ6tBgHd17vbsC:ygBKcg==:12AOZnO/U1acfvrgsa7oZQ==	1:Z/wvSb/+O4nAdpHD:rIuwK+GzA/lNCRHXC/n9LRd4Fpjb:VQlhoqkzUFQk7U/gDVvdbA==	1:EOnXa0ZygpMttksB:RXR6U5+2vg==:sVghvyGdHegtsSAWrNxkAQ==	1:6nzOMH0cgbYhZbmY:CUCTX/M=:VDc7s3C2vfyrh4NLkE7fRg==
eee8451e-c34c-4d0b-af09-2c183d584e31	0ce003d1-8cfc-4c99-90ab-09f302f9ac41	LLY	Lilly(Eli) & Company	1.0000	1013.00	2026-01-13	\N	\N	active	\N	2026-01-13 17:49:19.307419+00	2026-02-11 22:54:29.675328+00	1:pVASV5dDlGT/YzFc:JpgP:HDlvn5SX+Fkd239/1K4//g==	1:B0IU+NPXsWGQuvKU:USxpa4P8TzREoY6fADxXalEXPPk=:HJQdbb7o+5mFwbNtAvQH5g==	1:u/Z8iCEV1POl3w/S:IwrL9ex3:lCST0SRsQ77o+ocPZGkyqQ==	1:xKHb16WTyvOF4gOY:vihUq8jwRg==:FxPtHsySZk0W+wRqjg2IQg==
\.


--
-- TOC entry 3548 (class 0 OID 16416)
-- Dependencies: 216
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: admin
--

COPY public.transactions (id, account_id, date, amount, description, type, transfer_account_id, notes, tags, external_id, source, created_at, updated_at, category_id, amount_encrypted, description_encrypted) FROM stdin;
00174a09-f6a2-4770-867d-5e2eba8e0fe6	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-17	8.00	Bizum de Sergio Rodriguez	income	\N		{}	\N	manual	2025-12-31 02:25:43.04671+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:Azxy/nJ/0ons3PBO:P25UaQ==:F4ZOJaiZk7v1oVyzkTjgKQ==	1:XP7weiE71V5fRtbU:o6Py6x0o4z4LOtQ/h2hLFsgkygeTR7us/w==:qKWHDza2BJmR+MXHPgHI8g==
015dd1e9-4940-43a1-95a8-178f74e692e6	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-16	-27.20	Pasteleria Gito	expense	\N		{}	\N	manual	2025-12-31 02:25:42.932122+00	2026-02-11 22:54:29.599999+00	2d854969-3a82-4436-bc2f-e5393fc236a6	1:SIuSVbzHXTvKwb1p:ouJ1lTAB:g/nTCZvbsRVcakC16OXYPQ==	1:3hMFK8W3nMED+Xm2:UOAbRJhBpZfdaggUAiHf:k/QJ8J/WN8+Qe9EPH01owg==
024708f1-29f8-45c3-8bd2-3a1f513cb2f6	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-12-30	123.00	prueba1 	expense	1e1a4596-f1f0-42ba-860a-50a21c2aa005		{}	\N	manual	2025-12-30 00:41:04.571449+00	2026-02-11 22:54:29.599999+00	88d52b3c-9d8f-4008-bb51-5adb398ac4de	1:ur5aqJZm6W4kqQyB:Q4KjWZS6:cwhGD2+Q4uL7wr0crERhiA==	1:OKbintvN/bA7XUrQ:LxkA8ngH7VU=:6TKF7g1NGwQpRmW3+HPIIA==
02dc78a6-f198-4fbb-95ef-5a628155da1a	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-03	-30.00	Bizum a Jose Luis de la C	expense	\N		{}	\N	manual	2025-12-31 02:25:42.119037+00	2026-02-11 22:54:29.599999+00	0c5118f0-05ed-4da0-bcb2-383d265e46b1	1:gagUb22HzZjGXmAD:lNM/AS4J:PAgBfDbhgQrzKqaWSOwF+A==	1:XyAUyPaXNOlOgDhc:CVbrw8m6oiDDEtrelTNUwxP0TvyhW8SFWQ==:pB7arrSo2PZgp4Y5V0tR8g==
04ca3f0d-921f-4ae3-b684-cf57a38784b5	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-05	-16.30	Mercadona	expense	\N		{}	\N	manual	2025-12-31 02:25:42.290876+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:aSzXBfzJt7MF0xVH:y9x7+NNS:s/oHXgUjgQNkiBgoUCjdLw==	1:kEBFRTBYp98ak4Gc:DXGmAfc3j9Go:sSEhpL7S7IctUUEmv0ZIXA==
06283afe-a341-44c9-969f-8f0d7d81cbb3	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-10	-369.00	PcComponentes	expense	\N		{}	\N	manual	2025-12-31 02:25:42.474497+00	2026-02-11 22:54:29.599999+00	34ff018a-6826-4ab8-826f-ef22e629791e	1:UrHetfeJd+PV37Pg:V7ksQlXlWw==:AIZ58ZT+ApBSvPcas7eNRw==	1:WfGakQfbHlSOgGi2:glBzGtlleZfIlbN/HQ==:Ia/P2hMno39rNT2A+z3ekw==
07884bae-cb69-445b-9929-d14575281bef	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-27	-100.00	Bizum de Gema Porcar	expense	\N		{}	\N	manual	2025-12-31 02:25:43.848179+00	2026-02-11 22:54:29.599999+00	0c5118f0-05ed-4da0-bcb2-383d265e46b1	1:3JocClFnbXLp2Cv0:oMJckViH4Q==:KACMJvnLCyQPWo1+gzqcFA==	1:FsOLJpwXYKG54+ql:tRNy9MSpse8pNxJ0oq+TnUgEcSE=:oJ46mwTmIhTNKVPvwH27qg==
0e4781f5-6db8-4afd-9a49-4071556e3e66	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-03-08	7.30	Forn Cusi	expense	\N		{}	\N	manual	2025-12-31 02:38:20.313547+00	2026-02-11 22:54:29.599999+00	2d854969-3a82-4436-bc2f-e5393fc236a6	1:2ncwKplpFUoaH/8s:TgLZPw==:ofYUK2lLh3gSV3p++VCbeA==	1:kYOHYoTgIvktrBnB:b0MO8OtZTJ7M:hwTamuV/uNV4F7LPbE9sNA==
12c3d188-26b3-4800-9b5f-34963becf862	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-11	-10.00	Repostaje Ballenoil	expense	\N		{}	\N	manual	2025-12-31 02:25:42.536226+00	2026-02-11 22:54:29.599999+00	1960f361-abb2-4c4b-a8be-87aca42cb1d6	1:bceI8YgLFqbx1jIT:CArOgBn3:IqNAUIoeFQujbBAeMYfmDg==	1:tJHmBSqrV7HEhR88:fuMZe7fw4kXTlO5jr4UuIU5S3A==:D0w89v+VNLNgXRg1UOsl+A==
1533dc12-7e24-413b-a57b-ee08e392ad82	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-03-11	71.00	Klassmark (Anulación)	income	\N		{}	\N	manual	2025-12-31 02:38:20.569675+00	2026-02-11 22:54:29.599999+00	94c7e01f-ee86-4684-9bb8-37e8a4d378e0	1:VIo1hjHAVKR0XJqu:WnacdUQ=:EeqExTb5NBQQAs5kNnivXg==	1:DgWnAFzFbKBf9UaB:h8VMi5i3wpmMpk4xC3y72zLvwy6KKQ==:2+r9aZLDHJnad0AfA+EOhA==
164867d1-c365-4ec2-a42d-370db17bfa9c	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-26	-650.00	Transferencia a Ruben de la Cruz Diaz	expense	\N		{}	\N	manual	2025-12-31 02:25:43.609169+00	2026-02-11 22:54:29.599999+00	88d52b3c-9d8f-4008-bb51-5adb398ac4de	1:DazFt00PLQ+Nvrel:6vC5ukZI/w==:mjUFs0ZLSEcjEMgxB2FGDw==	1:obhOZa5efY6FZkc5:8CZ+rfWqhrjycwrxFOHm5KHa7/RGLmKE+5VZr8DM0wiNUFdwjA==:8HXQRdgQEV8GZ1JJOlGvbA==
183408e3-f099-45ea-9b37-5d022b1947be	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-02	14.20	Bizum a Gema Porcar	income	\N		{}	\N	manual	2025-12-31 02:25:42.065686+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:sYo/1ttARJpQ+qdB:NaabA8I=:U7sVrhcX9UID4KmQ1wgM0g==	1:VT9394wEPJ7VVC2U:b1NG64kCiaGx2cP9d5JVR3qNTQ==:jAdNovL0hEZAZD4oNbJuJQ==
1a2e9de2-eeef-4383-b59d-2356450f72b9	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-27	2182.81	Nomina Indra Soluciones	income	\N		{}	\N	manual	2025-12-31 02:25:43.786598+00	2026-02-11 22:54:29.599999+00	056a82ec-cebe-46a2-89e8-56f6118f7283	1:SOUIXRTtVEo3QUhe:i3maSyKFUg==:FKcMii5xHd4Wcei4z3u8yQ==	1:6yAuLP62u4sjoN4+:AiW7jvzenwIb/s+aLx86gysvI/o753o=:sSEB54fkjjx1DiTedQjrug==
1a5d548e-b7fd-4f91-b0ed-717d7f0a7e21	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-02	28.50	Bizum a Maria Olaria	income	\N		{}	\N	manual	2025-12-31 02:25:42.001669+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:VvpKvzFHIsoZYSVW:rAaRDPA=:Vq7xTbQHOPlKFechDZEaBg==	1:hYhMjX3Ft7XM05ht:CptZNUSt4vhOE1sk0MzZK82Mj9E=:x84LLQdV5nykgtvalOQrAw==
1f61e864-a5ed-4a7a-ba1f-7c2279101f53	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-22	-61.00	Revolut	expense	\N		{}	\N	manual	2025-12-31 02:25:43.423395+00	2026-02-11 22:54:29.599999+00	f107f866-accf-4c57-8276-669fc2f31004	1:KRs2CBXa/Dg7eOXU:Bbl00wi4:m9mIHT/+eTmbyGo55s8gNA==	1:A7WclsbYBQH+nx6e:zB32+p2BNw==:yo5Bci9PM8GcskJX9I/GUQ==
1f75e044-a99f-4ded-9f4c-4090acd0f6c5	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-01	-0.99	Mercadona	expense	\N		{}	\N	manual	2025-12-31 02:25:41.944557+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:6o/wJQTKciOB5lNz:qCopCa0=:T44FHsGcFBbNFNU/feai5g==	1:HtHQqfazofBYafrs:DZvjchMD+MON:Jjbz84EJQupXpFg6LQgfxA==
20afe133-e3a5-445a-a6ef-141c32b2810e	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-08	-50.00	Entrenamiento +Quekms	expense	\N		{}	\N	manual	2025-12-31 02:25:42.421485+00	2026-02-11 22:54:29.599999+00	e97bb263-2d15-43c3-9256-79938404834e	1:j4Sr1A3O2lFd9+GP:NIPq2wWS:QK4t9e5JXwAWf+X8jln2nQ==	1:DtGoRGhYUD7JDS4+:YaoO9Dtx9MhrvYudLiNTZkbGLQFv:Y5SiVpkGSOxfm1EuuehjTw==
2253d0f3-b6a7-4cc9-9010-a6d3d8b7691f	7d76d928-55d7-4401-8ee0-ab8eec344e34	2025-12-30	1500.00	nomina	income	\N		{}	\N	manual	2025-12-30 00:44:01.231539+00	2026-02-11 22:54:29.599999+00	056a82ec-cebe-46a2-89e8-56f6118f7283	1:viy5Z4emQLqxLbry:3vMKagVolg==:VIdWhfmz3HpmiKCM9EvG9w==	1:1w35VmT3OMcTA7hT:F3G1FtFn:PhZ/FK9DjW9VhRzHZJKy3w==
2aac9e13-211f-4628-9e73-519a83a50b7e	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-03-15	4.00	Bizum a Rosa Maria Molin	income	\N		{}	\N	manual	2025-12-31 02:38:20.627112+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:WbPbnlKBh+1fsDLS:wiu0Bg==:6hW8rNR5Yeld0DsvQkHF7g==	1:2OILz5mj0lUeiBjL:KLDwYUd1HjvzG4KZZqemSXWpqV/i7Yg/:Ckiu3N0WpwwdrfCQwQ1/2g==
2c0f193e-9845-4435-9aec-c3915a383cf5	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-28	-226.00	Transferencia a Ruben de la Cruz Diaz	expense	\N		{}	\N	manual	2025-12-31 02:25:43.911108+00	2026-02-11 22:54:29.599999+00	88d52b3c-9d8f-4008-bb51-5adb398ac4de	1:n14kK+g75UNqqdQJ:TDXldd+s5A==:x6haL0CMtdnup29M7bb3AA==	1:pAQyB9DKwzLSk+CE:C9de50cocUW+BSZu2ni8Vf8821uj8GDmLBb9ZhCBbh75WlFKVg==:MA0DHuvY4LiMdGtjwr9HcA==
2ccf007c-85c4-47cc-abce-a056dbfaeac1	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-03-06	60.00	Bizum a Jose Luis	income	\N		{}	\N	manual	2025-12-31 02:38:20.216296+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:83SMAtgoYIeZsKho:t0YkDyM=:5+ExOmu4xaYSKj/Z8+PA2g==	1:OC8g8inaLhRdejC/:Epwbr6Qmgq9PlMjgwcxtX3o=:PbMjAOwTt7urYMV3nW/Nug==
2ee039c2-927e-417b-8a2e-2693ed15c2f9	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-23	-7.70	Churreria Cazorla	expense	\N		{}	\N	manual	2025-12-31 02:25:43.477762+00	2026-02-11 22:54:29.599999+00	2d854969-3a82-4436-bc2f-e5393fc236a6	1:KZYY8j4ncO0QYazM:tTXOqVE=:R/XQH/h8VvhUwyTEOsSeaQ==	1:tAZ/nmZtxVqenb3d:RA+dM26oPglQoV1mNRVSfpc=:bIXqmqYKji1/4NGqwKkDVQ==
2efb75c5-e952-4ef4-a3ab-3bb9bf681194	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-05	2.25	Anulacion Mercadona	income	\N		{}	\N	manual	2025-12-31 02:25:42.364886+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:3lznmRpqs8Z0hdaA:0jnIZQ==:UChdn9PMnsucxCqUaaCZvA==	1:mgwBMzUk2n/FfW9o:K7MKrhX28VOsgW2T7j12TrOPnA==:shFbIOfUaLZ/mEsVO47g0A==
3a7afe68-509f-44e1-8011-c842133e3e01	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-19	-21.99	Wellhub - Gimnasio	expense	\N		{}	\N	manual	2025-12-31 02:25:43.35711+00	2026-02-11 22:54:29.599999+00	e97bb263-2d15-43c3-9256-79938404834e	1:V+oGXgdxEWIVNvta:WFKL+pIB:VJR/8Kw6SP9PwXcYKIoOew==	1:YWY4CdzEBisGO9Se:lRT3ktuTrkACQ5RMEjVdwWgn:/WzY2D3lLeJBW8eNKj7ltA==
3c7bf863-4abd-4a81-a65c-89d96b9558d7	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-26	-3.50	Citricos Oroplana	expense	\N		{}	\N	manual	2025-12-31 02:25:43.665977+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:0j8YwcOXYhTSVi1h:HVijOfQ=:p/QqTwnsppXJajonq/uEXw==	1:dZuB+X3zpKHOSRzF:Xon6AdMFTnfC4WPorIj5Vfo=:y5X0bRVXAfO8WjezI0t1ag==
428a42ce-7ab4-4a01-b1a5-6a404ccdc09b	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-15	-11.00	Revolut	expense	\N		{}	\N	manual	2025-12-31 02:25:42.702674+00	2026-02-11 22:54:29.599999+00	f107f866-accf-4c57-8276-669fc2f31004	1:bHM7pHyqr8WMsZkG:HUrqtgJZ:22EoqmshpWrfYwjWAxa3kg==	1:VesZ+I5584qWoFrX:Te2nNuPADA==:auRV6+ZG3f2laaUFkYE3vA==
44a86e3d-58e6-4a3c-b4a8-a74214c49fe7	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-16	55.00	Bizum de Gema Porcar	income	\N		{}	\N	manual	2025-12-31 02:25:42.812953+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:Fo3D0MVUKBrcq4oS:XtQlXYk=:ozVgYKq8S/goEF06N6hdow==	1:YGUKnqvBXrjIAoLU:ay0ocynykgNEnsNrrTjGJz7oNu4=:pZEvVVuHlKS8RSvBr1qPGQ==
50cfeb36-bc34-43d8-8655-2f1a6bf78f52	74c71e0a-81a9-49e2-8d70-b96cb61b638d	2025-12-22	8.20	2º prueba transaccion	expense	\N		{}	\N	manual	2025-12-22 00:54:25.574737+00	2026-02-11 22:54:29.599999+00	f14e7ce4-e65d-45de-8fb9-9185c0d91f34	1:FYAjlCSFKHqGT6tb:E9kBwA==:gwDXURVMiTNTCXv5u4isIA==	1:X1xBz0bmNDUKP82i:S4e9kGxKiAEXdc1J2M0U9nvMWpGeRQ==:fGAFGH6FD6yD4ik7bgn4iQ==
50ef95c2-26f4-4ade-9e1f-0fa519fc789b	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-02-26	33.00	Fundacio Dali Web	expense	\N		{}	\N	manual	2026-01-01 18:54:15.233228+00	2026-02-11 22:54:29.599999+00	e97bb263-2d15-43c3-9256-79938404834e	1:ZsuupiKzw8zhj94t:ZleAIz0=:H//BkQOUqrrPx5NAYwEGNA==	1:aR/wqIva9QuPMeEn:iiZzVn719iobqK7qdVh9qDY=:rWoNlRDeIgsK+YvzGc2D2Q==
5a7458ca-64e3-4534-a268-adb6855a156b	7d76d928-55d7-4401-8ee0-ab8eec344e34	2026-01-11	2000.00	salario enero	income	\N		{}	\N	manual	2026-01-11 20:05:44.094228+00	2026-02-11 22:54:29.599999+00	056a82ec-cebe-46a2-89e8-56f6118f7283	1:XqqDrs0MSQrQObeh:MqZ4ciKwFQ==:Q/gZRhrURuc16ngyPu9hvQ==	1:mDo3daDPuZRxFdnp:ojM7riwMntg5PhgsVQ==:RuOP9YU3iQb4sVXJpqQEmQ==
5cf783fe-c0f8-418f-a97d-67dd0100ba81	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-01-31	59.99	Wellhub	expense	\N	Pago con tarjeta	{}	\N	manual	2025-12-31 02:07:08.453163+00	2026-02-11 22:54:29.599999+00	\N	1:wUgorLdBRJM1YUMc:wcpURpU=:Xw2R/ME3EBdGA4TVzWEjkQ==	1:EFGMuxhnbQilYJjj:NhjsibVqow==:39PXY49muA3L46A+4YY7gQ==
673e9edf-43d0-4130-bc8f-051489fe0c16	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-02-16	30.00	Ballenoil Castellon - Repostaje	expense	\N		{}	\N	manual	2026-01-01 18:54:14.996638+00	2026-02-11 22:54:29.599999+00	1960f361-abb2-4c4b-a8be-87aca42cb1d6	1:hkPjhzussqzTARML:Z+QxbLY=:P7mmPZ1+TgFkqdQa1Aj7vQ==	1:8TPgf0Py8hLhywq9:L9lrHvcAe0qq/uIz8y/W3QVJb4erwGe7FmHqeA0gyQ==:OvznR37XNOOnkDRFanJKHw==
6d497ede-1cb2-40fc-9159-adb18b24f86c	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-13	-35.00	Bizum a Jordi Martinez	expense	\N		{}	\N	manual	2025-12-31 02:25:42.591442+00	2026-02-11 22:54:29.599999+00	0c5118f0-05ed-4da0-bcb2-383d265e46b1	1:TZZcTWETk1oE3Um5:dTo8ZPZ9:CaY/1/88msnpJ7sBGl4kow==	1:Wry21HnKJiVE6HKK:wbTLZe+3CQdIosSc+eoVluaYuMfaFw==:/z/0VGkMI/4xuhkMDFx8UQ==
6d8f00db-b995-4f46-8956-d756b2e1b051	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-04	-4.50	Citricos Oroplana	expense	\N		{}	\N	manual	2025-12-31 02:25:42.176048+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:4OiZxbzKYf4/wNWE:GSNkHKI=:RFZFVmG1VMj4mefEnc2J6Q==	1:SPKQbrQlGhEXpQR5:7HEH9PAe6fB2yRIAKHUnMmQ=:3f5fZn88sXWEeOIfBykBcA==
6dcdd69a-c768-4474-a3cf-c22eba91e7f1	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-19	-35.00	Clinica Segarra	expense	\N		{}	\N	manual	2025-12-31 02:25:43.228877+00	2026-02-11 22:54:29.599999+00	b0ce5d72-ad4a-44f2-bf0a-c629e17759dd	1:2tLYBrr1mvaXnUrL:NAwdG4LI:Wq4QF536S2MPnEJDD6BLkQ==	1:gQ+buHTgAtExYCkx:1w8ufQzDGqqxAPaTcU3E:UiTibVGyj/0HzypMO+ABEQ==
7202ff7f-5f63-410a-81a9-b47c827b1bb7	1e1a4596-f1f0-42ba-860a-50a21c2aa005	2026-01-12	800.00	transfer para cubrir rojos	expense	4e629dd0-cab6-4783-87b4-6673483fc3d0		{}	\N	manual	2026-01-12 00:40:14.909318+00	2026-02-11 22:54:29.599999+00	88d52b3c-9d8f-4008-bb51-5adb398ac4de	1:FSDkxnpq7MuyTau/:NIyLBNrs:i33tCrv1mrKKtvm8hTLm+A==	1:htL/ESPcvpl9ILso:KfWiwkyeN0dc0E3EDkbjEfLs0byvokSI4R0=:bCOBDJ95FGJwvZ/MjxE/EA==
74d79095-af1d-451e-a888-0df5fc0cd66a	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-16	-30.00	Repostaje Ballenoil	expense	\N		{}	\N	manual	2025-12-31 02:25:42.991807+00	2026-02-11 22:54:29.599999+00	1960f361-abb2-4c4b-a8be-87aca42cb1d6	1:WVVc7BgmJTvMmTLK:fxhCt66p:gScFVP7O24o3+ke0DbeVvQ==	1:nUMnW/01O96TqYel:cYOkWBaDLfoxLYhpCC3VrbprPQ==:Zjqptc3Jl+dDa1UprL2c6g==
79b5fb9e-24f6-4d0d-8155-8dc24669d047	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-15	17.90	Bizum de Lledo Garcia	income	\N		{}	\N	manual	2025-12-31 02:25:42.647449+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:5ntjmvOUCHfEn0g4:KffyQdw=:xulOgJkbUamGgM5jfc9w9g==	1:2e+qyzKw+EkESQyV:ysUJbMlj37IIj2Dxo9LdFhN84C/0:a9Hyz7cj6J9AmRbnA5h+Mg==
7e5eaa1a-487f-4592-b519-023615828f68	7d76d928-55d7-4401-8ee0-ab8eec344e34	2026-01-12	250.00	compra mercadona	expense	\N		{}	\N	manual	2026-01-12 00:09:54.09694+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:ycYvI5NKLcfUzlhl:a4IZozzs:Hhyt2E0/ASStfQqgfnH9CQ==	1:zrglh7SvTYo9IK1+:HMHy2ftdglMPL0maVJ/cdw==:K8A7jC5va/apu/PXaWNG/g==
801a3f09-0c8d-41b4-84fd-30b5d0a33e23	74c71e0a-81a9-49e2-8d70-b96cb61b638d	2025-07-31	222.00	Mercadona	expense	\N		{}	\N	automatico	2025-12-31 01:16:47.494475+00	2026-02-11 22:54:29.599999+00	e97bb263-2d15-43c3-9256-79938404834e	1:Y9R6AzKc9TPWSQTk:7KEBobRv:FxhEBJjgIB1WoJEf/rDWRQ==	1:VN7+zECKO9F9vg57:fidtBKkAmG7A:Jhiv45+UgrrbQIfzoUJrPw==
8a3f505c-0531-49a5-b18d-a0a88e89581b	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-02-16	27.20	Pasteleria Cafeteria Gito	expense	\N		{}	\N	manual	2026-01-01 18:54:14.949768+00	2026-02-11 22:54:29.599999+00	2d854969-3a82-4436-bc2f-e5393fc236a6	1:ROpgxIys5LyAEbY8:rdIp9ME=:2L+dLccVJPib3rvOxUO3ew==	1:Bfa2l9skgNzt9tfZ:Eez8/4AUXPV+3bt8DzfT2DkHqN0KcuMPyg==:pRXGDygoqPUkkPMifIQeqQ==
8aad320a-9c9b-4360-ac64-9d65414a47ad	1e1a4596-f1f0-42ba-860a-50a21c2aa005	2025-12-30	123.00	prueba1 	income	4e629dd0-cab6-4783-87b4-6673483fc3d0		{}	\N	manual	2025-12-30 00:41:04.571331+00	2026-02-11 22:54:29.599999+00	94c7e01f-ee86-4684-9bb8-37e8a4d378e0	1:7SWCOmybz/bA/uYu:bqfONXky:PXm+/0cX5x0ClWE1z9/lEw==	1:P2oRrs6x1QWef5o+:xewWiDQdbNk=:WNjGhYqCkMcKyoZNUGoNyw==
8ca2066b-7f38-45c9-afdf-160de68f3163	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-02-02	28.50	Bizum a Maria Olaria	income	\N		{}	\N	manual	2025-12-31 02:07:08.60512+00	2026-02-11 22:54:29.599999+00	\N	1:Eat8A4rJkecmsCyT:NwWAUsc=:t0atYPON6bGEcTzJCG1Rhg==	1:m2h8uManBdNo68KT:FnOWHUlce+T4uZr+pap3zBicJxg=:k7s/G4aS4qkOuAJr8+emHA==
8d76f104-00d5-4c10-8d43-2d03fb29f5ad	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-01-31	-59.99	Wellhub - Gimnasio	expense	\N		{}	\N	manual	2025-12-31 02:25:41.814717+00	2026-02-11 22:54:29.599999+00	e97bb263-2d15-43c3-9256-79938404834e	1:iVbaMsLb2IXSdjtF:xraTFM68:pQMVcjJBdo+pteBKwtfLow==	1:eYU73kmvoUwYfb2v:RLVvBSd5Nmwf3tSxEjCB5aUM:Pontua21shlfyXPsUhHR1Q==
90fb1c38-dd22-4a0f-9d8c-96d268dd4124	1405a2b1-5a95-4ac8-956d-4b707372d231	2025-11-17	10.10	Pago de ticket	expense	\N		{}	\N	manual	2026-01-04 20:53:29.896969+00	2026-02-11 22:54:29.599999+00	1960f361-abb2-4c4b-a8be-87aca42cb1d6	1:2JbIveaXSIha8IrE:pWYQE4Y=:WMeViRvd5zIRM/e3DsQ+/Q==	1:g+eLxTSZhHQkUYmE:+spOIWqSoLMwG8FDF8U=:A5bdeQs+Py+xOy2kJD8uZQ==
952ce1a3-5151-4761-9428-69bbec8f8950	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-02-19	350.00	Bizum de Gema Porcar	income	\N		{}	\N	manual	2026-01-01 18:54:15.048959+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:/MD7qEcair5ssrOq:yJInwn7C:BOBXE6i07AMHDzDXxj9w7Q==	1:noA19bkwjvaZxeEo:5aJIYk4ncwe23H/SRdN8iQyfC8w=:aZagngadnpp7u16gZ1pfmQ==
95ebbbcc-d96a-4f30-bd58-5dc4ed902fc8	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-19	350.00	Bizum de Gema Porcar	income	\N		{}	\N	manual	2025-12-31 02:25:43.160406+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:zNSUxoGV29ZMrftj:a86LhB0N:PCUMB0sAJihBP1b2alLeaQ==	1:fH+K4kFGIDDudVoM:5l7KCZIuZ9s/cH6fAELLaLIn8fA=:x0YvFcWVWCmbQ9gt/GMnug==
98c49d1d-60ec-4d1c-8d84-917a222885d6	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-02-02	14.20	Bizum a Gema Porcar	income	\N		{}	\N	manual	2025-12-31 02:07:08.707466+00	2026-02-11 22:54:29.599999+00	\N	1:D2OiIJZlZYJiDTbq:+YyKSXY=:Nz2GOrx3lJv4rL36/nA+Bw==	1:zguvzZkcoRLTdkgC:yhd7E3z2bTOJ4NTTbGd4h1iIUQ==:aspDTa8iw1EUoXv0vOdg8w==
99d97e1b-7ac7-4530-89a9-49aa28e30722	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-28	-450.00	Transferencia a Ruben de la Cruz Diaz	expense	\N		{}	\N	manual	2025-12-31 02:25:43.977429+00	2026-02-11 22:54:29.599999+00	88d52b3c-9d8f-4008-bb51-5adb398ac4de	1:6BkVHTLgeOTahK4V:XQ4nYPKBlg==:OdwGy4R28LZIChcJ+86O0g==	1:QHA8oV1yDKKct6C9:52gFnA+cm2OhgPA9yf3XiLOxUqkt1SJ7Qiccf9EH+iUPHl68kA==:v0N0w/ej/s2VdCJeGa/O6g==
9a4d4f27-dcb5-4f0a-a824-aeb454d61a09	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-24	-200.00	Transferencia a Ruben de la Cruz Diaz	expense	\N		{}	\N	manual	2025-12-31 02:25:43.54939+00	2026-02-11 22:54:29.599999+00	88d52b3c-9d8f-4008-bb51-5adb398ac4de	1:pyAyK1vktqNUCS3P:1PZXTJlxMw==:K5yh2bSOdvYeK8RiT1kffQ==	1:WRvkeuP/f/Lm5joB:VXexMiTxg9AbjTFxquXAN2sa6+/gUsD76CUifIN0COvxpe0T6g==:UzoeTUfpch1hHig8VqjTbw==
9bca8a46-3a55-4280-af09-ba7925ace1bf	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-17	-3.00	Citricos Oroplana	expense	\N		{}	\N	manual	2025-12-31 02:25:43.109909+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:OEZxxAOo4ZmtIyik:DjA1tLg=:gqSUcvPtHTqVj6I/+QvLmA==	1:Y2gC/phABRB8PnZ0:FvlcCWe4OS1LRtgvTAWoqU4=:mKSshZiulZvG3O5AqRY9YA==
9c6b5014-7ec4-4f75-bd08-bfec64b31aea	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-26	-33.00	Fundacio Dali	expense	\N		{}	\N	manual	2025-12-31 02:25:43.725715+00	2026-02-11 22:54:29.599999+00	e97bb263-2d15-43c3-9256-79938404834e	1:CXW3Y1JtQAR+FJX7:dTFbJwJj:/xl0sQMDCz7Z6QvQcaeLZA==	1:nV4JN8S18r1szBZu:Ojy1I5vqwIj++qSjPA==:YW9OspqFRt2+T71tmBF/4g==
9d792f39-653d-4b14-a36a-b6cbfdaae0c0	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-15	-54.97	Supeco Torrijos	expense	\N		{}	\N	manual	2025-12-31 02:25:42.757967+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:HnfhWjNtDv4HWas+:szkz4ox7:cXkTSJirvRK8rtpL2XvWXQ==	1:I4uYYLFrxJRRRdiE:1vIDE2WADdJ5QbLpC61P:MBPbKRXssLaOCx2HY73NkA==
9fa9b260-3648-4334-834b-45c893c5e0e7	74c71e0a-81a9-49e2-8d70-b96cb61b638d	2025-12-22	10.00	prueba transaccion	expense	\N		{}	\N	manual	2025-12-22 00:46:57.310599+00	2026-02-11 22:54:29.599999+00	275d2d2c-2901-40a4-807f-01b6b0a89998	1:Jy63LWO4w9A6nX6F:myO0iEA=:so+ZeDMNpTn7Ewu3mWa+xw==	1:J8H1tEZ0kZ9tVAMP:SBrMP8DMxSebznjWBLrfXxr9:iWDUdNJFlyjlduYAzwe7uw==
a16dab99-54eb-46d8-a35e-ff7ba910a16c	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-03-18	150.00	Bizum a Gema Porcar	income	\N		{}	\N	manual	2025-12-31 02:38:20.684785+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:h6SEVIRe+ldQc/mk:sO47xAi0:W/xQgw86zZw3L9g1V63d6g==	1:aN+R8749Opi4jJOX:H1rsLYGYK+x2PNLEZ0sz5kmP3A==:daRlVHakYmSgfxiTGDW66w==
abcd8fbb-0345-40b6-b904-fdd85ac9d508	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-01-30	-17.99	Spotify - Suscripcion	expense	\N		{}	\N	manual	2025-12-31 02:25:41.680718+00	2026-02-11 22:54:29.599999+00	275d2d2c-2901-40a4-807f-01b6b0a89998	1:uj01znyBVkKmmue/:/waVSUjJ:y3gBa2SzGJqWvsJB5VCdRA==	1:vYeDUvnudkHgHJ81:ihFw9fI4Kj1kUaw7f7iB+GWR5WFW:HnuTlgBsJTP4hGLHoAO/gA==
b5e51925-2dae-448b-8c03-7815ef4614bb	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-02-22	61.00	Revolut	expense	\N		{}	\N	manual	2026-01-01 18:54:15.102835+00	2026-02-11 22:54:29.599999+00	fff297ad-6016-41ec-8639-b3939bfa6745	1:AD5hyDlzkySltoPF:5pERfi8=:PkIVZfT/0wpj+ejEIFUa6Q==	1:pYAqMwp06NzA3hc0:ezRP0WUs3w==:UhAqyM8+UhgKN6jh1rGdlA==
bef8c219-922b-4647-9261-65f896d1fee3	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-04	-10.99	Amazon	expense	\N		{}	\N	manual	2025-12-31 02:25:42.234744+00	2026-02-11 22:54:29.599999+00	fff297ad-6016-41ec-8639-b3939bfa6745	1:GAPFCozRJ5TeCdxh:eGp1lxsG:4hBV1JH1rTOSAJfjXemqxA==	1:10o0rz1iVEVfxzHh:OO6NtPIA:p4WUFKRTNJOIEb2fDlHYJw==
c15af9a2-bd0a-41d9-865d-9b3a67e0082e	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-03-10	100.00	Bizum a Gema Porcar	income	\N		{}	\N	manual	2025-12-31 02:38:20.492229+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:1KlmFpRnXi3aLuXd:AB+/izcf:l1ps8fJOhh74lp3K3Hv5Zg==	1:AjN31JpCTNSNxMOF:bE3Fy9iZEpCttItWi6CDXcGWLw==:TuqLRwwLsTYqeo/GFlJs2g==
c5674297-499c-4781-81f4-40b20dc2da28	7f65a306-10aa-434c-b92d-4a6fde2a5692	2026-01-15	310.00	compra	expense	\N		{}	\N	manual	2026-01-15 23:53:17.427241+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:fJwLs5Bk+XIY+bMA:06FwKYdV:lxe0OQL+gdBgbMIn0yxgtg==	1:lIytZWNZOBx80qzh:qAY/fylr:A/eh7rjKK+ja19ey0hS4uw==
ca91ae09-58c7-421c-b864-3b0d7db9721e	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-01	-1019.64	Recibo Platinum	expense	\N		{}	\N	manual	2025-12-31 02:25:41.882241+00	2026-02-11 22:54:29.599999+00	275d2d2c-2901-40a4-807f-01b6b0a89998	1:QYEoYfE8PVvOQviA:7vnl9xxjxH4=:QRim7Xm4iMOqF72gkrvnig==	1:vWcwSMp1G8m8Msrj:XAFiXk04xx2wzFIGXXYM:EzayOiaGxm2l1rYKxrIH5A==
cf0e10b1-476f-41df-a6cf-aa4f30b590dc	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-16	4.00	Bizum de Iris Gonzalez	income	\N		{}	\N	manual	2025-12-31 02:25:42.87429+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:N2vXzjSHkeJjIEs5:xnffnw==:Tu1DnRfBIEenyhN42cMe8Q==	1:/3dqVpYXOC51foHl:IjuNtmq+YhGZNsT/PAOKpddAR3VggA==:GcJR0KTq0SHxlAsAothybg==
d499b65e-39b6-45e1-ae38-32c409369ef5	4e629dd0-cab6-4783-87b4-6673483fc3d0	2025-02-19	-51.35	Lidl	expense	\N		{}	\N	manual	2025-12-31 02:25:43.291799+00	2026-02-11 22:54:29.599999+00	d307ec0c-3908-4ff7-b13c-ea71619f768f	1:yCvBqmXqchTnJ//z:LfQbsfur:lkdpKQbChMji2ZlBY2jvrw==	1:2Jj3S2M1eHNtwRG8:8D/BsA==:QskfxB4Oa1oGN/VFaITsng==
e0e123fa-e2eb-4741-8855-dfff8be69b0b	74c71e0a-81a9-49e2-8d70-b96cb61b638d	2025-12-29	700.00	Alquiler mes diciembre	expense	\N		{alquiler}	\N	manual	2025-12-29 17:52:29.239825+00	2026-02-11 22:54:29.599999+00	ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef	1:TFQ9idR5Y3N/i3cF:JDOEqC5P:VQtsgKWFBa1ZLIO+NeWCIw==	1:3JjjAZeDvbP+wOuN:FuGYMsrvlhzmexUsNSQfkDmCmr3bQg==:y1kE9d1k3+N/KinhhuStPg==
e227ee06-7b37-49c4-97f1-129a66b376e6	74c71e0a-81a9-49e2-8d70-b96cb61b638d	2025-12-22	1200.20	prueba ingreso	income	\N		{}	\N	manual	2025-12-22 00:55:07.263863+00	2026-02-11 22:54:29.599999+00	fe58d212-e793-4237-8cc4-3bc8b4ec0c2f	1:v2cKXHKW+EBNqf2H:HlzUKP3qog==:lKMWlSSXMYA24sHyjf0RZA==	1:l8gdIF2fl+O6gyoM:oLvHIWTvDp6PVwmzITw=:ONlVXWzu/HwqpqdXPawbgQ==
e4aac559-b86d-4235-bbc8-0437d993104c	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-02-15	11.00	Revolut	expense	\N		{}	\N	manual	2026-01-01 18:54:14.698582+00	2026-02-11 22:54:29.599999+00	7203913a-2b15-45dc-83c2-c5880caa6121	1:mMLIOSLsSTr7b2Ch:hnyk1+o=:XJ89Ahm7oyaL7uZ/2k3IxA==	1:/3851dOAA6DZaEU7:ixMQOSF5+w==:5MYiFpE77S0p1A+bMWdJ8g==
e4cc7f0f-a77a-4c9e-92fe-a1923327e758	4e629dd0-cab6-4783-87b4-6673483fc3d0	2026-01-12	800.00	transfer para cubrir rojos	income	1e1a4596-f1f0-42ba-860a-50a21c2aa005		{}	\N	manual	2026-01-12 00:40:14.777476+00	2026-02-11 22:54:29.599999+00	94c7e01f-ee86-4684-9bb8-37e8a4d378e0	1:RbARqSP+xu/x56XX:Hvi8unox:UY56jBiZ39o0v5a4RbH0HQ==	1:ytAeQK0TQWUfjZMb:vAevM/42LUWiwarZKoL+ttHN1fmFwyvoajE=:FzIbgCLNgZmgNx2NcGRzKQ==
ed2e8daf-ab6b-4c37-a515-d4c62bd4ba02	7f65a306-10aa-434c-b92d-4a6fde2a5692	2025-03-08	50.00	Entrenamiento Quekms	expense	\N		{}	\N	manual	2025-12-31 02:38:20.383171+00	2026-02-11 22:54:29.599999+00	e97bb263-2d15-43c3-9256-79938404834e	1:uwwwkkV5Rn1GakCt:uJwMVJg=:JbDyZSYk0eVZ9t+KBIFv4Q==	1:raNPWOOUanw5Em9n:CfJ6egJ5Ti9x4hKY0vNcUBpwZDo=:zxiVsDFJy5b6MiLhJKfKHQ==
fbc03a33-56cf-4476-a9b3-96771426bdbc	5741fca9-7352-41a6-bb0e-ad31c15f588d	2025-12-30	1500.00	Salario febrero 	income	\N		{salario}	\N	manual	2025-12-30 18:32:46.725005+00	2026-02-11 22:54:29.599999+00	056a82ec-cebe-46a2-89e8-56f6118f7283	1:uyGI6Nf0pjI5KjP6:WPUK4XdYRw==:hKFdTNctZ5Z9pNRzezKN7A==	1:S1bmOmsU7ivjjgIj:7kh1e3EexzFtsZEx6rWzIw==:NeAinmD4ZHhZ+H2vdwA/bA==
\.


--
-- TOC entry 3550 (class 0 OID 24577)
-- Dependencies: 219
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: admin
--

COPY public.users (id, email, username, password_hash, full_name, is_active, is_admin, last_login, created_at, updated_at, profile_picture, email_encrypted, full_name_encrypted, profile_picture_encrypted) FROM stdin;
0ce003d1-8cfc-4c99-90ab-09f302f9ac41	ruben_cruz92@hotmail.com	Ruben	$2b$12$VFAohUsbVs0jdzidxObJ1ennngQtLjY1WE0eViRTtDxZgUYuJXlra	1:oh6HvqDJ+8ICl5jw:ICVTultShqZDP/eBrhJWKg==:MVPOx+EczBRmR9H59z/nNg==	t	f	2026-03-09 15:01:17.820614+00	2025-12-24 14:06:28.451108+00	2026-03-09 14:01:17.53638+00	1:iFmKJgGJJ3KNjaf+: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:0NesWENSLzNLeeebI7Lfew==	\N	1:RSHdIHoBIiiDg4vR:qXEN9bgDJzlPet/eKnUpHck0rKaV:HyRUYbo9rzF+A8yy9/Sh1w==	\N
2b3c618a-dbbc-4e9d-bf47-ee909c6b79c9	fernando@correo.es	Fernando	$2b$12$1F/78spXTGEhrkiHG2Zqve165e2WHOaDdx3gmK8yWIBNITBzLRhry	\N	t	f	2025-12-30 19:28:27.366165+00	2025-12-30 18:26:49.579426+00	2026-02-11 22:38:10.931257+00	\N	\N	1:OaEV5cpMq2L/FlmO:UNLW/58HPqc=:9UZUg88zo0umMtynnELTfg==	\N
51516172-a49e-4351-8c6b-247dc93815d9	user@example.com	usuario	$2b$12$gqfqqgn3tKtYATXSZ1fTduql43VGsgSQlhyyjvOY2bNM.nE16Onry	\N	t	f	2025-12-24 12:22:53.785147+00	2025-12-23 00:18:26.619045+00	2026-02-11 22:38:10.931257+00	\N	\N	1:TqOQT2qicnPzK9xr:pCh/GeXWA/2zXBYXiZ5D:p4q3OranX1R+Q3pbzlsWXw==	\N
7f376528-f49c-4799-b0d6-5eeb91ee9475	admin@example.com	admin	$2b$12$Z2Q.1US7JaXgVZhfFgURcunROM1S8P2S1bNzdupKbg61jtciABJDe	\N	t	t	\N	2025-12-23 00:18:26.615609+00	2026-02-11 22:38:10.931257+00	\N	\N	1:qwl+HpFTiDtClrp7:IU1SANx1yQUZ/Z+i+dIfy/Yr8ptPJcGGoQ==:dNGegAiZnLou3ckl46Nwnw==	\N
cbdfa49e-2774-4922-94da-dc3380504322	fernan@correo.es	Fernan	$2b$12$eRcz0dYRJhvP03XX9tDx6OSq1IM4DiuW9pwf8YotxNdzeg1.rO5wS	\N	t	f	2026-01-17 13:23:36.966502+00	2025-12-25 17:45:39.498305+00	2026-02-11 22:38:10.931257+00	\N	\N	1:K474XmmNQ5Fb3ElK:q+6l0zqHY95B8kvG1pkq:iu1+bSNY6OFvEfbfrOsuuQ==	\N
\.


--
-- TOC entry 3346 (class 2606 OID 16413)
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);


--
-- TOC entry 3386 (class 2606 OID 40993)
-- Name: budget_items budget_items_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.budget_items
    ADD CONSTRAINT budget_items_pkey PRIMARY KEY (id);


--
-- TOC entry 3379 (class 2606 OID 40972)
-- Name: budgets budgets_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT budgets_pkey PRIMARY KEY (id);


--
-- TOC entry 3360 (class 2606 OID 16466)
-- Name: categories categories_name_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_name_key UNIQUE (name);


--
-- TOC entry 3362 (class 2606 OID 16464)
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- TOC entry 3377 (class 2606 OID 32857)
-- Name: investments investments_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.investments
    ADD CONSTRAINT investments_pkey PRIMARY KEY (id);


--
-- TOC entry 3358 (class 2606 OID 16428)
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- TOC entry 3391 (class 2606 OID 40995)
-- Name: budget_items uq_budget_items_budget_category; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.budget_items
    ADD CONSTRAINT uq_budget_items_budget_category UNIQUE (budget_id, category_id);


--
-- TOC entry 3384 (class 2606 OID 40974)
-- Name: budgets uq_budgets_user_period; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT uq_budgets_user_period UNIQUE (user_id, month, year);


--
-- TOC entry 3369 (class 2606 OID 24591)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 3371 (class 2606 OID 24589)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 3373 (class 2606 OID 24593)
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- TOC entry 3347 (class 1259 OID 16415)
-- Name: idx_accounts_active; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_accounts_active ON public.accounts USING btree (is_active);


--
-- TOC entry 3348 (class 1259 OID 16414)
-- Name: idx_accounts_type; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_accounts_type ON public.accounts USING btree (type);


--
-- TOC entry 3349 (class 1259 OID 24602)
-- Name: idx_accounts_user_id; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_accounts_user_id ON public.accounts USING btree (user_id);


--
-- TOC entry 3387 (class 1259 OID 41008)
-- Name: idx_budget_items_budget_category; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_budget_items_budget_category ON public.budget_items USING btree (budget_id, category_id);


--
-- TOC entry 3388 (class 1259 OID 41006)
-- Name: idx_budget_items_budget_id; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_budget_items_budget_id ON public.budget_items USING btree (budget_id);


--
-- TOC entry 3389 (class 1259 OID 41007)
-- Name: idx_budget_items_category_id; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_budget_items_category_id ON public.budget_items USING btree (category_id);


--
-- TOC entry 3380 (class 1259 OID 40981)
-- Name: idx_budgets_period; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_budgets_period ON public.budgets USING btree (year DESC, month DESC);


--
-- TOC entry 3381 (class 1259 OID 40980)
-- Name: idx_budgets_user_id; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_budgets_user_id ON public.budgets USING btree (user_id);


--
-- TOC entry 3382 (class 1259 OID 40982)
-- Name: idx_budgets_user_period; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_budgets_user_period ON public.budgets USING btree (user_id, year DESC, month DESC);


--
-- TOC entry 3363 (class 1259 OID 16468)
-- Name: idx_categories_name; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_categories_name ON public.categories USING btree (name);


--
-- TOC entry 3364 (class 1259 OID 16467)
-- Name: idx_categories_type; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_categories_type ON public.categories USING btree (type);


--
-- TOC entry 3374 (class 1259 OID 32863)
-- Name: idx_investments_history; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_investments_history ON public.investments USING btree (user_id, status) WHERE (status = 'sold'::public.investment_status);


--
-- TOC entry 3375 (class 1259 OID 32864)
-- Name: idx_investments_status; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_investments_status ON public.investments USING btree (status);


--
-- TOC entry 3350 (class 1259 OID 16439)
-- Name: idx_transactions_account_id; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_transactions_account_id ON public.transactions USING btree (account_id);


--
-- TOC entry 3351 (class 1259 OID 16474)
-- Name: idx_transactions_category_id; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_transactions_category_id ON public.transactions USING btree (category_id);


--
-- TOC entry 3352 (class 1259 OID 16440)
-- Name: idx_transactions_date; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_transactions_date ON public.transactions USING btree (date DESC);


--
-- TOC entry 3353 (class 1259 OID 16443)
-- Name: idx_transactions_date_account; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_transactions_date_account ON public.transactions USING btree (date DESC, account_id);


--
-- TOC entry 3354 (class 1259 OID 16444)
-- Name: idx_transactions_external_id; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_transactions_external_id ON public.transactions USING btree (external_id) WHERE (external_id IS NOT NULL);


--
-- TOC entry 3355 (class 1259 OID 16442)
-- Name: idx_transactions_type; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_transactions_type ON public.transactions USING btree (type);


--
-- TOC entry 3356 (class 1259 OID 16445)
-- Name: idx_transactions_unique_import; Type: INDEX; Schema: public; Owner: admin
--

CREATE UNIQUE INDEX idx_transactions_unique_import ON public.transactions USING btree (account_id, date, amount, description) WHERE ((source)::text = 'import'::text);


--
-- TOC entry 3365 (class 1259 OID 24594)
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- TOC entry 3366 (class 1259 OID 24596)
-- Name: idx_users_is_active; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_users_is_active ON public.users USING btree (is_active);


--
-- TOC entry 3367 (class 1259 OID 24595)
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_users_username ON public.users USING btree (username);


--
-- TOC entry 3403 (class 2620 OID 41011)
-- Name: budget_items trg_budget_items_updated_at; Type: TRIGGER; Schema: public; Owner: admin
--

CREATE TRIGGER trg_budget_items_updated_at BEFORE UPDATE ON public.budget_items FOR EACH ROW EXECUTE FUNCTION public.update_budgets_updated_at();


--
-- TOC entry 3402 (class 2620 OID 41010)
-- Name: budgets trg_budgets_updated_at; Type: TRIGGER; Schema: public; Owner: admin
--

CREATE TRIGGER trg_budgets_updated_at BEFORE UPDATE ON public.budgets FOR EACH ROW EXECUTE FUNCTION public.update_budgets_updated_at();


--
-- TOC entry 3400 (class 2620 OID 16447)
-- Name: accounts update_accounts_updated_at; Type: TRIGGER; Schema: public; Owner: admin
--

CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON public.accounts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3401 (class 2620 OID 16448)
-- Name: transactions update_transactions_updated_at; Type: TRIGGER; Schema: public; Owner: admin
--

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON public.transactions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3392 (class 2606 OID 24597)
-- Name: accounts fk_accounts_user; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT fk_accounts_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3398 (class 2606 OID 40996)
-- Name: budget_items fk_budget_items_budget; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.budget_items
    ADD CONSTRAINT fk_budget_items_budget FOREIGN KEY (budget_id) REFERENCES public.budgets(id) ON DELETE CASCADE;


--
-- TOC entry 3399 (class 2606 OID 41001)
-- Name: budget_items fk_budget_items_category; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.budget_items
    ADD CONSTRAINT fk_budget_items_category FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE RESTRICT;


--
-- TOC entry 3397 (class 2606 OID 40975)
-- Name: budgets fk_budgets_user; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT fk_budgets_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3396 (class 2606 OID 32858)
-- Name: investments investments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.investments
    ADD CONSTRAINT investments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 3393 (class 2606 OID 16429)
-- Name: transactions transactions_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- TOC entry 3394 (class 2606 OID 16469)
-- Name: transactions transactions_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE SET NULL;


--
-- TOC entry 3395 (class 2606 OID 16434)
-- Name: transactions transactions_transfer_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_transfer_account_id_fkey FOREIGN KEY (transfer_account_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


-- Completed on 2026-03-09 15:32:10

--
-- PostgreSQL database dump complete
--

\unrestrict uoNbxZ9aCgbmbujvsSSbw0mSCVaa7vmiz6hIY9ke5B1HL0BdkpRRy9ZV5tALhlT

