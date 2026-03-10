#!/usr/bin/env bash
# =============================================================
# Script de verificación de inicialización de Base de Datos
# =============================================================

set -e

echo "🔍 Verificando inicialización de PostgreSQL..."
echo ""

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a que PostgreSQL esté disponible..."
until docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; do
  sleep 1
done
echo "✅ PostgreSQL está listo"
echo ""

# Verificar extensiones
echo "📦 Extensiones instaladas:"
docker-compose exec -T db psql -U postgres -d app_finance -c "\dx" -t
echo ""

# Verificar tipos personalizados
echo "🏷️  Tipos personalizados (ENUM):"
docker-compose exec -T db psql -U postgres -d app_finance -c "SELECT typname FROM pg_type WHERE typtype = 'e';" -t
echo ""

# Verificar funciones
echo "⚙️  Funciones personalizadas:"
docker-compose exec -T db psql -U postgres -d app_finance -c "SELECT proname FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'public' AND p.prokind = 'f';" -t
echo ""

# Listar todas las tablas
echo "📋 Tablas creadas:"
docker-compose exec -T db psql -U postgres -d app_finance -c "\dt" -x
echo ""

# Contar registros en cada tabla
echo "📊 Número de registros por tabla:"
docker-compose exec -T db psql -U postgres -d app_finance <<EOF
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = schemaname AND table_name = tablename) as exists
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
EOF

echo ""
echo "✅ Verificación completada"
echo ""
echo "💡 Para acceder a PostgreSQL interactivamente:"
echo "   docker-compose exec db psql -U postgres -d app_finance"
