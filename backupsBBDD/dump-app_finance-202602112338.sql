--
-- PostgreSQL database dump
--

\restrict Asheq61SPD2shhW3lSfeuQ9TYGDeSIO1dDmREFrhJtg8wyiVNyLpWi5MKb1a4HZ

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg13+1)
-- Dumped by pg_dump version 16.11

-- Started on 2026-02-11 23:38:02

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

\unrestrict Asheq61SPD2shhW3lSfeuQ9TYGDeSIO1dDmREFrhJtg8wyiVNyLpWi5MKb1a4HZ
\connect app_finance
\restrict Asheq61SPD2shhW3lSfeuQ9TYGDeSIO1dDmREFrhJtg8wyiVNyLpWi5MKb1a4HZ

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

COMMENT ON COLUMN public.accounts.balance IS 'Saldo actual de la cuenta (calculado o manual)';


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
-- TOC entry 3570 (class 0 OID 0)
-- Dependencies: 222
-- Name: TABLE budget_items; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.budget_items IS 'Partidas individuales de presupuestos (asignación por categoría)';


--
-- TOC entry 3571 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.id IS 'Identificador único de la partida (UUID)';


--
-- TOC entry 3572 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.budget_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.budget_id IS 'ID del presupuesto padre al que pertenece esta partida';


--
-- TOC entry 3573 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.category_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.category_id IS 'ID de la categoría de gasto asociada';


--
-- TOC entry 3574 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.allocated_amount; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.allocated_amount IS 'Monto asignado a esta categoría en el presupuesto';


--
-- TOC entry 3575 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.notes; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.notes IS 'Notas opcionales sobre esta partida (ej: "Incrementar por vacaciones")';


--
-- TOC entry 3576 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN budget_items.created_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budget_items.created_at IS 'Fecha y hora de creación de la partida';


--
-- TOC entry 3577 (class 0 OID 0)
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
-- TOC entry 3578 (class 0 OID 0)
-- Dependencies: 221
-- Name: TABLE budgets; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.budgets IS 'Presupuestos mensuales de usuarios';


--
-- TOC entry 3579 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.id IS 'Identificador único del presupuesto (UUID)';


--
-- TOC entry 3580 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.user_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.user_id IS 'Usuario propietario del presupuesto';


--
-- TOC entry 3581 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.month; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.month IS 'Mes del presupuesto (1=Enero, 12=Diciembre)';


--
-- TOC entry 3582 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.year; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.year IS 'Año del presupuesto';


--
-- TOC entry 3583 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.total_budget; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.total_budget IS 'Presupuesto total mensual (suma de todas las partidas)';


--
-- TOC entry 3584 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.name; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.name IS 'Nombre opcional del presupuesto (ej: "Enero 2026 - Plan de ahorro")';


--
-- TOC entry 3585 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN budgets.created_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.budgets.created_at IS 'Fecha y hora de creación del presupuesto';


--
-- TOC entry 3586 (class 0 OID 0)
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
-- TOC entry 3587 (class 0 OID 0)
-- Dependencies: 218
-- Name: TABLE categories; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.categories IS 'Categorías de ingresos y gastos';


--
-- TOC entry 3588 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN categories.type; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.categories.type IS 'Tipo: income (ingreso) o expense (gasto)';


--
-- TOC entry 3589 (class 0 OID 0)
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
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.investments OWNER TO admin;

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
    CONSTRAINT check_transfer_account CHECK (((((type)::text = 'transfer'::text) AND (transfer_account_id IS NOT NULL)) OR ((type)::text <> 'transfer'::text))),
    CONSTRAINT transactions_type_check CHECK (((type)::text = ANY ((ARRAY['income'::character varying, 'expense'::character varying, 'transfer'::character varying])::text[])))
);


ALTER TABLE public.transactions OWNER TO admin;

--
-- TOC entry 3590 (class 0 OID 0)
-- Dependencies: 216
-- Name: TABLE transactions; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.transactions IS 'Todas las transacciones financieras (ingresos, gastos, transferencias)';


--
-- TOC entry 3591 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.amount; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.amount IS 'Importe: positivo para ingresos, negativo para gastos';


--
-- TOC entry 3592 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.type; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.type IS 'Tipo de movimiento: income (ingreso), expense (gasto), transfer (transferencia)';


--
-- TOC entry 3593 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.transfer_account_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.transfer_account_id IS 'Cuenta destino si es una transferencia interna';


--
-- TOC entry 3594 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.external_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.external_id IS 'ID único del banco para evitar duplicados en importaciones';


--
-- TOC entry 3595 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN transactions.category_id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.transactions.category_id IS 'Categoría de la transacción (FK a categories)';


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
-- TOC entry 3596 (class 0 OID 0)
-- Dependencies: 219
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON TABLE public.users IS 'Usuarios del sistema de gestión financiera';


--
-- TOC entry 3597 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.id; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.id IS 'Identificador único del usuario';


--
-- TOC entry 3598 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.email; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.email IS 'Email del usuario (único)';


--
-- TOC entry 3599 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.username; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.username IS 'Nombre de usuario (único, opcional)';


--
-- TOC entry 3600 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.password_hash; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.password_hash IS 'Hash de la contraseña (bcrypt)';


--
-- TOC entry 3601 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.full_name; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.full_name IS '[DEPRECATED] Usar full_name_encrypted - Datos migrados a columna encriptada';


--
-- TOC entry 3602 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.is_active; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.is_active IS 'Si el usuario está activo';


--
-- TOC entry 3603 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.is_admin; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.is_admin IS 'Si el usuario tiene permisos de administrador';


--
-- TOC entry 3604 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.last_login; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.last_login IS 'Última fecha de login';


--
-- TOC entry 3605 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.created_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.created_at IS 'Fecha de creación del registro';


--
-- TOC entry 3606 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.updated_at; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.updated_at IS 'Fecha de última actualización';


