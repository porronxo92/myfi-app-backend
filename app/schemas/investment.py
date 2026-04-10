from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, Literal
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal


# ============================================
# BASE SCHEMAS
# ============================================

class InvestmentBase(BaseModel):
    """Schema base para Investment"""
    model_config = ConfigDict(populate_by_name=True)
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Ticker de la acción")
    company_name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="Nombre de la empresa", 
        validation_alias="companyName",
        serialization_alias="companyName"
    )
    shares: Decimal = Field(..., gt=0, description="Cantidad de acciones")
    average_price: Decimal = Field(
        ..., 
        gt=0, 
        description="Precio promedio de compra", 
        validation_alias="averagePrice",
        serialization_alias="averagePrice"
    )
    purchase_date: date = Field(
        ..., 
        description="Fecha de compra", 
        validation_alias="purchaseDate",
        serialization_alias="purchaseDate"
    )
    sale_price: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Precio de venta (solo para status=sold)",
        validation_alias="salePrice",
        serialization_alias="salePrice"
    )
    sale_date: Optional[date] = Field(
        None,
        description="Fecha de venta (solo para status=sold)",
        validation_alias="saleDate",
        serialization_alias="saleDate"
    )
    status: Literal['active', 'sold', 'watchlist'] = Field(
        default='active',
        description="Estado de la inversión"
    )
    notes: Optional[str] = Field(None, description="Notas adicionales")
    
    @field_validator('symbol')
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        """Convertir ticker a mayúsculas"""
        return v.upper().strip()
    
    @field_validator('shares', 'average_price')
    @classmethod
    def round_decimals(cls, v: Decimal) -> Decimal:
        """Redondear decimales"""
        return round(v, 4) if isinstance(v, Decimal) else Decimal(str(v))


# ============================================
# REQUEST SCHEMAS
# ============================================

class InvestmentCreate(InvestmentBase):
    """Schema para crear nueva inversión"""
    pass


class InvestmentSell(BaseModel):
    """Schema para vender una posición (cerrar swing trade)"""
    model_config = ConfigDict(populate_by_name=True)
    
    sale_price: Decimal = Field(
        ...,
        gt=0,
        description="Precio de venta",
        validation_alias="salePrice"
    )
    sale_date: date = Field(
        default_factory=date.today,
        description="Fecha de venta",
        validation_alias="saleDate"
    )
    notes: Optional[str] = Field(None, description="Notas sobre la venta")
    
    @field_validator('sale_price')
    @classmethod
    def round_sale_price(cls, v: Decimal) -> Decimal:
        """Redondear precio de venta"""
        return round(v, 2) if isinstance(v, Decimal) else Decimal(str(v))


