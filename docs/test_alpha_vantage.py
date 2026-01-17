#!/usr/bin/env python3
"""
Script de diagnóstico para Alpha Vantage API
Ejecutar desde: backend/

python test_alpha_vantage.py
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
BASE_URL = "https://www.alphavantage.co/query"

print("=" * 70)
print("🔍 DIAGNÓSTICO ALPHA VANTAGE API")
print("=" * 70)

# 1. Verificar API Key
print(f"\n1️⃣  API Key configurada: {API_KEY[:8]}..." if len(API_KEY) > 8 else API_KEY)
if API_KEY == "demo":
    print("   ⚠️  WARNING: Usando API key 'demo' (muy limitada)")
    print("   ⚠️  Obtén tu API key gratuita en: https://www.alphavantage.co/support/#api-key")
elif API_KEY == "IP8B1NDDPRG8F5T3":
    print("   ⚠️  WARNING: Usando API key por defecto del código")
    print("   ⚠️  Esta key puede estar agotada. Obtén la tuya propia.")
else:
    print("   ✅ API key personalizada configurada")

print(f"\n2️⃣  Base URL: {BASE_URL}")

async def test_search(query: str):
    """Probar búsqueda de símbolos"""
    print(f"\n3️⃣  Probando búsqueda: '{query}'")
    print("   " + "-" * 60)
    
    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": query,
        "apikey": API_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(BASE_URL, params=params)
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verificar errores específicos de Alpha Vantage
                if "Error Message" in data:
                    print(f"   ❌ Alpha Vantage Error: {data['Error Message']}")
                    return False
                
                if "Note" in data:
                    print(f"   ⚠️  Rate Limit Message: {data['Note']}")
                    print(f"   ⚠️  Probablemente alcanzaste el límite de 5 req/min o 500/día")
                    return False
                
                if "bestMatches" in data:
                    matches = data["bestMatches"]
                    print(f"   ✅ Encontrados {len(matches)} resultados")
                    
                    for i, match in enumerate(matches[:3], 1):
                        symbol = match.get("1. symbol", "N/A")
                        name = match.get("2. name", "N/A")
                        print(f"      {i}. {symbol} - {name}")
                    
                    if len(matches) > 3:
                        print(f"      ... y {len(matches) - 3} más")
                    
                    return True
                else:
                    print(f"   ❌ Respuesta inesperada (sin 'bestMatches')")
                    print(f"   📄 Response: {data}")
                    return False
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                print(f"   📄 Response: {response.text[:200]}")
                return False
                
    except httpx.TimeoutException:
        print(f"   ❌ Timeout - API no respondió en 10 segundos")
        return False
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        return False

async def test_quote(symbol: str):
    """Probar obtención de cotización"""
    print(f"\n4️⃣  Probando cotización: '{symbol}'")
    print("   " + "-" * 60)
    
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": API_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(BASE_URL, params=params)
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if "Error Message" in data:
                    print(f"   ❌ Alpha Vantage Error: {data['Error Message']}")
                    return False
                
                if "Note" in data:
                    print(f"   ⚠️  Rate Limit: {data['Note']}")
                    return False
                
                quote = data.get("Global Quote", {})
                
                if quote and "05. price" in quote:
                    price = quote.get("05. price")
                    change = quote.get("09. change")
                    change_pct = quote.get("10. change percent", "").replace("%", "")
                    
                    print(f"   ✅ Cotización obtenida:")
                    print(f"      Símbolo: {quote.get('01. symbol')}")
                    print(f"      Precio: ${price}")
                    print(f"      Cambio: {change} ({change_pct}%)")
                    return True
                else:
                    print(f"   ❌ Sin datos de cotización en respuesta")
                    print(f"   📄 Response: {data}")
                    return False
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                return False
                
    except httpx.TimeoutException:
        print(f"   ❌ Timeout")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def main():
    """Ejecutar todas las pruebas"""
    
    # Test 1: Búsqueda de CMG
    search_ok = await test_search("CMG")
    
    # Esperar 12 segundos entre llamadas (rate limit: 5 req/min = 1 req cada 12s)
    if search_ok:
        print("\n   ⏳ Esperando 13 segundos para evitar rate limit...")
        await asyncio.sleep(13)
    
    # Test 2: Cotización de AAPL
    quote_ok = await test_quote("AAPL")
    
    # Resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN DEL DIAGNÓSTICO")
    print("=" * 70)
    
    if search_ok and quote_ok:
        print("✅ Alpha Vantage API funcionando correctamente")
        print("✅ Tu aplicación debería recibir datos reales (no mock)")
    elif not search_ok and not quote_ok:
        print("❌ Alpha Vantage API NO está funcionando")
        print("❌ Posibles causas:")
        print("   1. API key inválida o expirada")
        print("   2. Rate limit excedido (5 req/min, 500/día)")
        print("   3. Problemas de conectividad")
        print("\n💡 SOLUCIÓN:")
        print("   - Si usas 'demo' o key compartida: Obtén tu propia key")
        print("   - Si excediste límite: Espera o actualiza a plan premium")
        print("   - La app usará MOCK DATA automáticamente")
    else:
        print("⚠️  Alpha Vantage API funcionando parcialmente")
        print("⚠️  Algunas funciones usan mock data")
    
    print("\n🔗 Obtener API key gratuita:")
    print("   https://www.alphavantage.co/support/#api-key")
    print("\n📝 Configurar en .env:")
    print("   ALPHA_VANTAGE_API_KEY=tu_api_key_aqui")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
