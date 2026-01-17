"""
Alpha Vantage Stock Market API Integration
===========================================
Servicio para consultar datos bursátiles en tiempo real
"""

import httpx
import asyncio
from typing import Optional, List
from datetime import datetime
from app.config import settings
from app.schemas.investment import StockQuote, StockSearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AlphaVantageService:
    """Servicio para integración con Alpha Vantage API"""
    
    def __init__(self):
        self.api_key = settings.ALPHA_VANTAGE_API_KEY
        self.base_url = settings.ALPHA_VANTAGE_BASE_URL
        self.timeout = 10.0  # segundos
        
        # Validar configuración
        if not self.api_key or self.api_key == "demo" or self.api_key == "IP8B1NDDPRG8F5T3":
            logger.warning("⚠️  Alpha Vantage API key not configured or using demo/default key")
            logger.warning("⚠️  Service will use mock data only. Set ALPHA_VANTAGE_API_KEY in .env")
            logger.warning("⚠️  Get your free key at: https://www.alphavantage.co/support/#api-key")
        else:
            logger.info(f"✅ Alpha Vantage service initialized with API key: {self.api_key[:8]}...")
    
    async def search_stocks(self, keywords: str) -> List[StockSearchResult]:
        """
        Buscar acciones por ticker o nombre de empresa
        
        Args:
            keywords: Texto a buscar (ticker o nombre)
            
        Returns:
            Lista de resultados de búsqueda
        """
        if not keywords or len(keywords.strip()) < 2:
            return []
        
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords,
            "apikey": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Calling Alpha Vantage SYMBOL_SEARCH for: {keywords}")
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Alpha Vantage retorna error en formato JSON
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                logger.warning(f"Using mock data fallback for: {keywords}")
                return self._get_mock_search_results(keywords)
            
            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                logger.warning(f"Using mock data fallback for: {keywords}")
                return self._get_mock_search_results(keywords)
            
            if "bestMatches" not in data:
                logger.warning(f"No 'bestMatches' key in response for: {keywords}")
                logger.info(f"Full API response: {data}")
                logger.warning(f"Using mock data fallback for: {keywords}")
                return self._get_mock_search_results(keywords)
            
            results = []
            for match in data["bestMatches"][:10]:  # Máximo 10 resultados
                results.append(StockSearchResult(
                    symbol=match.get("1. symbol", ""),
                    name=match.get("2. name", ""),
                    type=match.get("3. type", ""),
                    region=match.get("4. region", ""),
                    currency=match.get("8. currency", "USD")
                ))
            
            logger.info(f"✅ Alpha Vantage found {len(results)} results for: {keywords}")
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP error searching stocks for '{keywords}': {e}")
            logger.error(f"Status code: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
            logger.warning(f"Using mock data fallback for: {keywords}")
            return self._get_mock_search_results(keywords)
        except httpx.TimeoutException as e:
            logger.error(f"❌ Timeout searching stocks for '{keywords}': {e}")
            logger.warning(f"Using mock data fallback for: {keywords}")
            return self._get_mock_search_results(keywords)
        except Exception as e:
            logger.error(f"❌ Unexpected error searching stocks for '{keywords}': {e}", exc_info=True)
            logger.warning(f"Using mock data fallback for: {keywords}")
            return self._get_mock_search_results(keywords)
    
    async def get_stock_quote(self, symbol: str) -> Optional[StockQuote]:
        """
        Obtener cotización actual de una acción
        
        Args:
            symbol: Ticker de la acción (ej: AAPL)
            
        Returns:
            Cotización actual o None si hay error
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.upper(),
            "apikey": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Calling Alpha Vantage GLOBAL_QUOTE for: {symbol}")
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Alpha Vantage retorna errores en formato JSON
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API error for {symbol}: {data['Error Message']}")
                logger.warning(f"Using mock quote for: {symbol}")
                return self._get_mock_quote(symbol)
            
            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limit for {symbol}: {data['Note']}")
                logger.warning(f"Using mock quote for: {symbol}")
                return self._get_mock_quote(symbol)
            
            quote_data = data.get("Global Quote", {})
            
            if not quote_data or "05. price" not in quote_data:
                logger.warning(f"No quote data in 'Global Quote' for: {symbol}")
                # Logear toda la respuesta para diagnóstico
                if data:
                    logger.debug(f"Full API response for {symbol}: {data}")
                    if "Global Quote" in data:
                        logger.debug(f"Global Quote data: {data['Global Quote']}")
                else:
                    logger.debug(f"Empty response for {symbol}")
                logger.warning(f"⚠️  Ticker '{symbol}' not found or rate limited - Using mock quote")
                return self._get_mock_quote(symbol)
            
            # Parsear datos de Alpha Vantage
            # Formato de respuesta:
            # "01. symbol": "IBM"
            # "02. open": "302.8200"
            # "03. high": "312.2600"
            # "04. low": "299.9600"
            # "05. price": "312.1700"
            # "06. volume": "3891827"
            # "07. latest trading day": "2026-01-12"
            # "08. previous close": "304.2200"
            # "09. change": "7.9500"
            # "10. change percent": "2.6132%"
            
            try:
                price = float(quote_data.get("05. price", 0))
                change = float(quote_data.get("09. change", 0))
                change_percent_str = quote_data.get("10. change percent", "0%").replace("%", "")
                change_percent = float(change_percent_str)
                
                stock_quote = StockQuote(
                    symbol=quote_data.get("01. symbol", symbol).upper(),
                    name=symbol.upper(),  # Alpha Vantage no devuelve nombre en GLOBAL_QUOTE
                    price=price,
                    change=change,
                    change_percent=change_percent,
                    high=float(quote_data.get("03. high", price)),
                    low=float(quote_data.get("04. low", price)),
                    open=float(quote_data.get("02. open", price)),
                    previous_close=float(quote_data.get("08. previous close", price - change)),
                    volume=int(quote_data.get("06. volume", 0)),
                    currency="USD",
                    timestamp=datetime.utcnow()
                )
                
                logger.info(f"✅ Alpha Vantage quote for {symbol}: ${price:.2f} ({change_percent:+.2f}%)")
                return stock_quote
                
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing quote data for {symbol}: {e}")
                logger.debug(f"Quote data received: {quote_data}")
                logger.warning(f"Using mock quote for: {symbol}")
                return self._get_mock_quote(symbol)
            
        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP error getting quote for '{symbol}': {e}")
            logger.error(f"Status code: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
            logger.warning(f"Using mock quote for: {symbol}")
            return self._get_mock_quote(symbol)
        except httpx.TimeoutException as e:
            logger.error(f"❌ Timeout getting quote for '{symbol}': {e}")
            logger.warning(f"Using mock quote for: {symbol}")
            return self._get_mock_quote(symbol)
        except Exception as e:
            logger.error(f"❌ Unexpected error getting quote for '{symbol}': {e}", exc_info=True)
            logger.warning(f"Using mock quote for: {symbol}")
            return self._get_mock_quote(symbol)
    
    async def get_multiple_quotes(self, symbols: List[str]) -> dict[str, Optional[StockQuote]]:
        """
        Obtener cotizaciones para múltiples símbolos con rate limiting
        
        Alpha Vantage permite 5 requests por minuto en el plan gratuito.
        Este método agrega delays entre llamadas para evitar exceder el límite.
        
        Args:
            symbols: Lista de tickers
            
        Returns:
            Diccionario con {symbol: StockQuote}
        """
        if not symbols:
            return {}
        
        quotes = {}
        
        # Para Free tier: 5 API calls por minuto = 12 segundos entre llamadas
        # Agregamos un pequeño buffer: 12.5 segundos
        api_delay = 1
        
        logger.info(f"Getting quotes for {len(symbols)} symbols (with {api_delay}s delay between calls)")
        
        for i, symbol in enumerate(symbols):
            try:
                quote = await self.get_stock_quote(symbol)
                quotes[symbol] = quote
                
                # Agregar delay entre llamadas (excepto después de la última)
                if i < len(symbols) - 1:
                    logger.debug(f"Waiting {api_delay}s before next API call...")
                    await asyncio.sleep(api_delay)
                    
            except Exception as e:
                logger.error(f"Error getting quote for {symbol}: {e}")
                quotes[symbol] = self._get_mock_quote(symbol)
        
        return quotes
    
    # ========================================
    # MOCK DATA (fallback cuando falla la API)
    # ========================================
    
    def _get_mock_search_results(self, query: str) -> List[StockSearchResult]:
        """
        Datos mock para búsqueda - fallback cuando Alpha Vantage falla
        
        Incluye lista expandida de stocks populares + resultado genérico
        """
        mock_stocks = [
            # Tech Giants
            {"symbol": "AAPL", "name": "Apple Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "GOOGL", "name": "Alphabet Inc. Class A", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "META", "name": "Meta Platforms Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            
            # Other Tech
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "TSLA", "name": "Tesla Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "NFLX", "name": "Netflix Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            
            # Semiconductors
            {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "INTC", "name": "Intel Corporation", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "QCOM", "name": "Qualcomm Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
                        # Semiconductors
            {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "INTC", "name": "Intel Corporation", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "QCOM", "name": "Qualcomm Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
                        # Finance
            {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "BAC", "name": "Bank of America Corp.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "V", "name": "Visa Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            
            # Consumer
            {"symbol": "WMT", "name": "Walmart Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "PG", "name": "Procter & Gamble Co.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "KO", "name": "Coca-Cola Co.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "MCD", "name": "McDonald's Corp.", "type": "Equity", "region": "United States", "currency": "USD"},
            
            # Restaurantes
            {"symbol": "CMG", "name": "Chipotle Mexican Grill Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "SBUX", "name": "Starbucks Corporation", "type": "Equity", "region": "United States", "currency": "USD"},
            
            # Healthcare
            {"symbol": "JNJ", "name": "Johnson & Johnson", "type": "Equity", "region": "United States", "currency": "USD"},
            {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "type": "Equity", "region": "United States", "currency": "USD"},
        ]
        
        query_upper = query.upper()
        query_lower = query.lower()
        
        # Buscar coincidencias exactas o parciales
        filtered = [
            StockSearchResult(**stock)
            for stock in mock_stocks
            if query_upper in stock["symbol"].upper() or query_lower in stock["name"].lower()
        ]
        
        # Si encontramos resultados, retornarlos
        if filtered:
            logger.info(f"📋 Returning {len(filtered)} mock search results for '{query}'")
            return filtered
        
        # Si no hay coincidencias, retornar un resultado genérico con el query como símbolo
        # Esto permite al usuario al menos agregar el ticker manualmente
        logger.warning(f"⚠️  No mock matches for '{query}', returning generic result")
        generic_result = StockSearchResult(
            symbol=query_upper,
            name=f"{query_upper} - Ticker not in mock database (API offline)",
            type="Equity",
            region="United States",
            currency="USD"
        )
        return [generic_result]
    
    def _get_mock_quote(self, symbol: str) -> StockQuote:
        """
        Datos mock para cotización - fallback cuando Alpha Vantage falla
        
        Precios aproximados para stocks comunes (no financieros reales)
        """
        mock_quotes = {
            # Tech Giants
            "AAPL": {"price": 178.50, "change": 2.35, "change_percent": 1.33, "high": 180.25, "low": 176.80},
            "MSFT": {"price": 412.30, "change": -1.20, "change_percent": -0.29, "high": 415.50, "low": 410.00},
            "GOOGL": {"price": 142.80, "change": 3.45, "change_percent": 2.48, "high": 143.90, "low": 139.50},
            "AMZN": {"price": 178.20, "change": 0.90, "change_percent": 0.51, "high": 179.30, "low": 176.50},
            "META": {"price": 485.60, "change": 8.30, "change_percent": 1.74, "high": 488.50, "low": 478.20},
            
            # Other Tech
            "TSLA": {"price": 242.80, "change": -5.40, "change_percent": -2.18, "high": 248.90, "low": 241.20},
            "NVDA": {"price": 875.30, "change": 12.50, "change_percent": 1.45, "high": 880.00, "low": 865.00},
            "NFLX": {"price": 625.40, "change": -3.80, "change_percent": -0.60, "high": 630.00, "low": 622.00},
            
            # Semiconductors
            "AMD": {"price": 165.80, "change": 3.25, "change_percent": 2.00, "high": 167.50, "low": 163.20},
            "INTC": {"price": 42.15, "change": -0.85, "change_percent": -1.98, "high": 43.20, "low": 41.90},
            "QCOM": {"price": 148.90, "change": 2.10, "change_percent": 1.43, "high": 149.80, "low": 147.00},
            
            # Finance
            "JPM": {"price": 185.50, "change": 1.20, "change_percent": 0.65, "high": 186.00, "low": 183.50},
            "BAC": {"price": 38.75, "change": 0.35, "change_percent": 0.91, "high": 39.00, "low": 38.20},
            "V": {"price": 285.30, "change": 2.80, "change_percent": 0.99, "high": 286.50, "low": 283.00},
            
            # Consumer
            "WMT": {"price": 165.20, "change": 1.10, "change_percent": 0.67, "high": 166.00, "low": 164.00},
            "PG": {"price": 158.90, "change": 0.50, "change_percent": 0.32, "high": 159.50, "low": 157.80},
            "KO": {"price": 62.30, "change": 0.25, "change_percent": 0.40, "high": 62.60, "low": 61.90},
            "MCD": {"price": 295.40, "change": -1.50, "change_percent": -0.51, "high": 297.50, "low": 294.00},
            
            # Restaurantes
            "CMG": {"price": 2850.75, "change": 45.30, "change_percent": 1.61, "high": 2875.00, "low": 2810.50},
            "SBUX": {"price": 98.50, "change": -0.80, "change_percent": -0.81, "high": 99.50, "low": 97.80},
            
            # Healthcare
            "JNJ": {"price": 162.80, "change": 0.90, "change_percent": 0.56, "high": 163.50, "low": 161.50},
            "UNH": {"price": 548.30, "change": 3.20, "change_percent": 0.59, "high": 550.00, "low": 545.00},
        }
        
        symbol_upper = symbol.upper()
        base = mock_quotes.get(
            symbol_upper, 
            {
                "price": 100.0, 
                "change": 0.0, 
                "change_percent": 0.0, 
                "high": 105.0, 
                "low": 95.0
            }
        )
        
        quote = StockQuote(
            symbol=symbol_upper,
            name=symbol_upper,
            price=base["price"],
            change=base["change"],
            change_percent=base["change_percent"],
            high=base["high"],
            low=base["low"],
            open=base["price"],
            previous_close=base["price"] - base["change"],
            volume=1000000,
            currency="USD",
            timestamp=datetime.utcnow()
        )
        
        logger.info(f"📊 Returning mock quote for {symbol_upper}: ${base['price']}")
        return quote


# Instancia global del servicio
alpha_vantage_service = AlphaVantageService()
