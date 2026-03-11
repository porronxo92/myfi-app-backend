-- =============================================================
-- SEED DATA: app_finance
-- Generado: 2026-03-11
-- Usuario de prueba: Test1 / Test@1234
-- PostgreSQL 15
-- =============================================================

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

-- =============================================================
-- LIMPIAR DATOS PREVIOS (orden inverso de FK)
-- =============================================================
DELETE FROM public.budget_items;
DELETE FROM public.budgets;
DELETE FROM public.investments;
DELETE FROM public.transactions;
DELETE FROM public.accounts;
DELETE FROM public.categories;
DELETE FROM public.users;


-- =============================================================
-- USUARIOS
-- Usuario 1: Test1 / Test@1234  (admin)
-- Usuario 2: jgarcia / Test@1234 (usuario normal)
-- Nota: password_hash generado con bcrypt cost=10 para "Test@1234"
-- =============================================================

INSERT INTO public.users (id, email, username, password_hash, full_name, is_active, is_admin, last_login, created_at, updated_at)
VALUES
  (
    '11111111-1111-4111-8111-111111111111',
    'test1@financeapp.com',
    'Test1',
    -- bcrypt hash de "Test@1234"
    '$2b$12$2zumh7u864RwrImAET.Zc.0pDjSX4bKo0fKYaKE46Sh9buHldc6VW',
    'Test User Admin',
    true,
    true,
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '90 days',
    NOW() - INTERVAL '2 hours'
  ),
  (
    '22222222-2222-4222-8222-222222222222',
    'jgarcia@financeapp.com',
    'jgarcia',
    '$2b$12$2zumh7u864RwrImAET.Zc.0pDjSX4bKo0fKYaKE46Sh9buHldc6VW',
    'Juan García López',
    true,
    false,
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '180 days',
    NOW() - INTERVAL '1 day'
  );


-- =============================================================
-- CATEGORÍAS (compartidas, sin user_id)
-- =============================================================

