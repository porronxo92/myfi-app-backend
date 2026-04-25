#!/usr/bin/env python
"""
Test script para verificar integración de Finnhub + Alpha Vantage
"""

import asyncio
import sys
import os

# Agregar el directorio del app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.stock_api_service import stock_api_service


async def test_search():
    """Probar búsqueda de acciones"""
    print("\n" + "="*80)
    print("TEST: Búsqueda de Acciones")
    print("="*80)
    
    test_queries = ["AAPL", "Tesla", "Microsoft"]
    
    for query in test_queries:
        print(f"\n📍 Buscando: {query}")
        try:
            results = await stock_api_service.search_stocks(query)
            if results:
                for result in results[:3]:  # Mostrar primeros 3
                    print(f"  ✓ {result.symbol}: {result.name}")
            else:
                print(f"  ✗ Sin resultados para: {query}")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")


async def test_quote():
    """Probar obtención de cotizaciones"""
    print("\n" + "="*80)
    print("TEST: Obtención de Cotizaciones")
    print("="*80)
    
    test_symbols = ["AAPL", "TSLA", "MSFT", "CMG"]
    
    for symbol in test_symbols:
        print(f"\n📍 Cotización: {symbol}")
        try:
            quote = await stock_api_service.get_stock_quote(symbol)
            if quote:
                print(f"  ✓ Precio: ${quote.price:.2f}")
                print(f"  ✓ Cambio: {quote.change_percent:+.2f}%")
                print(f"  ✓ Volumen: {quote.volume:,}")
            else:
                print(f"  ✗ No se pudo obtener cotización para: {symbol}")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")


async def test_batch_quotes():
    """Probar obtención de múltiples cotizaciones"""
    print("\n" + "="*80)
    print("TEST: Múltiples Cotizaciones")
    print("="*80)
    
    symbols = ["AAPL", "MSFT", "GOOGL"]
    print(f"\n📍 Obteniendo cotizaciones para: {', '.join(symbols)}")
    
    try:
        quotes = await stock_api_service.get_multiple_quotes(symbols)
        for symbol, quote in quotes.items():
            if quote:
                print(f"  ✓ {symbol}: ${quote.price:.2f} ({quote.change_percent:+.2f}%)")
            else:
                print(f"  ✗ {symbol}: No disponible")
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")


def test_api_status():
    """Probar estado de APIs"""
    print("\n" + "="*80)
    print("TEST: Estado de APIs")
    print("="*80)
    
    status = stock_api_service.get_api_status()
    
    print("\n📌 Finnhub:")
    print(f"  ✓ Configurada: {status['finnhub']['configured']}")
    print(f"  ✓ Disponible: {status['finnhub']['available']}")
    print(f"  ✓ Llamadas en último minuto: {status['finnhub']['calls_last_minute']}/{status['finnhub']['limit_per_minute']}")
    print(f"  ✓ Llamadas restantes: {status['finnhub']['remaining']}")
    
    print("\n📌 Alpha Vantage:")
    print(f"  ✓ Configurada: {status['alpha_vantage']['configured']}")
    print(f"  ✓ Disponible: {status['alpha_vantage']['available']}")
    print(f"  ✓ Llamadas en último día: {status['alpha_vantage']['calls_last_day']}/{status['alpha_vantage']['limit_per_day']}")
    print(f"  ✓ Llamadas restantes: {status['alpha_vantage']['remaining']}")


async def main():
    """Ejecutar todos los tests"""
    print("\n" + "🧪 INICIANDO TESTS DE INTEGRACIÓN STOCK API 🧪".center(80))
    
    # Test de configuración
    test_api_status()
    
    # Tests de funcionalidad
    await test_search()
    await test_quote()
    await test_batch_quotes()
    
    print("\n" + "="*80)
    print("✅ Tests completados")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
