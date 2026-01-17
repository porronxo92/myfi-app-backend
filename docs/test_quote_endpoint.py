"""
Script de Prueba - Endpoint /api/investments/quote
===================================================

Prueba el nuevo endpoint de cotizaciones en tiempo real

Uso:
    python test_quote_endpoint.py
"""

import httpx
import asyncio
from app.utils.alpha_vantage import alpha_vantage_service

async def test_quote_endpoint():
    """Prueba directa del servicio Alpha Vantage"""
    
    print("=" * 60)
    print("TEST: Alpha Vantage Quote Service")
    print("=" * 60)
    
    test_symbols = ["ONON", "AAPL", "AMD", "TSLA", "INVALID_TICKER"]
    
    for symbol in test_symbols:
        print(f"\n{'─' * 60}")
        print(f"📊 Testing ticker: {symbol}")
        print(f"{'─' * 60}")
        
        try:
            quote = await alpha_vantage_service.get_stock_quote(symbol)
            
            if quote:
                print(f"✅ Quote received for {symbol}:")
                print(f"   Symbol: {quote.symbol}")
                print(f"   Price: ${quote.price:.2f}")
                print(f"   Change: ${quote.change:+.2f} ({quote.change_percent:+.2f}%)")
                print(f"   High: ${quote.high:.2f}")
                print(f"   Low: ${quote.low:.2f}")
                print(f"   Open: ${quote.open:.2f}")
                print(f"   Previous Close: ${quote.previous_close:.2f}")
                print(f"   Volume: {quote.volume:,}")
                print(f"   Currency: {quote.currency}")
                print(f"   Timestamp: {quote.timestamp}")
            else:
                print(f"❌ No quote received for {symbol}")
                
        except Exception as e:
            print(f"❌ Error testing {symbol}: {e}")
        
        # Esperar 13 segundos entre requests para respetar rate limit (5 req/min)
        if symbol != test_symbols[-1]:
            print(f"\n⏳ Waiting 13 seconds (rate limit: 5 req/min)...")
            await asyncio.sleep(13)
    
    print(f"\n{'=' * 60}")
    print("✅ Test completed")
    print(f"{'=' * 60}")


async def test_http_endpoint():
    """
    Prueba el endpoint HTTP directamente
    
    Nota: Requiere que el servidor esté corriendo y tener un token JWT válido
    """
    print("\n" + "=" * 60)
    print("TEST: HTTP Endpoint /api/investments/quote")
    print("=" * 60)
    print("\n⚠️  Este test requiere:")
    print("   1. Servidor backend corriendo (uvicorn)")
    print("   2. Token JWT válido")
    print("\nPara probar manualmente:")
    print("   1. Inicia sesión en el frontend")
    print("   2. Copia el token del localStorage")
    print("   3. Usa curl o Postman:")
    print("\n   curl -H 'Authorization: Bearer YOUR_TOKEN' \\")
    print("        'http://localhost:8000/api/investments/quote?q=ONON'")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n🚀 Starting Alpha Vantage Quote Endpoint Tests\n")
    
    # Test 1: Servicio directo
    asyncio.run(test_quote_endpoint())
    
    # Test 2: Instrucciones para endpoint HTTP
    asyncio.run(test_http_endpoint())