--
-- TOC entry 3607 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.profile_picture; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.profile_picture IS '[DEPRECATED] Usar profile_picture_encrypted - Datos migrados a columna encriptada';


--
-- TOC entry 3608 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.email_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.email_encrypted IS 'Email encriptado con AES-256-GCM para cumplimiento GDPR';


--
-- TOC entry 3609 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN users.full_name_encrypted; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON COLUMN public.users.full_name_encrypted IS 'Nombre completo encriptado con AES-256-GCM';


--
-- TOC entry 3610 (class 0 OID 0)
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
-- TOC entry 3611 (class 0 OID 0)
-- Dependencies: 217
-- Name: VIEW v_accounts_summary; Type: COMMENT; Schema: public; Owner: admin
--

COMMENT ON VIEW public.v_accounts_summary IS 'Resumen de cuentas con balance calculado y estadísticas básicas';


--
-- TOC entry 3547 (class 0 OID 16400)
-- Dependencies: 215
-- Data for Name: accounts; Type: TABLE DATA; Schema: public; Owner: admin
--

INSERT INTO public.accounts VALUES ('7f65a306-10aa-434c-b92d-4a6fde2a5692', 'Rand', 'savings', 13367.19, 'EUR', 'Rand', 'ES1234567894569887461233', true, '', '2025-12-30 01:00:49.443013+00', '2026-01-17 01:37:07.318533+00', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', NULL, NULL);
INSERT INTO public.accounts VALUES ('904ca456-5ded-458b-8425-60752a032519', 'Compartida con Gema', 'checking', 1000.00, 'EUR', 'Banco Sabadell', 'es1234567891234568795646', true, '', '2026-01-17 02:15:59.508199+00', '2026-01-17 02:15:59.508199+00', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', NULL, NULL);
INSERT INTO public.accounts VALUES ('4e629dd0-cab6-4783-87b4-6673483fc3d0', 'Revolut', 'checking', 252.55, 'EUR', 'Revolut', 'ES1234567899878654546545', true, '', '2025-12-28 23:31:53.809442+00', '2026-01-17 11:30:41.937427+00', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', NULL, NULL);
INSERT INTO public.accounts VALUES ('5741fca9-7352-41a6-bb0e-ad31c15f588d', 'Bankinter', 'checking', 11500.00, 'EUR', 'Bankinter', 'ES1234123412341234133265', true, '', '2025-12-30 18:29:21.38843+00', '2025-12-30 18:32:46.725005+00', '2b3c618a-dbbc-4e9d-bf47-ee909c6b79c9', NULL, NULL);
INSERT INTO public.accounts VALUES ('74c71e0a-81a9-49e2-8d70-b96cb61b638d', 'Prueba', 'checking', 11538.00, 'EUR', 'Bankinter', 'ES1234569874582563', true, 'Cuenta Principal', '2025-12-22 00:30:33.174306+00', '2025-12-31 01:16:47.494475+00', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', NULL, NULL);
INSERT INTO public.accounts VALUES ('1405a2b1-5a95-4ac8-956d-4b707372d231', 'Principal', 'checking', 12255.06, 'EUR', 'Bankinter', 'ES12123545687895645', true, '', '2025-12-26 00:34:39.441663+00', '2026-01-04 20:53:29.896969+00', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', NULL, NULL);
INSERT INTO public.accounts VALUES ('7d76d928-55d7-4401-8ee0-ab8eec344e34', 'BBVA - prueba', 'checking', 8337.25, 'EUR', 'BBVA', 'ES15849851654621', true, '', '2025-12-28 18:18:03.298426+00', '2026-01-12 00:09:54.09694+00', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', NULL, NULL);
INSERT INTO public.accounts VALUES ('1e1a4596-f1f0-42ba-860a-50a21c2aa005', 'IB - Inversion', 'investment', 15718.00, 'EUR', 'Interactive Brokers', 'ES1234567898977897899878', true, '', '2025-12-28 23:32:23.46171+00', '2026-01-12 00:40:14.909318+00', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', NULL, NULL);


--
-- TOC entry 3553 (class 0 OID 40983)
-- Dependencies: 222
-- Data for Name: budget_items; Type: TABLE DATA; Schema: public; Owner: admin
--

INSERT INTO public.budget_items VALUES ('281a4766-c6cc-4e00-a4a5-191caaeda6c0', '5cd57528-de35-42ff-abee-5e216d0f8ace', 'd307ec0c-3908-4ff7-b13c-ea71619f768f', 500.00, NULL, '2026-01-17 11:35:20.985097+00', '2026-01-17 11:35:20.985097+00');
INSERT INTO public.budget_items VALUES ('5141cf7d-36b6-4f41-814c-d3a3cdc3f067', '5cd57528-de35-42ff-abee-5e216d0f8ace', 'fff297ad-6016-41ec-8639-b3939bfa6745', 50.00, NULL, '2026-01-17 11:35:20.985097+00', '2026-01-17 11:35:20.985097+00');
INSERT INTO public.budget_items VALUES ('7a8b0759-43f2-4f91-92cc-a831ac5c9bf9', '5cd57528-de35-42ff-abee-5e216d0f8ace', 'ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef', 700.00, NULL, '2026-01-17 11:35:20.985097+00', '2026-01-17 11:35:20.985097+00');
INSERT INTO public.budget_items VALUES ('e38e0061-fc0d-4521-a4e2-c399e10bf04f', '43c1554e-1480-410d-9fbc-e3c0fdd1533c', 'd307ec0c-3908-4ff7-b13c-ea71619f768f', 200.00, 'cosas de supermercado mias', '2026-01-17 11:50:37.252249+00', '2026-01-17 11:50:37.252249+00');
INSERT INTO public.budget_items VALUES ('e2826c05-3f06-4f08-8245-06b7d4be04e0', '43c1554e-1480-410d-9fbc-e3c0fdd1533c', 'f14e7ce4-e65d-45de-8fb9-9185c0d91f34', 43.00, NULL, '2026-01-17 11:50:37.252249+00', '2026-01-17 11:50:37.252249+00');
INSERT INTO public.budget_items VALUES ('e17fa5f6-3089-4a08-893d-e1012d76000f', '43c1554e-1480-410d-9fbc-e3c0fdd1533c', 'fff297ad-6016-41ec-8639-b3939bfa6745', 50.00, NULL, '2026-01-17 11:50:37.252249+00', '2026-01-17 11:50:37.252249+00');
INSERT INTO public.budget_items VALUES ('ab9f948b-fd88-43ef-a96f-e143562051ec', '43c1554e-1480-410d-9fbc-e3c0fdd1533c', 'ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef', 650.00, 'Alquiler del mes', '2026-01-17 11:50:37.252249+00', '2026-01-17 11:50:37.252249+00');
INSERT INTO public.budget_items VALUES ('5c180b9f-330f-445f-9884-58432a3e3801', '43c1554e-1480-410d-9fbc-e3c0fdd1533c', 'e97bb263-2d15-43c3-9256-79938404834e', 100.00, NULL, '2026-01-17 11:50:37.252249+00', '2026-01-17 11:50:37.252249+00');
INSERT INTO public.budget_items VALUES ('dcf80f47-7af9-4829-9ee2-e124f77a3580', 'df9584cd-0998-4140-befb-c85e22b8fdd9', 'd307ec0c-3908-4ff7-b13c-ea71619f768f', 500.00, NULL, '2026-01-17 12:30:49.857695+00', '2026-01-17 12:30:49.857695+00');
INSERT INTO public.budget_items VALUES ('064a1463-f6bc-445e-a746-316e30ee2eef', 'df9584cd-0998-4140-befb-c85e22b8fdd9', 'fff297ad-6016-41ec-8639-b3939bfa6745', 50.00, NULL, '2026-01-17 12:30:49.857695+00', '2026-01-17 12:30:49.857695+00');
INSERT INTO public.budget_items VALUES ('069e2d8c-831a-4935-adee-90c2de913458', 'df9584cd-0998-4140-befb-c85e22b8fdd9', 'ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef', 700.00, NULL, '2026-01-17 12:30:49.857695+00', '2026-01-17 12:30:49.857695+00');
INSERT INTO public.budget_items VALUES ('d21fa3ee-0e06-4633-bb93-b45e38868fb8', 'df9584cd-0998-4140-befb-c85e22b8fdd9', '0c5118f0-05ed-4da0-bcb2-383d265e46b1', 25.00, NULL, '2026-01-17 12:30:49.857695+00', '2026-01-17 12:30:49.857695+00');


--
-- TOC entry 3552 (class 0 OID 40961)
-- Dependencies: 221
-- Data for Name: budgets; Type: TABLE DATA; Schema: public; Owner: admin
--

INSERT INTO public.budgets VALUES ('43c1554e-1480-410d-9fbc-e3c0fdd1533c', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 1, 2026, 943.00, 'Enero 2026', '2026-01-16 22:03:58.020213+00', '2026-01-17 01:58:28.980856+00');
INSERT INTO public.budgets VALUES ('5cd57528-de35-42ff-abee-5e216d0f8ace', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 2, 2026, 1250.00, 'Febrero 2026', '2026-01-17 11:35:20.985097+00', '2026-01-17 11:35:20.985097+00');
INSERT INTO public.budgets VALUES ('df9584cd-0998-4140-befb-c85e22b8fdd9', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 3, 2026, 1250.00, 'Febrero 2026', '2026-01-17 11:37:09.827612+00', '2026-01-17 11:37:09.827612+00');


--
-- TOC entry 3549 (class 0 OID 16456)
-- Dependencies: 218
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: admin
--

INSERT INTO public.categories VALUES ('d307ec0c-3908-4ff7-b13c-ea71619f768f', 'Supermercado', 'expense', '#10B981', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('2d854969-3a82-4436-bc2f-e5393fc236a6', 'Restaurantes', 'expense', '#F59E0B', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('1960f361-abb2-4c4b-a8be-87aca42cb1d6', 'Transporte', 'expense', '#3B82F6', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('e75ee282-4e27-4c80-b6e1-667cf1e8a9d3', 'Coche', 'expense', '#6366F1', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('f14e7ce4-e65d-45de-8fb9-9185c0d91f34', 'Bicicleta', 'expense', '#14B8A6', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('34ff018a-6826-4ab8-826f-ef22e629791e', 'Compras Online', 'expense', '#EC4899', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('fff297ad-6016-41ec-8639-b3939bfa6745', 'Amazon', 'expense', '#FF9900', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef', 'Alquiler', 'expense', '#EF4444', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('e97bb263-2d15-43c3-9256-79938404834e', 'Ocio/Deporte', 'expense', '#06B6D4', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('48e4d0cd-6292-4c58-bf10-2379b8c5d3b2', 'Viajes', 'expense', '#0EA5E9', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('b0ce5d72-ad4a-44f2-bf0a-c629e17759dd', 'Salud/Cuidados', 'expense', '#DC2626', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('275d2d2c-2901-40a4-807f-01b6b0a89998', 'Gastos Fijos', 'expense', '#6B7280', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('64445688-c033-4eaa-85cf-935c18fa6db4', 'Inversión', 'expense', '#059669', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('0c5118f0-05ed-4da0-bcb2-383d265e46b1', 'Bizum', 'expense', '#0891B2', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('7203913a-2b15-45dc-83c2-c5880caa6121', 'Regalos', 'expense', '#EC4899', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('20113046-6b5f-4a6c-9536-6b473f6582cc', 'Gastos Personales', 'expense', '#DB2777', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('f107f866-accf-4c57-8276-669fc2f31004', 'Sin Categorizar', 'expense', '#94A3B8', '2025-12-21 13:31:20.24344+00');
INSERT INTO public.categories VALUES ('313d81c7-4346-46ec-98ea-672e8cd31a1c', 'Freelance', 'income', '#14B8A6', '2025-12-21 13:31:20.259445+00');
INSERT INTO public.categories VALUES ('b545d5c3-3cdd-4198-868c-58cb7873c49b', 'Inversiones', 'income', '#059669', '2025-12-21 13:31:20.259445+00');
INSERT INTO public.categories VALUES ('fe58d212-e793-4237-8cc4-3bc8b4ec0c2f', 'Ingreso - Bizum', 'income', '#22C55E', '2025-12-21 13:31:20.259445+00');
INSERT INTO public.categories VALUES ('a66db8ff-825b-46bf-9d71-5e769daea823', 'Intereses', 'income', '#059669', '2025-12-21 13:32:56.377826+00');
INSERT INTO public.categories VALUES ('88d52b3c-9d8f-4008-bb51-5adb398ac4de', 'Transferencia', 'expense', '#2738F5', '2025-12-30 00:06:18.297+00');
INSERT INTO public.categories VALUES ('94c7e01f-ee86-4684-9bb8-37e8a4d378e0', 'Ingreso', 'income', '#2738F5', '2025-12-21 13:31:20.259445+00');
INSERT INTO public.categories VALUES ('056a82ec-cebe-46a2-89e8-56f6118f7283', 'Salario', 'income', '#3b82f6', '2025-12-21 13:31:20.259445+00');


--
-- TOC entry 3551 (class 0 OID 32847)
-- Dependencies: 220
-- Data for Name: investments; Type: TABLE DATA; Schema: public; Owner: admin
--

INSERT INTO public.investments VALUES ('db5639f0-92d5-4c99-bbf4-ee30df9feabd', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'ONON', 'On Holding AG Class A', 23.0000, 45.11, '2026-01-13', NULL, NULL, 'active', NULL, '2026-01-13 17:46:28.121439+00', '2026-01-13 17:46:28.121439+00');
INSERT INTO public.investments VALUES ('eee8451e-c34c-4d0b-af09-2c183d584e31', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'LLY', 'Lilly(Eli) & Company', 1.0000, 1013.00, '2026-01-13', NULL, NULL, 'active', NULL, '2026-01-13 17:49:19.307419+00', '2026-01-13 17:49:19.307419+00');
INSERT INTO public.investments VALUES ('01dc07f9-1fd1-4b10-b809-d75138dac5af', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'AS', 'AMER SPORTS INC', 22.0000, 39.15, '2026-01-13', NULL, NULL, 'active', NULL, '2026-01-13 22:13:03.166848+00', '2026-01-13 22:13:03.166848+00');
INSERT INTO public.investments VALUES ('a52c7a7c-ae61-43ed-948d-72aa4eea4258', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'ZETA', 'ZETA GLOBAL HOLDINGS CORP-A', 40.0000, 23.52, '2026-01-13', NULL, NULL, 'active', NULL, '2026-01-13 22:13:30.48413+00', '2026-01-13 22:13:30.48413+00');
INSERT INTO public.investments VALUES ('0a61ea83-383c-4f77-b76a-f42ec626f51a', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'CMG', 'Chipotle Mexican Grill', 91.0000, 55.75, '2026-01-13', NULL, NULL, 'active', NULL, '2026-01-13 17:18:05.979319+00', '2026-01-13 17:18:05.979319+00');
INSERT INTO public.investments VALUES ('5904a77a-563d-4284-aa89-456f198e6f1e', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'AMZN', 'Amazon.com Inc', 12.0000, 191.73, '2024-06-12', NULL, NULL, 'active', NULL, '2026-01-13 17:23:52.697622+00', '2026-01-13 17:23:52.697622+00');
INSERT INTO public.investments VALUES ('cac0e2f1-834e-49a9-a2d1-c1adcc8a5fd8', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'META', 'META PLATFORMS INC-CLASS A', 1.0000, 643.87, '2025-11-12', NULL, NULL, 'active', NULL, '2026-01-13 22:07:27.842229+00', '2026-01-13 22:07:27.842229+00');
INSERT INTO public.investments VALUES ('4a35fb03-a507-44f6-aa8d-0ee86598744b', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'MMM', '3M CO', 6.0000, 166.83, '2026-01-13', NULL, NULL, 'sold', 'Presenta resultados el martes 20/01', '2026-01-13 22:13:59.995049+00', '2026-01-16 16:44:17.740904+00');
INSERT INTO public.investments VALUES ('a876c593-4697-4610-abde-68fcaf4f27b9', '0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'TSLA', 'TESLA INC', 4.0000, 438.00, '2026-01-17', NULL, NULL, 'sold', '', '2026-01-17 11:44:09.724049+00', '2026-01-17 11:44:25.158759+00');


--
-- TOC entry 3548 (class 0 OID 16416)
-- Dependencies: 216
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: admin
--

INSERT INTO public.transactions VALUES ('e227ee06-7b37-49c4-97f1-129a66b376e6', '74c71e0a-81a9-49e2-8d70-b96cb61b638d', '2025-12-22', 1200.20, 'prueba ingreso', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-22 00:55:07.263863+00', '2025-12-29 11:33:12.515387+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('e0e123fa-e2eb-4741-8855-dfff8be69b0b', '74c71e0a-81a9-49e2-8d70-b96cb61b638d', '2025-12-29', 700.00, 'Alquiler mes diciembre', 'expense', NULL, '', '{alquiler}', NULL, 'manual', '2025-12-29 17:52:29.239825+00', '2025-12-29 17:52:29.239825+00', 'ecaf2bf5-3fde-4354-89bc-0d3bd74bfaef');
INSERT INTO public.transactions VALUES ('9fa9b260-3648-4334-834b-45c893c5e0e7', '74c71e0a-81a9-49e2-8d70-b96cb61b638d', '2025-12-22', 10.00, 'prueba transaccion', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-22 00:46:57.310599+00', '2025-12-29 22:43:57.824742+00', '275d2d2c-2901-40a4-807f-01b6b0a89998');
INSERT INTO public.transactions VALUES ('50cfeb36-bc34-43d8-8655-2f1a6bf78f52', '74c71e0a-81a9-49e2-8d70-b96cb61b638d', '2025-12-22', 8.20, '2º prueba transaccion', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-22 00:54:25.574737+00', '2025-12-29 22:43:57.879965+00', 'f14e7ce4-e65d-45de-8fb9-9185c0d91f34');
INSERT INTO public.transactions VALUES ('8aad320a-9c9b-4360-ac64-9d65414a47ad', '1e1a4596-f1f0-42ba-860a-50a21c2aa005', '2025-12-30', 123.00, 'prueba1 ', 'income', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '', '{}', NULL, 'manual', '2025-12-30 00:41:04.571331+00', '2025-12-30 00:41:04.571331+00', '94c7e01f-ee86-4684-9bb8-37e8a4d378e0');
INSERT INTO public.transactions VALUES ('024708f1-29f8-45c3-8bd2-3a1f513cb2f6', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-12-30', 123.00, 'prueba1 ', 'expense', '1e1a4596-f1f0-42ba-860a-50a21c2aa005', '', '{}', NULL, 'manual', '2025-12-30 00:41:04.571449+00', '2025-12-30 00:41:04.571449+00', '88d52b3c-9d8f-4008-bb51-5adb398ac4de');
INSERT INTO public.transactions VALUES ('2253d0f3-b6a7-4cc9-9010-a6d3d8b7691f', '7d76d928-55d7-4401-8ee0-ab8eec344e34', '2025-12-30', 1500.00, 'nomina', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-30 00:44:01.231539+00', '2025-12-30 00:44:01.231539+00', '056a82ec-cebe-46a2-89e8-56f6118f7283');
INSERT INTO public.transactions VALUES ('fbc03a33-56cf-4476-a9b3-96771426bdbc', '5741fca9-7352-41a6-bb0e-ad31c15f588d', '2025-12-30', 1500.00, 'Salario febrero ', 'income', NULL, '', '{salario}', NULL, 'manual', '2025-12-30 18:32:46.725005+00', '2025-12-30 18:32:46.725005+00', '056a82ec-cebe-46a2-89e8-56f6118f7283');
INSERT INTO public.transactions VALUES ('801a3f09-0c8d-41b4-84fd-30b5d0a33e23', '74c71e0a-81a9-49e2-8d70-b96cb61b638d', '2025-07-31', 222.00, 'Mercadona', 'expense', NULL, '', '{}', NULL, 'automatico', '2025-12-31 01:16:47.494475+00', '2025-12-31 01:16:47.494475+00', 'e97bb263-2d15-43c3-9256-79938404834e');
INSERT INTO public.transactions VALUES ('5cf783fe-c0f8-418f-a97d-67dd0100ba81', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-01-31', 59.99, 'Wellhub', 'expense', NULL, 'Pago con tarjeta', '{}', NULL, 'manual', '2025-12-31 02:07:08.453163+00', '2025-12-31 02:07:08.453163+00', NULL);
INSERT INTO public.transactions VALUES ('8ca2066b-7f38-45c9-afdf-160de68f3163', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-02-02', 28.50, 'Bizum a Maria Olaria', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:07:08.60512+00', '2025-12-31 02:07:08.60512+00', NULL);
INSERT INTO public.transactions VALUES ('98c49d1d-60ec-4d1c-8d84-917a222885d6', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-02-02', 14.20, 'Bizum a Gema Porcar', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:07:08.707466+00', '2025-12-31 02:07:08.707466+00', NULL);
INSERT INTO public.transactions VALUES ('abcd8fbb-0345-40b6-b904-fdd85ac9d508', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-01-30', -17.99, 'Spotify - Suscripcion', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:41.680718+00', '2025-12-31 02:25:41.680718+00', '275d2d2c-2901-40a4-807f-01b6b0a89998');
INSERT INTO public.transactions VALUES ('8d76f104-00d5-4c10-8d43-2d03fb29f5ad', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-01-31', -59.99, 'Wellhub - Gimnasio', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:41.814717+00', '2025-12-31 02:25:41.814717+00', 'e97bb263-2d15-43c3-9256-79938404834e');
INSERT INTO public.transactions VALUES ('ca91ae09-58c7-421c-b864-3b0d7db9721e', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-01', -1019.64, 'Recibo Platinum', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:41.882241+00', '2025-12-31 02:25:41.882241+00', '275d2d2c-2901-40a4-807f-01b6b0a89998');
INSERT INTO public.transactions VALUES ('1f75e044-a99f-4ded-9f4c-4090acd0f6c5', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-01', -0.99, 'Mercadona', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:41.944557+00', '2025-12-31 02:25:41.944557+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');
INSERT INTO public.transactions VALUES ('1a5d548e-b7fd-4f91-b0ed-717d7f0a7e21', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-02', 28.50, 'Bizum a Maria Olaria', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.001669+00', '2025-12-31 02:25:42.001669+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('183408e3-f099-45ea-9b37-5d022b1947be', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-02', 14.20, 'Bizum a Gema Porcar', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.065686+00', '2025-12-31 02:25:42.065686+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('02dc78a6-f198-4fbb-95ef-5a628155da1a', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-03', -30.00, 'Bizum a Jose Luis de la C', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.119037+00', '2025-12-31 02:25:42.119037+00', '0c5118f0-05ed-4da0-bcb2-383d265e46b1');
INSERT INTO public.transactions VALUES ('6d8f00db-b995-4f46-8956-d756b2e1b051', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-04', -4.50, 'Citricos Oroplana', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.176048+00', '2025-12-31 02:25:42.176048+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');
INSERT INTO public.transactions VALUES ('bef8c219-922b-4647-9261-65f896d1fee3', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-04', -10.99, 'Amazon', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.234744+00', '2025-12-31 02:25:42.234744+00', 'fff297ad-6016-41ec-8639-b3939bfa6745');
INSERT INTO public.transactions VALUES ('04ca3f0d-921f-4ae3-b684-cf57a38784b5', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-05', -16.30, 'Mercadona', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.290876+00', '2025-12-31 02:25:42.290876+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');
INSERT INTO public.transactions VALUES ('2efb75c5-e952-4ef4-a3ab-3bb9bf681194', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-05', 2.25, 'Anulacion Mercadona', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.364886+00', '2025-12-31 02:25:42.364886+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');
INSERT INTO public.transactions VALUES ('20afe133-e3a5-445a-a6ef-141c32b2810e', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-08', -50.00, 'Entrenamiento +Quekms', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.421485+00', '2025-12-31 02:25:42.421485+00', 'e97bb263-2d15-43c3-9256-79938404834e');
INSERT INTO public.transactions VALUES ('06283afe-a341-44c9-969f-8f0d7d81cbb3', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-10', -369.00, 'PcComponentes', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.474497+00', '2025-12-31 02:25:42.474497+00', '34ff018a-6826-4ab8-826f-ef22e629791e');
INSERT INTO public.transactions VALUES ('12c3d188-26b3-4800-9b5f-34963becf862', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-11', -10.00, 'Repostaje Ballenoil', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.536226+00', '2025-12-31 02:25:42.536226+00', '1960f361-abb2-4c4b-a8be-87aca42cb1d6');
INSERT INTO public.transactions VALUES ('6d497ede-1cb2-40fc-9159-adb18b24f86c', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-13', -35.00, 'Bizum a Jordi Martinez', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.591442+00', '2025-12-31 02:25:42.591442+00', '0c5118f0-05ed-4da0-bcb2-383d265e46b1');
INSERT INTO public.transactions VALUES ('79b5fb9e-24f6-4d0d-8155-8dc24669d047', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-15', 17.90, 'Bizum de Lledo Garcia', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.647449+00', '2025-12-31 02:25:42.647449+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('428a42ce-7ab4-4a01-b1a5-6a404ccdc09b', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-15', -11.00, 'Revolut', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.702674+00', '2025-12-31 02:25:42.702674+00', 'f107f866-accf-4c57-8276-669fc2f31004');
INSERT INTO public.transactions VALUES ('9d792f39-653d-4b14-a36a-b6cbfdaae0c0', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-15', -54.97, 'Supeco Torrijos', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.757967+00', '2025-12-31 02:25:42.757967+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');
INSERT INTO public.transactions VALUES ('44a86e3d-58e6-4a3c-b4a8-a74214c49fe7', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-16', 55.00, 'Bizum de Gema Porcar', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.812953+00', '2025-12-31 02:25:42.812953+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('cf0e10b1-476f-41df-a6cf-aa4f30b590dc', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-16', 4.00, 'Bizum de Iris Gonzalez', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.87429+00', '2025-12-31 02:25:42.87429+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('015dd1e9-4940-43a1-95a8-178f74e692e6', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-16', -27.20, 'Pasteleria Gito', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.932122+00', '2025-12-31 02:25:42.932122+00', '2d854969-3a82-4436-bc2f-e5393fc236a6');
INSERT INTO public.transactions VALUES ('74d79095-af1d-451e-a888-0df5fc0cd66a', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-16', -30.00, 'Repostaje Ballenoil', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:42.991807+00', '2025-12-31 02:25:42.991807+00', '1960f361-abb2-4c4b-a8be-87aca42cb1d6');
INSERT INTO public.transactions VALUES ('00174a09-f6a2-4770-867d-5e2eba8e0fe6', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-17', 8.00, 'Bizum de Sergio Rodriguez', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.04671+00', '2025-12-31 02:25:43.04671+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('9bca8a46-3a55-4280-af09-ba7925ace1bf', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-17', -3.00, 'Citricos Oroplana', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.109909+00', '2025-12-31 02:25:43.109909+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');
INSERT INTO public.transactions VALUES ('95ebbbcc-d96a-4f30-bd58-5dc4ed902fc8', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-19', 350.00, 'Bizum de Gema Porcar', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.160406+00', '2025-12-31 02:25:43.160406+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('6dcdd69a-c768-4474-a3cf-c22eba91e7f1', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-19', -35.00, 'Clinica Segarra', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.228877+00', '2025-12-31 02:25:43.228877+00', 'b0ce5d72-ad4a-44f2-bf0a-c629e17759dd');
INSERT INTO public.transactions VALUES ('d499b65e-39b6-45e1-ae38-32c409369ef5', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-19', -51.35, 'Lidl', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.291799+00', '2025-12-31 02:25:43.291799+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');
INSERT INTO public.transactions VALUES ('3a7afe68-509f-44e1-8011-c842133e3e01', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-19', -21.99, 'Wellhub - Gimnasio', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.35711+00', '2025-12-31 02:25:43.35711+00', 'e97bb263-2d15-43c3-9256-79938404834e');
INSERT INTO public.transactions VALUES ('1f61e864-a5ed-4a7a-ba1f-7c2279101f53', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-22', -61.00, 'Revolut', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.423395+00', '2025-12-31 02:25:43.423395+00', 'f107f866-accf-4c57-8276-669fc2f31004');
INSERT INTO public.transactions VALUES ('2ee039c2-927e-417b-8a2e-2693ed15c2f9', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-23', -7.70, 'Churreria Cazorla', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.477762+00', '2025-12-31 02:25:43.477762+00', '2d854969-3a82-4436-bc2f-e5393fc236a6');
INSERT INTO public.transactions VALUES ('9a4d4f27-dcb5-4f0a-a824-aeb454d61a09', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-24', -200.00, 'Transferencia a Ruben de la Cruz Diaz', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.54939+00', '2025-12-31 02:25:43.54939+00', '88d52b3c-9d8f-4008-bb51-5adb398ac4de');
INSERT INTO public.transactions VALUES ('164867d1-c365-4ec2-a42d-370db17bfa9c', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-26', -650.00, 'Transferencia a Ruben de la Cruz Diaz', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.609169+00', '2025-12-31 02:25:43.609169+00', '88d52b3c-9d8f-4008-bb51-5adb398ac4de');
INSERT INTO public.transactions VALUES ('9c6b5014-7ec4-4f75-bd08-bfec64b31aea', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-26', -33.00, 'Fundacio Dali', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.725715+00', '2025-12-31 02:25:43.725715+00', 'e97bb263-2d15-43c3-9256-79938404834e');
INSERT INTO public.transactions VALUES ('1a2e9de2-eeef-4383-b59d-2356450f72b9', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-27', 2182.81, 'Nomina Indra Soluciones', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.786598+00', '2025-12-31 02:25:43.786598+00', '056a82ec-cebe-46a2-89e8-56f6118f7283');
INSERT INTO public.transactions VALUES ('07884bae-cb69-445b-9929-d14575281bef', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-27', -100.00, 'Bizum de Gema Porcar', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.848179+00', '2025-12-31 02:25:43.848179+00', '0c5118f0-05ed-4da0-bcb2-383d265e46b1');
INSERT INTO public.transactions VALUES ('2c0f193e-9845-4435-9aec-c3915a383cf5', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-28', -226.00, 'Transferencia a Ruben de la Cruz Diaz', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.911108+00', '2025-12-31 02:25:43.911108+00', '88d52b3c-9d8f-4008-bb51-5adb398ac4de');
INSERT INTO public.transactions VALUES ('99d97e1b-7ac7-4530-89a9-49aa28e30722', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-28', -450.00, 'Transferencia a Ruben de la Cruz Diaz', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.977429+00', '2025-12-31 02:25:43.977429+00', '88d52b3c-9d8f-4008-bb51-5adb398ac4de');
INSERT INTO public.transactions VALUES ('2ccf007c-85c4-47cc-abce-a056dbfaeac1', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-03-06', 60.00, 'Bizum a Jose Luis', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:38:20.216296+00', '2025-12-31 02:38:20.216296+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('0e4781f5-6db8-4afd-9a49-4071556e3e66', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-03-08', 7.30, 'Forn Cusi', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:38:20.313547+00', '2025-12-31 02:38:20.313547+00', '2d854969-3a82-4436-bc2f-e5393fc236a6');
INSERT INTO public.transactions VALUES ('ed2e8daf-ab6b-4c37-a515-d4c62bd4ba02', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-03-08', 50.00, 'Entrenamiento Quekms', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:38:20.383171+00', '2025-12-31 02:38:20.383171+00', 'e97bb263-2d15-43c3-9256-79938404834e');
INSERT INTO public.transactions VALUES ('c15af9a2-bd0a-41d9-865d-9b3a67e0082e', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-03-10', 100.00, 'Bizum a Gema Porcar', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:38:20.492229+00', '2025-12-31 02:38:20.492229+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('1533dc12-7e24-413b-a57b-ee08e392ad82', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-03-11', 71.00, 'Klassmark (Anulación)', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:38:20.569675+00', '2025-12-31 02:38:20.569675+00', '94c7e01f-ee86-4684-9bb8-37e8a4d378e0');
INSERT INTO public.transactions VALUES ('2aac9e13-211f-4628-9e73-519a83a50b7e', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-03-15', 4.00, 'Bizum a Rosa Maria Molin', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:38:20.627112+00', '2025-12-31 02:38:20.627112+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('a16dab99-54eb-46d8-a35e-ff7ba910a16c', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-03-18', 150.00, 'Bizum a Gema Porcar', 'income', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:38:20.684785+00', '2025-12-31 02:38:20.684785+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('e4aac559-b86d-4235-bbc8-0437d993104c', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-02-15', 11.00, 'Revolut', 'expense', NULL, '', '{}', NULL, 'manual', '2026-01-01 18:54:14.698582+00', '2026-01-01 18:54:14.698582+00', '7203913a-2b15-45dc-83c2-c5880caa6121');
INSERT INTO public.transactions VALUES ('8a3f505c-0531-49a5-b18d-a0a88e89581b', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-02-16', 27.20, 'Pasteleria Cafeteria Gito', 'expense', NULL, '', '{}', NULL, 'manual', '2026-01-01 18:54:14.949768+00', '2026-01-01 18:54:14.949768+00', '2d854969-3a82-4436-bc2f-e5393fc236a6');
INSERT INTO public.transactions VALUES ('673e9edf-43d0-4130-bc8f-051489fe0c16', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-02-16', 30.00, 'Ballenoil Castellon - Repostaje', 'expense', NULL, '', '{}', NULL, 'manual', '2026-01-01 18:54:14.996638+00', '2026-01-01 18:54:14.996638+00', '1960f361-abb2-4c4b-a8be-87aca42cb1d6');
INSERT INTO public.transactions VALUES ('952ce1a3-5151-4761-9428-69bbec8f8950', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-02-19', 350.00, 'Bizum de Gema Porcar', 'income', NULL, '', '{}', NULL, 'manual', '2026-01-01 18:54:15.048959+00', '2026-01-01 18:54:15.048959+00', 'fe58d212-e793-4237-8cc4-3bc8b4ec0c2f');
INSERT INTO public.transactions VALUES ('b5e51925-2dae-448b-8c03-7815ef4614bb', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-02-22', 61.00, 'Revolut', 'expense', NULL, '', '{}', NULL, 'manual', '2026-01-01 18:54:15.102835+00', '2026-01-01 18:54:15.102835+00', 'fff297ad-6016-41ec-8639-b3939bfa6745');
INSERT INTO public.transactions VALUES ('50ef95c2-26f4-4ade-9e1f-0fa519fc789b', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2025-02-26', 33.00, 'Fundacio Dali Web', 'expense', NULL, '', '{}', NULL, 'manual', '2026-01-01 18:54:15.233228+00', '2026-01-01 18:54:15.233228+00', 'e97bb263-2d15-43c3-9256-79938404834e');
INSERT INTO public.transactions VALUES ('90fb1c38-dd22-4a0f-9d8c-96d268dd4124', '1405a2b1-5a95-4ac8-956d-4b707372d231', '2025-11-17', 10.10, 'Pago de ticket', 'expense', NULL, '', '{}', NULL, 'manual', '2026-01-04 20:53:29.896969+00', '2026-01-04 20:53:29.896969+00', '1960f361-abb2-4c4b-a8be-87aca42cb1d6');
INSERT INTO public.transactions VALUES ('5a7458ca-64e3-4534-a268-adb6855a156b', '7d76d928-55d7-4401-8ee0-ab8eec344e34', '2026-01-11', 2000.00, 'salario enero', 'income', NULL, '', '{}', NULL, 'manual', '2026-01-11 20:05:44.094228+00', '2026-01-11 20:05:44.094228+00', '056a82ec-cebe-46a2-89e8-56f6118f7283');
INSERT INTO public.transactions VALUES ('7e5eaa1a-487f-4592-b519-023615828f68', '7d76d928-55d7-4401-8ee0-ab8eec344e34', '2026-01-12', 250.00, 'compra mercadona', 'expense', NULL, '', '{}', NULL, 'manual', '2026-01-12 00:09:54.09694+00', '2026-01-12 00:09:54.09694+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');
INSERT INTO public.transactions VALUES ('e4cc7f0f-a77a-4c9e-92fe-a1923327e758', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2026-01-12', 800.00, 'transfer para cubrir rojos', 'income', '1e1a4596-f1f0-42ba-860a-50a21c2aa005', '', '{}', NULL, 'manual', '2026-01-12 00:40:14.777476+00', '2026-01-12 00:40:14.777476+00', '94c7e01f-ee86-4684-9bb8-37e8a4d378e0');
INSERT INTO public.transactions VALUES ('7202ff7f-5f63-410a-81a9-b47c827b1bb7', '1e1a4596-f1f0-42ba-860a-50a21c2aa005', '2026-01-12', 800.00, 'transfer para cubrir rojos', 'expense', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '', '{}', NULL, 'manual', '2026-01-12 00:40:14.909318+00', '2026-01-12 00:40:14.909318+00', '88d52b3c-9d8f-4008-bb51-5adb398ac4de');
INSERT INTO public.transactions VALUES ('c5674297-499c-4781-81f4-40b20dc2da28', '7f65a306-10aa-434c-b92d-4a6fde2a5692', '2026-01-15', 310.00, 'compra', 'expense', NULL, '', '{}', NULL, 'manual', '2026-01-15 23:53:17.427241+00', '2026-01-15 23:53:17.427241+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');
INSERT INTO public.transactions VALUES ('3c7bf863-4abd-4a81-a65c-89d96b9558d7', '4e629dd0-cab6-4783-87b4-6673483fc3d0', '2025-02-26', -3.50, 'Citricos Oroplana', 'expense', NULL, '', '{}', NULL, 'manual', '2025-12-31 02:25:43.665977+00', '2026-01-17 01:36:47.649415+00', 'd307ec0c-3908-4ff7-b13c-ea71619f768f');


--
-- TOC entry 3550 (class 0 OID 24577)
-- Dependencies: 219
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: admin
--

INSERT INTO public.users VALUES ('7f376528-f49c-4799-b0d6-5eeb91ee9475', 'admin@example.com', 'admin', '$2b$12$Z2Q.1US7JaXgVZhfFgURcunROM1S8P2S1bNzdupKbg61jtciABJDe', 'Administrador del Sistema', true, true, NULL, '2025-12-23 00:18:26.615609+00', '2025-12-23 00:18:26.615609+00', NULL, NULL, NULL, NULL);
INSERT INTO public.users VALUES ('cbdfa49e-2774-4922-94da-dc3380504322', 'fernan@correo.es', 'Fernan', '$2b$12$eRcz0dYRJhvP03XX9tDx6OSq1IM4DiuW9pwf8YotxNdzeg1.rO5wS', 'Fernando Lazaro', true, false, '2026-01-17 13:23:36.966502+00', '2025-12-25 17:45:39.498305+00', '2026-01-17 12:23:36.714516+00', NULL, NULL, NULL, NULL);
INSERT INTO public.users VALUES ('51516172-a49e-4351-8c6b-247dc93815d9', 'user@example.com', 'usuario', '$2b$12$gqfqqgn3tKtYATXSZ1fTduql43VGsgSQlhyyjvOY2bNM.nE16Onry', 'Usuario Regular', true, false, '2025-12-24 12:22:53.785147+00', '2025-12-23 00:18:26.619045+00', '2025-12-24 11:22:53.488049+00', NULL, NULL, NULL, NULL);
INSERT INTO public.users VALUES ('0ce003d1-8cfc-4c99-90ab-09f302f9ac41', 'ruben_cruz92@hotmail.com', 'ruben', '$2b$12$VFAohUsbVs0jdzidxObJ1ennngQtLjY1WE0eViRTtDxZgUYuJXlra', 'Ruben de la Cruz Diaz', true, false, '2026-01-19 20:59:07.290513+00', '2025-12-24 14:06:28.451108+00', '2026-01-19 19:59:06.998465+00', NULL, NULL, NULL, NULL);
INSERT INTO public.users VALUES ('2b3c618a-dbbc-4e9d-bf47-ee909c6b79c9', 'fernando@correo.es', 'Fernando', '$2b$12$1F/78spXTGEhrkiHG2Zqve165e2WHOaDdx3gmK8yWIBNITBzLRhry', 'F Lazaro', true, false, '2025-12-30 19:28:27.366165+00', '2025-12-30 18:26:49.579426+00', '2025-12-30 18:28:27.134409+00', NULL, NULL, NULL, NULL);


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


-- Completed on 2026-02-11 23:38:02

--
-- PostgreSQL database dump complete
--

\unrestrict Asheq61SPD2shhW3lSfeuQ9TYGDeSIO1dDmREFrhJtg8wyiVNyLpWi5MKb1a4HZ

