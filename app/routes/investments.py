"""
Endpoints REST para Investments (Inversiones Bursátiles)
=========================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.schemas.investment import (
    InvestmentCreate,
    InvestmentUpdate,
    InvestmentSell,
    InvestmentResponse,
    EnrichedInvestment,
    InvestmentsWithSummary,
    StockSearchResult,
    StockQuote
)
from app.services.investment_service import investment_service
from app.services.stock_api_service import stock_api_service
from app.utils.security import get_current_user, check_rate_limit
from app.utils.logger import get_logger
from app.models import User

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/investments",
    tags=["investments"]
)


# ============================================
# SEARCH - Buscar acciones con Finnhub + Alpha Vantage Fallback
# ============================================

@router.get("/search", response_model=List[StockSearchResult])
async def search_stocks(
    q: str = Query(..., min_length=1, description="Ticker o nombre de empresa"),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Buscar acciones por ticker o nombre de empresa
    
    Utiliza Finnhub como prioridad, con fallback a Alpha Vantage
    
    **Ejemplo:**
    - GET /api/investments/search?q=AAPL
    - GET /api/investments/search?q=Apple
    """
    logger.info(f"User {current_user.id} searching stocks: {q}")
    
    results = await stock_api_service.search_stocks(q)
    return results


# ============================================
# QUOTE - Obtener cotización con Finnhub + Alpha Vantage Fallback
# ============================================

