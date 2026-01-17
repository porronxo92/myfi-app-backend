"""
Test script para el endpoint de logos de stocks
Ejecutar después de configurar BRANDFETCH_CLIENT_ID en .env
"""

import asyncio
import httpx
from app.services.stock_api_service import stock_api_service


async def test_logo_service():
    """Test directo del servicio de logos"""
    
    print("=" * 60)
    print("TEST: Stock Logo Service - Brandfetch Integration")
    print("=" * 60)
    
    test_tickers = [
        "AAPL",   # Apple
        "MSFT",   # Microsoft
        "GOOGL",  # Google
        "TSLA",   # Tesla
        "ONON",   # On Running
        "NVDA",   # NVIDIA
        "CMG"     # Chipotle (ejemplo de la documentación)
    ]
    
    print("\n🧪 Probando obtención de logos para diferentes tickers...\n")
    
    for ticker in test_tickers:
        try:
            print(f"📍 Testing {ticker}...")
            result = await stock_api_service.get_stock_logo(ticker)
            
            if result.get("available"):
                print(f"   ✅ Logo encontrado")
                print(f"   🔗 URL: {result.get('logo_url')}")
                print(f"   📄 Tipo: {result.get('content_type', 'N/A')}")
            else:
                print(f"   ⚠️  Logo no disponible")
                print(f"   ℹ️  Mensaje: {result.get('message', 'N/A')}")
            
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            print()
    
    print("=" * 60)
    print("✓ Test completado")
    print("=" * 60)


async def test_with_httpx():
    """Test del endpoint completo (requiere servidor corriendo)"""
    
    print("\n" + "=" * 60)
    print("TEST: Endpoint HTTP (requiere servidor corriendo)")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # NOTA: Necesitarás un token JWT válido para esto
    # Puedes obtenerlo haciendo login primero
    
    print("\n⚠️  Para probar el endpoint HTTP completo:")
    print("   1. Asegúrate de que el servidor esté corriendo")
    print("   2. Obtén un token JWT válido (login)")
    print("   3. Ejecuta:")
    print(f"\n   curl -X GET '{base_url}/api/investments/logo?q=AAPL' \\")
    print(f"        -H 'Authorization: Bearer YOUR_JWT_TOKEN'\n")
    
    print("=" * 60)


if __name__ == "__main__":
    print("\n🚀 Iniciando tests...\n")
    
    # Test directo del servicio
    asyncio.run(test_logo_service())
    
    # Instrucciones para test HTTP
    asyncio.run(test_with_httpx())
