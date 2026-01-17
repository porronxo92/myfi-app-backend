"""
Unified Stock API Service
=========================
Sistema de integración con múltiples APIs de datos bursátiles.
Implementa fallback automático: Finnhub (Prioridad 1) → Alpha Vantage (Fallback)

Finnhub: 60 llamadas/minuto (máxima disponibilidad)
Alpha Vantage: 25 llamadas/día (fallback)
"""

import os
import httpx
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from app.config import settings
from app.schemas.investment import StockQuote, StockSearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StockAPIService:
    """
    Servicio unificado para consultas de datos bursátiles.
    Implementa fallback automático: Finnhub → Alpha Vantage
    """
    
    def __init__(self):
        # Configurar API keys
        self.finnhub_key = settings.FINNHUB_API_KEY if hasattr(settings, 'FINNHUB_API_KEY') else os.getenv('FINNHUB_API_KEY', '')
        self.finnhub_base_url = "https://finnhub.io/api/v1"
        
        self.alpha_vantage_key = settings.ALPHA_VANTAGE_API_KEY
        self.alpha_vantage_base_url = settings.ALPHA_VANTAGE_BASE_URL
        
        # Brandfetch Configuration
        self.brandfetch_client_id = settings.BRANDFETCH_CLIENT_ID if hasattr(settings, 'BRANDFETCH_CLIENT_ID') else os.getenv('BRANDFETCH_CLIENT_ID', '')
        self.brandfetch_base_url = "https://cdn.brandfetch.io"
        
        # Rate limiting tracking
        self.finnhub_calls = []
        self.alpha_vantage_calls = []
        
        self.FINNHUB_MAX_PER_MINUTE = int(os.getenv('FINNHUB_MAX_CALLS_PER_MINUTE', 60))
        self.ALPHA_VANTAGE_MAX_PER_DAY = int(os.getenv('ALPHA_VANTAGE_MAX_CALLS_PER_DAY', 25))
        
        # Cliente HTTP compartido para mejor rendimiento
        self._client: Optional[httpx.AsyncClient] = None
        
        # Semáforo para limitar concurrencia (evitar saturar APIs)
        self._semaphore = asyncio.Semaphore(10)  # Máximo 10 peticiones concurrentes
        
        # Validar configuración
        self._validate_config()
    
    def _validate_config(self):
        """Validar que las claves de API estén configuradas"""
        if not self.finnhub_key or self.finnhub_key == 'your_finnhub_api_key_here':
            logger.warning("⚠️  Finnhub API key not configured - will use only Alpha Vantage")
        else:
            logger.info(f"✅ Finnhub service initialized with API key: {self.finnhub_key[:8]}...")
        
        if not self.alpha_vantage_key or self.alpha_vantage_key == "demo":
            logger.warning("⚠️  Alpha Vantage API key not configured - service will use mock data")
        else:
            logger.info(f"✅ Alpha Vantage service initialized with API key: {self.alpha_vantage_key[:8]}...")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtener o crear cliente HTTP compartido para mejor rendimiento"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=30)
            )
        return self._client
    
    async def close(self):
        """Cerrar cliente HTTP al finalizar"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    # ========== BÚSQUEDA DE ACCIONES ==========
    
    async def search_stocks(self, keywords: str) -> List[StockSearchResult]:
        """
        Buscar acciones por símbolo o nombre.
        Prioridad: Finnhub → Alpha Vantage (fallback)
        
        Args:
            keywords: Texto a buscar (ticker o nombre)
            
        Returns:
            Lista de resultados de búsqueda normalizados
        """
        if not keywords or len(keywords.strip()) < 1:
            return []
        
        # 1. Intentar con Finnhub
        if self.finnhub_key and self.finnhub_key != 'your_finnhub_api_key_here':
            try:
                if self._can_call_finnhub():
                    logger.info(f"[SEARCH] Intentando con Finnhub: {keywords}")
                    results = await self._search_finnhub(keywords)
                    
                    if results:
                        logger.info(f"[SEARCH] ✓ Finnhub devolvió {len(results)} resultados")
                        return results
                    else:
                        logger.debug(f"[SEARCH] Finnhub sin resultados para: {keywords}")
            except Exception as e:
                logger.warning(f"[SEARCH] Error en Finnhub: {str(e)}")
        
        # 2. Fallback a Alpha Vantage
        try:
            if self._can_call_alpha_vantage():
                logger.info(f"[SEARCH] Fallback a Alpha Vantage: {keywords}")
                results = await self._search_alpha_vantage(keywords)
                
                if results:
                    logger.info(f"[SEARCH] ✓ Alpha Vantage devolvió {len(results)} resultados")
                    return results
        except Exception as e:
            logger.warning(f"[SEARCH] Error en Alpha Vantage: {str(e)}")
        
        # 3. Si ambos fallaron, retornar resultado genérico
        logger.warning(f"[SEARCH] Ambas APIs fallaron para: {keywords}")
        return [
            StockSearchResult(
                symbol=keywords.upper(),
                name=f"{keywords.upper()} - Not found in API",
                type="Unknown",
                region="Unknown",
                currency="USD"
            )
        ]
    
    async def _search_finnhub(self, keywords: str) -> List[StockSearchResult]:
        """Búsqueda usando Finnhub API"""
        self._track_finnhub_call()
        
        client = await self._get_client()
        response = await client.get(
            f"{self.finnhub_base_url}/search",
            params={"q": keywords, "token": self.finnhub_key}
        )
        response.raise_for_status()
        data = response.json()
        
        # Normalizar respuesta de Finnhub
        results = []
        if 'result' in data and data['result']:
            for item in data['result'][:10]:  # Máximo 10 resultados
                results.append(StockSearchResult(
                    symbol=item.get('symbol', ''),
                    name=item.get('description', item.get('symbol', '')),
                    type=item.get('type', 'Unknown'),
                    region=item.get('displaySymbol', '').split('.')[-1] if '.' in item.get('displaySymbol', '') else 'US',
                    currency="USD"
                ))
        
        return results
    
    async def _search_alpha_vantage(self, keywords: str) -> List[StockSearchResult]:
        """Búsqueda usando Alpha Vantage API (fallback)"""
        self._track_alpha_vantage_call()
        
        client = await self._get_client()
        response = await client.get(
            self.alpha_vantage_base_url,
            params={
                'function': 'SYMBOL_SEARCH',
                'keywords': keywords,
                'apikey': self.alpha_vantage_key
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Normalizar respuesta de Alpha Vantage
        results = []
        if 'bestMatches' in data and data['bestMatches']:
            for match in data['bestMatches'][:10]:  # Máximo 10 resultados
                results.append(StockSearchResult(
                    symbol=match.get('1. symbol', ''),
                    name=match.get('2. name', ''),
                    type=match.get('3. type', 'Unknown'),
                    region=match.get('4. region', 'Unknown'),
                    currency=match.get('8. currency', 'USD')
                ))
        
        return results
    
    # ========== COTIZACIÓN DE ACCIONES ==========
    
    async def get_stock_quote(self, symbol: str) -> Optional[StockQuote]:
        """
        Obtener cotización actual de una acción.
        Prioridad: Finnhub → Alpha Vantage (fallback)
        
        Args:
            symbol: Ticker del stock (ej: AAPL)
            
        Returns:
            StockQuote con datos normalizados o None si falla
        """
        symbol = symbol.upper().strip()
        
        # 1. Intentar con Finnhub
        if self.finnhub_key and self.finnhub_key != 'your_finnhub_api_key_here':
            try:
                if self._can_call_finnhub():
                    logger.info(f"[QUOTE] Intentando con Finnhub: {symbol}")
                    quote = await self._get_quote_finnhub(symbol)
                    
                    if quote:
                        logger.info(f"[QUOTE] ✓ Finnhub devolvió cotización para {symbol}")
                        return quote
            except Exception as e:
                logger.warning(f"[QUOTE] Error en Finnhub: {str(e)}")
        
        # 2. Fallback a Alpha Vantage
        try:
            if self._can_call_alpha_vantage():
                logger.info(f"[QUOTE] Fallback a Alpha Vantage: {symbol}")
                quote = await self._get_quote_alpha_vantage(symbol)
                
                if quote:
                    logger.info(f"[QUOTE] ✓ Alpha Vantage devolvió cotización para {symbol}")
                    return quote
        except Exception as e:
            logger.warning(f"[QUOTE] Error en Alpha Vantage: {str(e)}")
        
        # 3. Si ambos fallaron
        logger.error(f"[QUOTE] Ambas APIs fallaron para: {symbol}")
        return None
    
    async def _get_quote_finnhub(self, symbol: str) -> Optional[StockQuote]:
        """Obtener cotización usando Finnhub API"""
        self._track_finnhub_call()
        
        client = await self._get_client()
        response = await client.get(
            f"{self.finnhub_base_url}/quote",
            params={"symbol": symbol, "token": self.finnhub_key}
        )
        response.raise_for_status()
        data = response.json()
        
        # Normalizar respuesta de Finnhub
        if data and 'c' in data:
            timestamp = datetime.fromtimestamp(data.get('t', datetime.now().timestamp()))
            
            return StockQuote(
                symbol=symbol,
                name=symbol,
                price=float(data.get('c', 0)),
                change=float(data.get('c', 0)) - float(data.get('pc', 0)),
                change_percent=(
                    ((float(data.get('c', 0)) - float(data.get('pc', 0))) / float(data.get('pc', 1))) * 100
                    if float(data.get('pc', 0)) > 0 else 0
                ),
                high=float(data.get('h', 0)),
                low=float(data.get('l', 0)),
                open=float(data.get('o', 0)),
                previous_close=float(data.get('pc', 0)),
                volume=int(data.get('v', 0)),
                currency="USD",
                timestamp=timestamp
            )
        
        return None
    
    async def _get_quote_alpha_vantage(self, symbol: str) -> Optional[StockQuote]:
        """Obtener cotización usando Alpha Vantage API (fallback)"""
        self._track_alpha_vantage_call()
        
        client = await self._get_client()
        response = await client.get(
            self.alpha_vantage_base_url,
            params={
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Normalizar respuesta de Alpha Vantage
        if 'Global Quote' in data and data['Global Quote']:
            quote_data = data['Global Quote']
            
            if '05. price' in quote_data:
                current_price = float(quote_data.get('05. price', 0))
                previous_close = float(quote_data.get('08. previous close', 0))
                
                return StockQuote(
                    symbol=symbol,
                    name=symbol,
                    price=current_price,
                    change=float(quote_data.get('09. change', 0)),
                    change_percent=float(quote_data.get('10. change percent', '0').replace('%', '')),
                    high=float(quote_data.get('03. high', 0)),
                    low=float(quote_data.get('04. low', 0)),
                    open=float(quote_data.get('02. open', 0)),
                    previous_close=previous_close,
                    volume=int(quote_data.get('06. volume', 0)),
                    currency="USD",
                    timestamp=datetime.now()
                )
        
        return None
    
    # ========== COTIZACIONES MÚLTIPLES ==========
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Optional[StockQuote]]:
        """
        Obtener cotizaciones para múltiples símbolos con rate limiting inteligente.
        
        Procesa todas las cotizaciones en paralelo respetando los límites de cada API.
        Finnhub (60/min) permite concurrencia, Alpha Vantage (25/día) requiere delays.
        
        Optimizado con:
        - Cliente HTTP compartido (reutiliza conexiones)
        - Semáforo para limitar concurrencia
        - Procesamiento en batches si hay muchos símbolos
        
        Args:
            symbols: Lista de tickers
            
        Returns:
            Diccionario: {'AAPL': StockQuote, 'TSLA': StockQuote}
        """
        if not symbols:
            return {}
        
        start_time = datetime.now()
        logger.info(f"[BATCH] 🚀 Iniciando obtención de cotizaciones para {len(symbols)} símbolos")
        
        quotes = {}
        
        # Procesar en batches de 20 para evitar sobrecarga
        batch_size = 20
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            logger.info(f"[BATCH] Procesando batch {i//batch_size + 1}: {len(batch)} símbolos")
            
            # Crear tareas concurrentes con control de semáforo
            tasks = [self._get_quote_with_semaphore(symbol) for symbol in batch]
            
            # Ejecutar todas las tareas concurrentemente
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Procesar resultados
            for symbol, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Error obteniendo cotización para {symbol}: {str(result)}")
                    quotes[symbol] = None
                else:
                    quotes[symbol] = result
        
        elapsed = (datetime.now() - start_time).total_seconds()
        success_count = len([q for q in quotes.values() if q])
        logger.info(f"[BATCH] ✅ Completadas {success_count}/{len(symbols)} cotizaciones en {elapsed:.2f}s ({success_count/elapsed:.1f} quotes/s)")
        return quotes
    
    async def _get_quote_with_semaphore(self, symbol: str) -> Optional[StockQuote]:
        """
        Obtener una cotización con control de concurrencia mediante semáforo.
        Limita el número de peticiones simultáneas para evitar saturar las APIs.
        """
        async with self._semaphore:
            try:
                quote = await self.get_stock_quote(symbol)
                return quote
            except Exception as e:
                logger.error(f"Error obteniendo cotización para {symbol}: {str(e)}")
                return None
    
    # ========== RATE LIMITING ==========
    
    def _can_call_finnhub(self) -> bool:
        """Verifica si se puede llamar a Finnhub sin exceder límites"""
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Limpiar llamadas antiguas
        self.finnhub_calls = [call for call in self.finnhub_calls if call > one_minute_ago]
        
        can_call = len(self.finnhub_calls) < self.FINNHUB_MAX_PER_MINUTE
        
        if not can_call:
            logger.debug(f"Finnhub rate limit alcanzado: {len(self.finnhub_calls)}/{self.FINNHUB_MAX_PER_MINUTE}")
        
        return can_call
    
    def _can_call_alpha_vantage(self) -> bool:
        """Verifica si se puede llamar a Alpha Vantage sin exceder límites"""
        now = datetime.now()
        one_day_ago = now - timedelta(days=1)
        
        # Limpiar llamadas antiguas
        self.alpha_vantage_calls = [call for call in self.alpha_vantage_calls if call > one_day_ago]
        
        can_call = len(self.alpha_vantage_calls) < self.ALPHA_VANTAGE_MAX_PER_DAY
        
        if not can_call:
            logger.debug(f"Alpha Vantage rate limit alcanzado: {len(self.alpha_vantage_calls)}/{self.ALPHA_VANTAGE_MAX_PER_DAY}")
        
        return can_call
    
    def _track_finnhub_call(self):
        """Registra una llamada a Finnhub"""
        self.finnhub_calls.append(datetime.now())
    
    def _track_alpha_vantage_call(self):
        """Registra una llamada a Alpha Vantage"""
        self.alpha_vantage_calls.append(datetime.now())
    
    # ========== DIAGNÓSTICO ==========
    
    def get_api_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual de las APIs"""
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        one_day_ago = now - timedelta(days=1)
        
        finnhub_recent = len([c for c in self.finnhub_calls if c > one_minute_ago])
        alpha_vantage_recent = len([c for c in self.alpha_vantage_calls if c > one_day_ago])
        
        return {
            'finnhub': {
                'configured': bool(self.finnhub_key and self.finnhub_key != 'your_finnhub_api_key_here'),
                'available': self._can_call_finnhub(),
                'calls_last_minute': finnhub_recent,
                'limit_per_minute': self.FINNHUB_MAX_PER_MINUTE,
                'remaining': max(0, self.FINNHUB_MAX_PER_MINUTE - finnhub_recent)
            },
            'alpha_vantage': {
                'configured': bool(self.alpha_vantage_key and self.alpha_vantage_key != 'demo'),
                'available': self._can_call_alpha_vantage(),
                'calls_last_day': alpha_vantage_recent,
                'limit_per_day': self.ALPHA_VANTAGE_MAX_PER_DAY,
                'remaining': max(0, self.ALPHA_VANTAGE_MAX_PER_DAY - alpha_vantage_recent)
            },
            'timestamp': datetime.now().isoformat()
        }
    
    # ========== LOGO SERVICE ==========
    
    async def get_stock_logo(self, ticker: str) -> Dict[str, Any]:
        """
        Obtener el logo de una acción desde Brandfetch API.
        
        Args:
            ticker: Símbolo del ticker (ej: AAPL, MSFT, ONON)
            
        Returns:
            Dict con la URL del logo y metadatos
        """
        if not ticker or len(ticker.strip()) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticker symbol is required"
            )
        
        ticker = ticker.strip().upper()
        
        # Verificar si Brandfetch está configurado
        if not self.brandfetch_client_id:
            logger.warning(f"[LOGO] Brandfetch client ID not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Logo service not configured"
            )
        
        try:
            logo_url = f"{self.brandfetch_base_url}/{ticker}?c={self.brandfetch_client_id}"
            
            # Crear cliente temporal con verify=False para evitar problemas SSL
            # (No usamos el cliente compartido porque necesita verify=False)
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                logger.info(f"[LOGO] Fetching logo for {ticker} from Brandfetch")
                
                response = await client.get(logo_url, follow_redirects=True)
                
                if response.status_code == 200:
                    logger.info(f"[LOGO] ✓ Logo found for {ticker}")
                    return {
                        "ticker": ticker,
                        "logo_url": logo_url,
                        "available": True,
                        "content_type": response.headers.get("content-type", "image/png")
                    }
                elif response.status_code == 404:
                    logger.warning(f"[LOGO] Logo not found for {ticker}")
                    return {
                        "ticker": ticker,
                        "logo_url": None,
                        "available": False,
                        "message": f"Logo not available for {ticker}"
                    }
                else:
                    logger.warning(f"[LOGO] Unexpected status {response.status_code} for {ticker}")
                    return {
                        "ticker": ticker,
                        "logo_url": None,
                        "available": False,
                        "message": f"Error retrieving logo: HTTP {response.status_code}"
                    }
                    
        except httpx.TimeoutException:
            logger.error(f"[LOGO] Timeout fetching logo for {ticker}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Logo service timeout"
            )
        except httpx.SSLError as e:
            logger.error(f"[LOGO] SSL Error fetching logo for {ticker}: {str(e)}")
            # Retornar respuesta sin error para no romper el flujo
            return {
                "ticker": ticker,
                "logo_url": None,
                "available": False,
                "message": f"SSL certificate verification failed"
            }
        except Exception as e:
            logger.error(f"[LOGO] Error fetching logo for {ticker}: {str(e)}")
            # Retornar respuesta sin logo disponible en lugar de lanzar excepción
            return {
                "ticker": ticker,
                "logo_url": None,
                "available": False,
                "message": f"Error retrieving logo: {str(e)}"
            }


# Instancia global del servicio
stock_api_service = StockAPIService()