@router.get("/quote", response_model=StockQuote)
async def get_stock_quote(
    q: str = Query(..., min_length=1, max_length=10, description="Ticker de la acción"),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener cotización en tiempo real de una acción
    
    Utiliza Finnhub como prioridad (60 llamadas/minuto), 
    con fallback a Alpha Vantage (25 llamadas/día)
    
    **Ejemplo:**
    - GET /api/investments/quote?q=ONON
    - GET /api/investments/quote?q=AAPL
    
    **Respuesta:**
    ```json
    {
      "symbol": "ONON",
      "name": "ONON",
      "price": 48.93,
      "change": -0.19,
      "change_percent": -0.39,
      "high": 50.29,
      "low": 47.89,
      "open": 48.50,
      "previous_close": 49.12,
      "volume": 4664389,
      "currency": "USD",
      "timestamp": "2026-01-12T00:00:00"
    }
    ```
    """
    logger.info(f"User {current_user.id} requesting quote for: {q}")
    
    quote = await stock_api_service.get_stock_quote(q)
    
    if not quote:
        logger.warning(f"No quote found for ticker: {q}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo obtener cotización para el ticker '{q}'. Intenta de nuevo más tarde."
        )
    
    return quote


# ============================================
# LOGO - Obtener logo de una acción
# ============================================

@router.get("/logo")
async def get_stock_logo(
    q: str = Query(..., min_length=1, max_length=10, description="Ticker de la acción"),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener el logo de una acción desde Brandfetch API
    
    **Ejemplo:**
    - GET /api/investments/logo?q=AAPL
    - GET /api/investments/logo?q=MSFT
    
    **Respuesta exitosa:**
    ```json
    {
      "ticker": "AAPL",
      "logo_url": "https://cdn.brandfetch.io/AAPL?c=YOUR_CLIENT_ID",
      "available": true,
      "content_type": "image/png"
    }
    ```
    
    **Respuesta cuando no está disponible:**
    ```json
    {
      "ticker": "AAPL",
      "logo_url": null,
      "available": false,
      "message": "Logo not available for AAPL"
    }
    ```
    """
    logger.info(f"User {current_user.id} requesting logo for: {q}")
    
    logo_data = await stock_api_service.get_stock_logo(q)
    
    return logo_data


# ============================================
# LIST - Listar inversiones con datos de mercado
# ============================================

@router.get("", response_model=InvestmentsWithSummary)
async def list_investments(
    status: Optional[str] = Query(None, description="Filter by status: 'active', 'sold', or None for all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Listar todas las inversiones del usuario con datos enriquecidos
    
    **Query Parameters:**
    - status: 'active' para posiciones abiertas, 'sold' para vendidas, None para todas
    
    **Retorna:**
    - positions: Lista de inversiones con precios actuales y cálculos
    - summary: Resumen del portfolio (valor total, ganancias, etc.)
    - insights: Recomendaciones de diversificación
    """
    logger.info(f"User {current_user.id} listing investments (status={status})")
    
    # Convertir string a enum si se especificó
    status_filter = None
    if status:
        try:
            from app.models.investment import InvestmentStatus
            status_filter = InvestmentStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Use 'active' or 'sold'"
            )
    
    # Obtener inversiones de la BD
    investments = investment_service.get_user_investments(db, current_user.id, status_filter)
    
    # Enriquecer con datos de mercado (solo para activas)
    if status_filter == InvestmentStatus.ACTIVE or status_filter is None:
        enriched = await investment_service.enrich_investments(investments)
    else:
        # Para vendidas, no enriquecemos (no tiene sentido cotización actual)
        enriched = [investment_service.convert_to_enriched(inv) for inv in investments]
    
    # Calcular resumen del portfolio
    summary = investment_service.calculate_portfolio_summary(enriched)
    
    # Generar insights
    insights = investment_service.generate_insights(enriched, summary)
    
    return InvestmentsWithSummary(
        positions=enriched,
        summary=summary,
        insights=insights
    )


# ============================================
# GET ONE - Obtener inversión específica
# ============================================

@router.get("/{investment_id}", response_model=EnrichedInvestment)
async def get_investment(
    investment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtener una inversión específica con datos enriquecidos
    """
    logger.info(f"User {current_user.id} getting investment {investment_id}")
    
    investment = investment_service.get_investment_by_id(db, investment_id, current_user.id)
    
    if not investment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investment not found"
        )
    
    # Enriquecer con datos de mercado
    enriched = await investment_service.enrich_investments([investment])
    
    return enriched[0]


# ============================================
# CREATE - Crear nueva inversión
# ============================================

@router.post("", response_model=InvestmentResponse, status_code=status.HTTP_201_CREATED)
async def create_investment(
    investment_data: InvestmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Crear nueva inversión
    
    **Campos requeridos:**
    - symbol: Ticker de la acción (ej: AAPL)
    - company_name: Nombre completo de la empresa
    - shares: Cantidad de acciones (> 0)
    - average_price: Precio promedio de compra (> 0)
    - purchase_date: Fecha de compra (formato: YYYY-MM-DD)
    - notes: Notas adicionales (opcional)
    """
    logger.info(f"User {current_user.id} creating investment: {investment_data.symbol}")
    
    investment = investment_service.create_investment(db, investment_data, current_user.id)
    
    return investment


# ============================================
# UPDATE - Actualizar inversión
# ============================================

@router.patch("/{investment_id}", response_model=InvestmentResponse)
async def update_investment(
    investment_id: UUID,
    investment_data: InvestmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Actualizar inversión existente
    
    **Campos actualizables:**
    - shares: Nueva cantidad de acciones
    - average_price: Nuevo precio promedio
    - notes: Nuevas notas
    
    Solo se actualizan los campos proporcionados (PATCH parcial)
    """
    logger.info(f"User {current_user.id} updating investment {investment_id}")
    
    investment = investment_service.update_investment(
        db,
        investment_id,
        investment_data,
        current_user.id
    )
    
    if not investment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investment not found"
        )
    
    return investment


# ============================================
# SELL - Vender posición (cerrar swing trade)
# ============================================

@router.post("/{investment_id}/sell", response_model=InvestmentResponse)
async def sell_investment(
    investment_id: UUID,
    sell_data: InvestmentSell,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Vender posición (cerrar swing trade)
    
    Marca la inversión como 'sold' y registra:
    - Precio de venta
    - Fecha de venta
    - Notas adicionales
    
    **No elimina el registro**, lo mantiene para historial.
    
    **Ejemplo:**
    ```json
    {
        "salePrice": 185.50,
        "saleDate": "2026-01-13",
        "notes": "Venta por objetivo alcanzado"
    }
    ```
    """
    logger.info(f"User {current_user.id} selling investment {investment_id}")
    
    # Actualizar a status='sold' con datos de venta
    update_data = InvestmentUpdate(
        status='sold',
        sale_price=sell_data.sale_price,
        sale_date=sell_data.sale_date,
        notes=sell_data.notes
    )
    
    investment = investment_service.update_investment(
        db,
        investment_id,
        update_data,
        current_user.id
    )
    
    if not investment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investment not found"
        )
    
    return investment


# ============================================
# DELETE - Eliminar inversión permanentemente
# ============================================

@router.delete("/{investment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investment(
    investment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(check_rate_limit)
):
    """
    Eliminar inversión permanentemente
    
    **ATENCIÓN:** Esta acción es irreversible.
    Para mantener historial, usa POST /{investment_id}/sell en su lugar.
    
    **Retorna:**
    - 204 No Content si se eliminó correctamente
    - 404 Not Found si no existe o no pertenece al usuario
    """
    logger.info(f"User {current_user.id} permanently deleting investment {investment_id}")
    
    success = investment_service.delete_investment(db, investment_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investment not found"
        )


# ============================================
# DIAGNOSTICS - Estado de las APIs de stocks
# ============================================

@router.get("/api-status")
async def get_stock_api_status(
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el estado actual de las APIs de stocks.
    
    Útil para debugging y monitoreo de límites de rate limiting.
    
    **Respuesta:**
    ```json
    {
        "finnhub": {
            "configured": true,
            "available": true,
            "calls_last_minute": 12,
            "limit_per_minute": 60,
            "remaining": 48
        },
        "alpha_vantage": {
            "configured": true,
            "available": true,
            "calls_last_day": 5,
            "limit_per_day": 25,
            "remaining": 20
        },
        "timestamp": "2026-01-13T20:00:00"
    }
    ```
    """
    logger.info(f"User {current_user.id} checking API status")
    return stock_api_service.get_api_status()
    return None
