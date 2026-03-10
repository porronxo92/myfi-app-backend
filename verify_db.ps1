# =============================================================
# Script de verificación de inicialización de Base de Datos
# PowerShell version
# =============================================================

Write-Host "🔍 Verificando inicialización de PostgreSQL..." -ForegroundColor Cyan
Write-Host ""

# Esperar a que PostgreSQL esté listo
Write-Host "⏳ Esperando a que PostgreSQL esté disponible..." -ForegroundColor Yellow
$ready = $false
$attempts = 0
while (-not $ready -and $attempts -lt 30) {
    try {
        $result = docker-compose exec -T db pg_isready -U postgres 2>&1
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
        }
    } catch {
        Start-Sleep -Seconds 1
        $attempts++
    }
}

if (-not $ready) {
    Write-Host "❌ PostgreSQL no está disponible después de 30 segundos" -ForegroundColor Red
    exit 1
}

Write-Host "✅ PostgreSQL está listo" -ForegroundColor Green
Write-Host ""

# Verificar extensiones
Write-Host "📦 Extensiones instaladas:" -ForegroundColor Cyan
docker-compose exec -T db psql -U postgres -d app_finance -c "\dx"
Write-Host ""

# Verificar tipos personalizados
Write-Host "🏷️  Tipos personalizados (ENUM):" -ForegroundColor Cyan
docker-compose exec -T db psql -U postgres -d app_finance -c "SELECT typname FROM pg_type WHERE typtype = 'e';"
Write-Host ""

# Verificar funciones
Write-Host "⚙️  Funciones personalizadas:" -ForegroundColor Cyan
docker-compose exec -T db psql -U postgres -d app_finance -c "SELECT proname FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'public' AND p.prokind = 'f';"
Write-Host ""

# Listar todas las tablas
Write-Host "📋 Tablas creadas:" -ForegroundColor Cyan
docker-compose exec -T db psql -U postgres -d app_finance -c "\dt"
Write-Host ""

Write-Host "✅ Verificación completada" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Para acceder a PostgreSQL interactivamente:" -ForegroundColor Yellow
Write-Host "   docker-compose exec db psql -U postgres -d app_finance"
Write-Host ""
Write-Host "💡 Para ver logs de la API:" -ForegroundColor Yellow
Write-Host "   docker-compose logs -f api"