INSERT INTO public.categories (id, name, type, color, created_at)
VALUES
  -- INGRESOS
  ('c4000001-0000-4000-8000-000000000001', 'Salario',            'income',  '#22C55E', NOW() - INTERVAL '90 days'),
  ('c4000001-0000-4000-8000-000000000002', 'Freelance',          'income',  '#16A34A', NOW() - INTERVAL '90 days'),
  ('c4000001-0000-4000-8000-000000000003', 'Dividendos',         'income',  '#15803D', NOW() - INTERVAL '90 days'),
  ('c4000001-0000-4000-8000-000000000004', 'Reembolsos',         'income',  '#4ADE80', NOW() - INTERVAL '90 days'),
  ('c4000001-0000-4000-8000-000000000005', 'Otros ingresos',     'income',  '#86EFAC', NOW() - INTERVAL '90 days'),
  -- GASTOS
  ('c4000002-0000-4000-8000-000000000001', 'Alquiler / Hipoteca','expense', '#EF4444', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000002', 'Supermercado',       'expense', '#F97316', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000003', 'Restaurantes',       'expense', '#FB923C', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000004', 'Transporte',         'expense', '#FACC15', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000005', 'Salud',              'expense', '#A78BFA', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000006', 'Ocio y entretenimiento','expense','#60A5FA', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000007', 'Suscripciones',      'expense', '#818CF8', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000008', 'Ropa y calzado',     'expense', '#F472B6', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000009', 'Educación',          'expense', '#34D399', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000010', 'Suministros del hogar','expense','#94A3B8', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000011', 'Viajes',             'expense', '#38BDF8', NOW() - INTERVAL '90 days'),
  ('c4000002-0000-4000-8000-000000000012', 'Seguros',            'expense', '#CBD5E1', NOW() - INTERVAL '90 days');


-- =============================================================
-- CUENTAS — Usuario Test1
-- =============================================================

INSERT INTO public.accounts (id, name, type, balance, currency, bank_name, account_number, is_active, notes, created_at, updated_at, user_id)
VALUES
  (
    'acc11111-0000-4000-8000-000000000001',
    'Cuenta Corriente Principal',
    'checking',
    3250.75,
    'EUR',
    'Banco Santander',
    'ES12 0049 0000 0121 3456 7890',
    true,
    'Cuenta principal nómina',
    NOW() - INTERVAL '90 days',
    NOW() - INTERVAL '1 day',
    '11111111-1111-4111-8111-111111111111'
  ),
  (
    'acc11111-0000-4000-8000-000000000002',
    'Cuenta Ahorro Emergencias',
    'savings',
    12000.00,
    'EUR',
    'Banco Santander',
    'ES12 0049 0000 0199 8765 4321',
    true,
    'Fondo de emergencia 6 meses',
    NOW() - INTERVAL '90 days',
    NOW() - INTERVAL '7 days',
    '11111111-1111-4111-8111-111111111111'
  ),
  (
    'acc11111-0000-4000-8000-000000000003',
    'Tarjeta de Crédito VISA',
    'credit_card',
    -450.20,
    'EUR',
    'CaixaBank',
    'ES76 2100 0418 4502 0005 1332',
    true,
    'Límite 5.000€ - Pago domiciliado el 5 de cada mes',
    NOW() - INTERVAL '80 days',
    NOW(),
    '11111111-1111-4111-8111-111111111111'
  ),
  (
    'acc11111-0000-4000-8000-000000000004',
    'Cartera Inversión',
    'investment',
    18500.00,
    'EUR',
    'DEGIRO',
    'NL-DEG-2024-001122',
    true,
    'Cartera de ETFs y acciones a largo plazo',
    NOW() - INTERVAL '60 days',
    NOW() - INTERVAL '3 days',
    '11111111-1111-4111-8111-111111111111'
  );


-- =============================================================
-- CUENTAS — Usuario jgarcia
-- =============================================================

INSERT INTO public.accounts (id, name, type, balance, currency, bank_name, account_number, is_active, notes, created_at, updated_at, user_id)
VALUES
  (
    'acc22222-0000-4000-8000-000000000001',
    'Cuenta Nómina BBVA',
    'checking',
    1800.50,
    'EUR',
    'BBVA',
    'ES91 0182 1111 2222 3333 4444',
    true,
    'Cuenta principal',
    NOW() - INTERVAL '180 days',
    NOW() - INTERVAL '1 day',
    '22222222-2222-4222-8222-222222222222'
  ),
  (
    'acc22222-0000-4000-8000-000000000002',
    'Cuenta Ahorro Vacaciones',
    'savings',
    3500.00,
    'EUR',
    'BBVA',
    'ES91 0182 1111 5555 6666 7777',
    true,
    'Objetivo: viaje Japón 2026',
    NOW() - INTERVAL '180 days',
    NOW() - INTERVAL '5 days',
    '22222222-2222-4222-8222-222222222222'
  );


-- =============================================================
-- TRANSACCIONES — Usuario Test1
-- Últimos 3 meses con movimientos realistas
-- =============================================================

INSERT INTO public.transactions (id, account_id, date, amount, description, type, transfer_account_id, notes, tags, source, created_at, updated_at, category_id)
VALUES

  -- ── ENERO 2026 ──────────────────────────────────────────────

  -- Nómina enero
  ('e1111001-0000-4000-8000-000000000001', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-02', 2850.00, 'Transferencia nómina enero 2026', 'income', NULL,
   'Nómina mensual neta', ARRAY['nómina','enero'], 'manual',
   '2026-01-02 09:00:00+01', '2026-01-02 09:00:00+01', 'c4000001-0000-4000-8000-000000000001'),

  -- Alquiler enero
  ('e1111001-0000-4000-8000-000000000002', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-05', -950.00, 'Alquiler piso enero', 'expense', NULL,
   NULL, ARRAY['alquiler','fijo'], 'manual',
   '2026-01-05 08:30:00+01', '2026-01-05 08:30:00+01', 'c4000002-0000-4000-8000-000000000001'),

  -- Supermercado
  ('e1111001-0000-4000-8000-000000000003', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-07', -87.45, 'Mercadona compra semanal', 'expense', NULL,
   NULL, ARRAY['supermercado'], 'manual',
   '2026-01-07 19:10:00+01', '2026-01-07 19:10:00+01', 'c4000002-0000-4000-8000-000000000002'),

  ('e1111001-0000-4000-8000-000000000004', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-14', -65.20, 'Carrefour compra semana 2', 'expense', NULL,
   NULL, ARRAY['supermercado'], 'manual',
   '2026-01-14 18:45:00+01', '2026-01-14 18:45:00+01', 'c4000002-0000-4000-8000-000000000002'),

  -- Restaurante
  ('e1111001-0000-4000-8000-000000000005', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-10', -42.00, 'Restaurante La Tasca - cena amigos', 'expense', NULL,
   NULL, ARRAY['restaurante','social'], 'manual',
   '2026-01-10 21:30:00+01', '2026-01-10 21:30:00+01', 'c4000002-0000-4000-8000-000000000003'),

  -- Transporte
  ('e1111001-0000-4000-8000-000000000006', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-03', -55.00, 'Abono transportes enero', 'expense', NULL,
   NULL, ARRAY['transporte','mensual'], 'manual',
   '2026-01-03 08:00:00+01', '2026-01-03 08:00:00+01', 'c4000002-0000-4000-8000-000000000004'),

  -- Suscripciones
  ('e1111001-0000-4000-8000-000000000007', 'acc11111-0000-4000-8000-000000000003',
   '2026-01-08', -14.99, 'Netflix - suscripción mensual', 'expense', NULL,
   NULL, ARRAY['suscripción','ocio'], 'manual',
   '2026-01-08 00:00:00+01', '2026-01-08 00:00:00+01', 'c4000002-0000-4000-8000-000000000007'),

  ('e1111001-0000-4000-8000-000000000008', 'acc11111-0000-4000-8000-000000000003',
   '2026-01-12', -9.99, 'Spotify Premium', 'expense', NULL,
   NULL, ARRAY['suscripción','música'], 'manual',
   '2026-01-12 00:00:00+01', '2026-01-12 00:00:00+01', 'c4000002-0000-4000-8000-000000000007'),

  -- Gym
  ('e1111001-0000-4000-8000-000000000009', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-06', -39.99, 'Cuota gimnasio enero', 'expense', NULL,
   NULL, ARRAY['salud','deporte'], 'manual',
   '2026-01-06 07:00:00+01', '2026-01-06 07:00:00+01', 'c4000002-0000-4000-8000-000000000005'),

  -- Transferencia a ahorro
  ('e1111001-0000-4000-8000-000000000010', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-31', -300.00, 'Transferencia a cuenta ahorro', 'transfer', 'acc11111-0000-4000-8000-000000000002',
   'Ahorro mensual programado', ARRAY['ahorro','transferencia'], 'manual',
   '2026-01-31 10:00:00+01', '2026-01-31 10:00:00+01', NULL),

  ('e1111001-0000-4000-8000-000000000011', 'acc11111-0000-4000-8000-000000000002',
   '2026-01-31', 300.00, 'Recepción transferencia ahorro enero', 'transfer', 'acc11111-0000-4000-8000-000000000001',
   NULL, ARRAY['ahorro','transferencia'], 'manual',
   '2026-01-31 10:01:00+01', '2026-01-31 10:01:00+01', NULL),

  -- Seguro médico
  ('e1111001-0000-4000-8000-000000000012', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-15', -62.50, 'Seguro médico Adeslas mensual', 'expense', NULL,
   NULL, ARRAY['seguro','salud'], 'manual',
   '2026-01-15 09:00:00+01', '2026-01-15 09:00:00+01', 'c4000002-0000-4000-8000-000000000012'),

  -- Freelance extra
  ('e1111001-0000-4000-8000-000000000013', 'acc11111-0000-4000-8000-000000000001',
   '2026-01-20', 450.00, 'Proyecto web freelance - cliente ABC', 'income', NULL,
   'Diseño web responsive', ARRAY['freelance','extra'], 'manual',
   '2026-01-20 15:00:00+01', '2026-01-20 15:00:00+01', 'c4000001-0000-4000-8000-000000000002'),

  -- ── FEBRERO 2026 ─────────────────────────────────────────────

  -- Nómina febrero
  ('e1111002-0000-4000-8000-000000000001', 'acc11111-0000-4000-8000-000000000001',
   '2026-02-02', 2850.00, 'Transferencia nómina febrero 2026', 'income', NULL,
   'Nómina mensual neta', ARRAY['nómina','febrero'], 'manual',
   '2026-02-02 09:00:00+01', '2026-02-02 09:00:00+01', 'c4000001-0000-4000-8000-000000000001'),

  -- Alquiler febrero
  ('e1111002-0000-4000-8000-000000000002', 'acc11111-0000-4000-8000-000000000001',
   '2026-02-05', -950.00, 'Alquiler piso febrero', 'expense', NULL,
   NULL, ARRAY['alquiler','fijo'], 'manual',
   '2026-02-05 08:30:00+01', '2026-02-05 08:30:00+01', 'c4000002-0000-4000-8000-000000000001'),

  -- Supermercado feb
  ('e1111002-0000-4000-8000-000000000003', 'acc11111-0000-4000-8000-000000000001',
   '2026-02-06', -93.10, 'Mercadona compra semanal', 'expense', NULL,
   NULL, ARRAY['supermercado'], 'manual',
   '2026-02-06 19:00:00+01', '2026-02-06 19:00:00+01', 'c4000002-0000-4000-8000-000000000002'),

  ('e1111002-0000-4000-8000-000000000004', 'acc11111-0000-4000-8000-000000000001',
   '2026-02-13', -71.55, 'Lidl + Mercadona semana 2', 'expense', NULL,
   NULL, ARRAY['supermercado'], 'manual',
   '2026-02-13 18:00:00+01', '2026-02-13 18:00:00+01', 'c4000002-0000-4000-8000-000000000002'),

  -- San Valentín restaurante
  ('e1111002-0000-4000-8000-000000000005', 'acc11111-0000-4000-8000-000000000003',
   '2026-02-14', -89.00, 'Restaurante El Portal - cena San Valentín', 'expense', NULL,
   '2 personas, menú degustación', ARRAY['restaurante','especial'], 'manual',
   '2026-02-14 22:00:00+01', '2026-02-14 22:00:00+01', 'c4000002-0000-4000-8000-000000000003'),

  -- Viaje fin de semana
  ('e1111002-0000-4000-8000-000000000006', 'acc11111-0000-4000-8000-000000000003',
   '2026-02-20', -220.00, 'Hotel Barcelona fin de semana', 'expense', NULL,
   'Viaje escapada febrero', ARRAY['viaje','hotel'], 'manual',
   '2026-02-20 14:00:00+01', '2026-02-20 14:00:00+01', 'c4000002-0000-4000-8000-000000000011'),

  -- Ropa
  ('e1111002-0000-4000-8000-000000000007', 'acc11111-0000-4000-8000-000000000003',
   '2026-02-22', -145.99, 'Zara rebajas - ropa temporada', 'expense', NULL,
   NULL, ARRAY['ropa','rebajas'], 'manual',
   '2026-02-22 12:00:00+01', '2026-02-22 12:00:00+01', 'c4000002-0000-4000-8000-000000000008'),

  -- Suscripciones feb
  ('e1111002-0000-4000-8000-000000000008', 'acc11111-0000-4000-8000-000000000003',
   '2026-02-08', -14.99, 'Netflix febrero', 'expense', NULL,
   NULL, ARRAY['suscripción','ocio'], 'manual',
   '2026-02-08 00:00:00+01', '2026-02-08 00:00:00+01', 'c4000002-0000-4000-8000-000000000007'),

  ('e1111002-0000-4000-8000-000000000009', 'acc11111-0000-4000-8000-000000000003',
   '2026-02-12', -9.99, 'Spotify febrero', 'expense', NULL,
   NULL, ARRAY['suscripción'], 'manual',
   '2026-02-12 00:00:00+01', '2026-02-12 00:00:00+01', 'c4000002-0000-4000-8000-000000000007'),

  -- Gym feb
  ('e1111002-0000-4000-8000-000000000010', 'acc11111-0000-4000-8000-000000000001',
   '2026-02-06', -39.99, 'Cuota gimnasio febrero', 'expense', NULL,
   NULL, ARRAY['salud','deporte'], 'manual',
   '2026-02-06 07:00:00+01', '2026-02-06 07:00:00+01', 'c4000002-0000-4000-8000-000000000005'),

  -- Transferencia a ahorro
  ('e1111002-0000-4000-8000-000000000011', 'acc11111-0000-4000-8000-000000000001',
   '2026-02-28', -300.00, 'Transferencia a cuenta ahorro', 'transfer', 'acc11111-0000-4000-8000-000000000002',
   NULL, ARRAY['ahorro'], 'manual',
   '2026-02-28 10:00:00+01', '2026-02-28 10:00:00+01', NULL),

  ('e1111002-0000-4000-8000-000000000012', 'acc11111-0000-4000-8000-000000000002',
   '2026-02-28', 300.00, 'Recepción transferencia ahorro febrero', 'transfer', 'acc11111-0000-4000-8000-000000000001',
   NULL, ARRAY['ahorro'], 'manual',
   '2026-02-28 10:01:00+01', '2026-02-28 10:01:00+01', NULL),

  -- Dividendos ETF
  ('e1111002-0000-4000-8000-000000000013', 'acc11111-0000-4000-8000-000000000004',
   '2026-02-17', 38.50, 'Dividendos VWCE Q4 2025', 'income', NULL,
   'Distribución trimestral ETF Vanguard', ARRAY['dividendo','inversión'], 'manual',
   '2026-02-17 12:00:00+01', '2026-02-17 12:00:00+01', 'c4000001-0000-4000-8000-000000000003'),

  -- ── MARZO 2026 ──────────────────────────────────────────────

  -- Nómina marzo
  ('e1111003-0000-4000-8000-000000000001', 'acc11111-0000-4000-8000-000000000001',
   '2026-03-03', 2850.00, 'Transferencia nómina marzo 2026', 'income', NULL,
   'Nómina mensual neta', ARRAY['nómina','marzo'], 'manual',
   '2026-03-03 09:00:00+01', '2026-03-03 09:00:00+01', 'c4000001-0000-4000-8000-000000000001'),

  -- Alquiler marzo
  ('e1111003-0000-4000-8000-000000000002', 'acc11111-0000-4000-8000-000000000001',
   '2026-03-05', -950.00, 'Alquiler piso marzo', 'expense', NULL,
   NULL, ARRAY['alquiler','fijo'], 'manual',
   '2026-03-05 08:30:00+01', '2026-03-05 08:30:00+01', 'c4000002-0000-4000-8000-000000000001'),

  -- Supermercado mar
  ('e1111003-0000-4000-8000-000000000003', 'acc11111-0000-4000-8000-000000000001',
   '2026-03-05', -78.30, 'Mercadona', 'expense', NULL,
   NULL, ARRAY['supermercado'], 'manual',
   '2026-03-05 19:00:00+01', '2026-03-05 19:00:00+01', 'c4000002-0000-4000-8000-000000000002'),

  -- Transporte marzo
  ('e1111003-0000-4000-8000-000000000004', 'acc11111-0000-4000-8000-000000000001',
   '2026-03-03', -55.00, 'Abono transportes marzo', 'expense', NULL,
   NULL, ARRAY['transporte','mensual'], 'manual',
   '2026-03-03 08:00:00+01', '2026-03-03 08:00:00+01', 'c4000002-0000-4000-8000-000000000004'),

  -- Suscripciones mar
  ('e1111003-0000-4000-8000-000000000005', 'acc11111-0000-4000-8000-000000000003',
   '2026-03-08', -14.99, 'Netflix marzo', 'expense', NULL,
   NULL, ARRAY['suscripción'], 'manual',
   '2026-03-08 00:00:00+01', '2026-03-08 00:00:00+01', 'c4000002-0000-4000-8000-000000000007'),

  ('e1111003-0000-4000-8000-000000000006', 'acc11111-0000-4000-8000-000000000003',
   '2026-03-09', -13.99, 'Adobe Creative Cloud mensual', 'expense', NULL,
   NULL, ARRAY['suscripción','software'], 'manual',
   '2026-03-09 00:00:00+01', '2026-03-09 00:00:00+01', 'c4000002-0000-4000-8000-000000000007'),

  -- Suministros hogar
  ('e1111003-0000-4000-8000-000000000007', 'acc11111-0000-4000-8000-000000000001',
   '2026-03-07', -98.40, 'Endesa - factura luz febrero', 'expense', NULL,
   NULL, ARRAY['suministros','fijo'], 'manual',
   '2026-03-07 10:00:00+01', '2026-03-07 10:00:00+01', 'c4000002-0000-4000-8000-000000000010'),

  -- Gym marzo
  ('e1111003-0000-4000-8000-000000000008', 'acc11111-0000-4000-8000-000000000001',
   '2026-03-06', -39.99, 'Cuota gimnasio marzo', 'expense', NULL,
   NULL, ARRAY['salud'], 'manual',
   '2026-03-06 07:00:00+01', '2026-03-06 07:00:00+01', 'c4000002-0000-4000-8000-000000000005'),

  -- Ocio
  ('e1111003-0000-4000-8000-000000000009', 'acc11111-0000-4000-8000-000000000001',
   '2026-03-08', -30.00, 'Entradas cine + palomitas x2', 'expense', NULL,
   NULL, ARRAY['ocio','cine'], 'manual',
   '2026-03-08 20:00:00+01', '2026-03-08 20:00:00+01', 'c4000002-0000-4000-8000-000000000006');


-- =============================================================
-- INVERSIONES — Usuario Test1
-- =============================================================

INSERT INTO public.investments (id, user_id, symbol, company_name, shares, average_price, purchase_date, sale_price, sale_date, status, notes, created_at, updated_at)
VALUES
  (
    '11b11111-0000-4000-8000-000000000001',
    '11111111-1111-4111-8111-111111111111',
    'VWCE',
    'Vanguard FTSE All-World UCITS ETF',
    45.0000,
    98.50,
    '2024-01-15',
    NULL, NULL,
    'active',
    'Posición núcleo cartera. Acumulación automática mensual.',
    '2024-01-15 10:00:00+01', NOW() - INTERVAL '3 days'
  ),
  (
    '11b11111-0000-4000-8000-000000000002',
    '11111111-1111-4111-8111-111111111111',
    'IEMG',
    'iShares Core MSCI Emerging Markets ETF',
    30.0000,
    52.30,
    '2024-03-10',
    NULL, NULL,
    'active',
    'Exposición mercados emergentes 15% cartera',
    '2024-03-10 11:00:00+01', NOW() - INTERVAL '3 days'
  ),
  (
    '11b11111-0000-4000-8000-000000000003',
    '11111111-1111-4111-8111-111111111111',
    'AAPL',
    'Apple Inc.',
    10.0000,
    175.20,
    '2023-06-01',
    NULL, NULL,
    'active',
    'Acciones Apple compradas tras corrección 2023',
    '2023-06-01 15:30:00+01', NOW() - INTERVAL '7 days'
  ),
  (
    '11b11111-0000-4000-8000-000000000004',
    '11111111-1111-4111-8111-111111111111',
    'MSFT',
    'Microsoft Corporation',
    5.0000,
    310.00,
    '2023-09-15',
    NULL, NULL,
    'watchlist',
    'Ampliar posición si baja de 380$',
    '2023-09-15 14:00:00+01', NOW() - INTERVAL '10 days'
  ),
  (
    '11b11111-0000-4000-8000-000000000005',
    '11111111-1111-4111-8111-111111111111',
    'META',
    'Meta Platforms Inc.',
    8.0000,
    245.00,
    '2023-01-20',
    520.00,
    '2024-11-30',
    'sold',
    'Vendido con +112% de rentabilidad. Plusvalía reinvertida en VWCE.',
    '2023-01-20 10:00:00+01', '2024-11-30 16:00:00+01'
  );


-- =============================================================
-- PRESUPUESTOS — Usuario Test1
-- =============================================================

INSERT INTO public.budgets (id, user_id, month, year, total_budget, name, created_at, updated_at)
VALUES
  (
    'b0d11111-0000-4000-8000-000000000001',
    '11111111-1111-4111-8111-111111111111',
    1, 2026,
    2200.00,
    'Enero 2026 - Presupuesto estándar',
    '2025-12-28 10:00:00+01', '2025-12-28 10:00:00+01'
  ),
  (
    'b0d11111-0000-4000-8000-000000000002',
    '11111111-1111-4111-8111-111111111111',
    2, 2026,
    2400.00,
    'Febrero 2026 - San Valentín + escapada',
    '2026-01-28 10:00:00+01', '2026-01-28 10:00:00+01'
  ),
  (
    'b0d11111-0000-4000-8000-000000000003',
    '11111111-1111-4111-8111-111111111111',
    3, 2026,
    2100.00,
    'Marzo 2026 - Vuelta a la normalidad',
    '2026-02-25 10:00:00+01', '2026-02-25 10:00:00+01'
  );


-- =============================================================
-- PARTIDAS DE PRESUPUESTO
-- =============================================================

-- Enero 2026
INSERT INTO public.budget_items (id, budget_id, category_id, allocated_amount, notes, created_at, updated_at)
VALUES
  ('b1111001-0000-4000-8000-000000000001', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000001',  950.00, 'Alquiler fijo', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000002', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000002',  300.00, 'Compra semanal estimada', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000003', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000003',   80.00, 'Salidas a comer', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000004', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000004',   60.00, 'Abono + extras', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000005', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000005',  110.00, 'Gym + seguro médico', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000006', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000007',   50.00, 'Netflix + Spotify + otros', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000007', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000006',  100.00, 'Ocio general', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000008', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000012',   65.00, 'Seguros varios', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000009', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000010',  100.00, 'Luz, agua, internet', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000010', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000008',  100.00, 'Ropa ocasional', NOW(), NOW()),
  ('b1111001-0000-4000-8000-000000000011', 'b0d11111-0000-4000-8000-000000000001', 'c4000002-0000-4000-8000-000000000011',  285.00, 'Viajes y escapadas', NOW(), NOW());

-- Febrero 2026
INSERT INTO public.budget_items (id, budget_id, category_id, allocated_amount, notes, created_at, updated_at)
VALUES
  ('b1111002-0000-4000-8000-000000000001', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000001',  950.00, 'Alquiler fijo', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000002', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000002',  300.00, 'Supermercado', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000003', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000003',  150.00, 'San Valentín + salidas', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000004', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000004',   60.00, 'Transporte', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000005', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000005',  110.00, 'Salud', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000006', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000007',   50.00, 'Suscripciones', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000007', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000008',  200.00, 'Ropa rebajas', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000008', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000011',  280.00, 'Escapada Barcelona', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000009', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000010',  100.00, 'Suministros', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000010', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000012',   65.00, 'Seguros', NOW(), NOW()),
  ('b1111002-0000-4000-8000-000000000011', 'b0d11111-0000-4000-8000-000000000002', 'c4000002-0000-4000-8000-000000000006',  135.00, 'Ocio general', NOW(), NOW());

-- Marzo 2026
INSERT INTO public.budget_items (id, budget_id, category_id, allocated_amount, notes, created_at, updated_at)
VALUES
  ('b1111003-0000-4000-8000-000000000001', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000001',  950.00, 'Alquiler fijo', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000002', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000002',  280.00, 'Supermercado', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000003', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000003',   80.00, 'Restaurantes', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000004', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000004',   60.00, 'Transporte', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000005', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000005',  110.00, 'Salud', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000006', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000007',   65.00, 'Suscripciones', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000007', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000010',  120.00, 'Suministros + luz', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000008', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000006',   80.00, 'Ocio', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000009', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000012',   65.00, 'Seguros', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000010', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000011',  100.00, 'Viajes', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000011', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000008',   90.00, 'Ropa', NOW(), NOW()),
  ('b1111003-0000-4000-8000-000000000012', 'b0d11111-0000-4000-8000-000000000003', 'c4000002-0000-4000-8000-000000000009',  100.00, 'Curso online', NOW(), NOW());


-- =============================================================
-- VERIFICACIÓN FINAL
-- =============================================================

DO $$
DECLARE
  v_users       INT;
  v_accounts    INT;
  v_categories  INT;
  v_transactions INT;
  v_investments INT;
  v_budgets     INT;
  v_items       INT;
BEGIN
  SELECT COUNT(*) INTO v_users       FROM public.users;
  SELECT COUNT(*) INTO v_accounts    FROM public.accounts;
  SELECT COUNT(*) INTO v_categories  FROM public.categories;
  SELECT COUNT(*) INTO v_transactions FROM public.transactions;
  SELECT COUNT(*) INTO v_investments FROM public.investments;
  SELECT COUNT(*) INTO v_budgets     FROM public.budgets;
  SELECT COUNT(*) INTO v_items       FROM public.budget_items;

  RAISE NOTICE '==========================================';
  RAISE NOTICE 'SEED DATA CARGADO CORRECTAMENTE';
  RAISE NOTICE '==========================================';
  RAISE NOTICE 'Usuarios:       %', v_users;
  RAISE NOTICE 'Cuentas:        %', v_accounts;
  RAISE NOTICE 'Categorías:     %', v_categories;
  RAISE NOTICE 'Transacciones:  %', v_transactions;
  RAISE NOTICE 'Inversiones:    %', v_investments;
  RAISE NOTICE 'Presupuestos:   %', v_budgets;
  RAISE NOTICE 'Partidas ppto:  %', v_items;
  RAISE NOTICE '------------------------------------------';
  RAISE NOTICE 'Login 1 (admin): Test1 / Test@1234';
  RAISE NOTICE 'Login 2 (user):  jgarcia / Test@1234';
  RAISE NOTICE '==========================================';
END $$;