class InvestmentUpdate(BaseModel):
    """Schema para actualizar inversión existente"""
    shares: Optional[Decimal] = Field(None, gt=0)
    average_price: Optional[Decimal] = Field(None, gt=0)
    sale_price: Optional[Decimal] = Field(None, gt=0, validation_alias="salePrice")
    sale_date: Optional[date] = Field(None, validation_alias="saleDate")
    status: Optional[Literal['active', 'sold', 'watchlist']] = None
    notes: Optional[str] = None
    
    @field_validator('shares', 'average_price', 'sale_price')
    @classmethod
    def round_decimals(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Redondear decimales"""
        if v is None:
            return None
        return round(v, 4) if isinstance(v, Decimal) else Decimal(str(v))


# ============================================
# RESPONSE SCHEMAS
# ============================================

class InvestmentResponse(InvestmentBase):
    """Schema para respuesta de Investment"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: UUID
    user_id: UUID = Field(serialization_alias="userId")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    
    @model_validator(mode='before')
    @classmethod
    def populate_encrypted_fields(cls, data):
        """
        Lee campos del modelo (TypeDecorator desencripta automáticamente).
        
        NOTA: Los campos symbol, company_name, shares, average_price ahora son 
        EncryptedString/EncryptedNumeric que se desencriptan automáticamente.
        """
        if hasattr(data, 'symbol'):
            if not isinstance(data, dict):
                obj_data = {
                    'id': data.id,
                    'user_id': data.user_id,
                    # TypeDecorator desencripta automáticamente
                    'symbol': data.symbol,
                    'company_name': data.company_name,
                    'shares': data.shares,
                    'average_price': data.average_price,
                    'purchase_date': data.purchase_date,
                    'sale_price': data.sale_price,
                    'sale_date': data.sale_date,
                    'status': data.status.value if hasattr(data.status, 'value') else data.status,
                    'notes': data.notes,
                    'created_at': data.created_at,
                    'updated_at': data.updated_at,
                }
                return obj_data
        return data


# ============================================
# STOCK DATA SCHEMAS
# ============================================

class StockQuote(BaseModel):
    """Cotización actual de una acción"""
    model_config = ConfigDict(populate_by_name=True)
    
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float = Field(serialization_alias="changePercent")
    high: float
    low: float
    open: float
    previous_close: float = Field(serialization_alias="previousClose")
    volume: int
    currency: str = "USD"
    timestamp: datetime


class StockSearchResult(BaseModel):
    """Resultado de búsqueda de acciones"""
    symbol: str
    name: str
    type: str
    region: str
    currency: str


# ============================================
# ENRICHED SCHEMAS (con datos de mercado)
# ============================================

class EnrichedInvestment(InvestmentResponse):
    """Investment enriquecida con datos actuales del mercado"""
    current_price: float = Field(..., description="Precio actual del mercado", serialization_alias="currentPrice")
    change_percent: float = Field(..., description="Cambio porcentual del día", serialization_alias="changePercent")
    total_value: float = Field(..., description="Valor total de la posición", serialization_alias="totalValue")
    total_gain_loss: float = Field(..., description="Ganancia/pérdida total en $", serialization_alias="totalGainLoss")
    total_gain_loss_percent: float = Field(..., description="Ganancia/pérdida total en %", serialization_alias="totalGainLossPercent")
    day_change: float = Field(..., description="Cambio del día en $", serialization_alias="dayChange")


class PortfolioSummary(BaseModel):
    """Resumen del portfolio completo"""
    model_config = ConfigDict(populate_by_name=True)

    total_value: float = Field(..., description="Valor total del portfolio (investedValue + cashBalance)", serialization_alias="totalValue")
    total_invested: float = Field(..., description="Total invertido originalmente", serialization_alias="totalInvested")
    total_gain_loss: float = Field(..., description="Ganancia/pérdida total (solo posiciones)", serialization_alias="totalGainLoss")
    total_gain_loss_percent: float = Field(..., description="% de rendimiento (solo posiciones)", serialization_alias="totalGainLossPercent")
    day_change: float = Field(..., description="Cambio total del día", serialization_alias="dayChange")
    day_change_percent: float = Field(..., description="% cambio del día", serialization_alias="dayChangePercent")
    positions_count: int = Field(..., description="Número de posiciones", serialization_alias="positionsCount")
    cash_balance: float = Field(0.0, description="Efectivo no invertido", serialization_alias="cashBalance")
    invested_value: float = Field(0.0, description="Valor actual de las posiciones", serialization_alias="investedValue")


class InvestmentInsight(BaseModel):
    """Insight o recomendación"""
    type: str = Field(..., description="Tipo: info, warning, success, danger")
    title: str
    message: str
    icon: str


# ============================================
# CASH BALANCE SCHEMAS
# ============================================

class CashBalanceUpdate(BaseModel):
    """Schema para actualizar cash balance"""
    model_config = ConfigDict(populate_by_name=True)

    cash_balance: Decimal = Field(
        ...,
        ge=0,
        description="Efectivo no invertido (debe ser >= 0)",
        validation_alias="cashBalance"
    )

    @field_validator('cash_balance')
    @classmethod
    def round_cash_balance(cls, v: Decimal) -> Decimal:
        """Redondear a 2 decimales"""
        return round(v, 2) if isinstance(v, Decimal) else Decimal(str(v)).quantize(Decimal("0.01"))


class CashBalanceResponse(BaseModel):
    """Schema para respuesta de cash balance"""
    model_config = ConfigDict(populate_by_name=True)

    cash_balance: float = Field(..., description="Efectivo no invertido", serialization_alias="cashBalance")


# ============================================
# COMBINED RESPONSE
# ============================================

class InvestmentsWithSummary(BaseModel):
    """Respuesta completa con posiciones enriquecidas y resumen"""
    positions: list[EnrichedInvestment]
    summary: PortfolioSummary
    insights: list[InvestmentInsight]
