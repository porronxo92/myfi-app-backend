"""
Investment Business Logic Service
==================================
Servicio de lógica de negocio para inversiones
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from app.models.investment import Investment, InvestmentStatus
from app.models.investment_settings import InvestmentSettings
from app.schemas.investment import (
    InvestmentCreate,
    InvestmentUpdate,
    InvestmentResponse,
    EnrichedInvestment,
    PortfolioSummary,
    InvestmentInsight
)
from app.services.stock_api_service import stock_api_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InvestmentService:
    """Servicio para gestión de inversiones"""

    @staticmethod
    def get_user_cash_balance(db: Session, user_id: UUID) -> float:
        """
        Obtener el cash balance del usuario

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Cash balance del usuario (0.0 si no tiene registro)
        """
        settings = db.query(InvestmentSettings).filter(
            InvestmentSettings.user_id == user_id
        ).first()

        if settings:
            return float(settings.cash_balance)
        return 0.0

    @staticmethod
    def update_user_cash_balance(db: Session, user_id: UUID, cash_balance: Decimal) -> float:
        """
        Actualizar el cash balance del usuario

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            cash_balance: Nuevo valor de cash balance

        Returns:
            Cash balance actualizado
        """
        settings = db.query(InvestmentSettings).filter(
            InvestmentSettings.user_id == user_id
        ).first()

        if settings:
            settings.cash_balance = cash_balance
        else:
            settings = InvestmentSettings(
                user_id=user_id,
                cash_balance=cash_balance
            )
            db.add(settings)

        db.commit()
        db.refresh(settings)

        logger.info(f"Updated cash balance for user {user_id}: {cash_balance}")
        return float(settings.cash_balance)

    @staticmethod
    def get_user_investments(db: Session, user_id: UUID, status: Optional[InvestmentStatus] = None) -> List[Investment]:
        """
        Obtener inversiones de un usuario filtradas por status
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            status: Estado de las inversiones ('active', 'sold', o None para todas)
            
        Returns:
            Lista de inversiones filtradas por status
        """
        query = db.query(Investment).filter(Investment.user_id == user_id)
        
        if status is not None:
            query = query.filter(Investment.status == status)
        
        investments = query.order_by(Investment.created_at.desc()).all()
        
        status_filter = status.value if status else "all"
        logger.info(f"Found {len(investments)} {status_filter} investments for user {user_id}")
        return investments
    
    @staticmethod
    def get_investment_by_id(db: Session, investment_id: UUID, user_id: UUID) -> Optional[Investment]:
        """
        Obtener una inversión específica
        
        Args:
            db: Sesión de base de datos
            investment_id: ID de la inversión
            user_id: ID del usuario (para validación)
            
        Returns:
            Inversión o None
        """
        investment = db.query(Investment).filter(
            and_(
                Investment.id == investment_id,
                Investment.user_id == user_id
            )
        ).first()
        
        return investment
    
    @staticmethod
    def create_investment(db: Session, investment_data: InvestmentCreate, user_id: UUID) -> Investment:
        """
        Crear nueva inversión, descontando el coste del cash balance.
        Lanza ValueError si el efectivo disponible es insuficiente.
        """
        cost = Decimal(str(investment_data.shares)) * Decimal(str(investment_data.average_price))

        # Verificar cash balance
        settings = db.query(InvestmentSettings).filter(
            InvestmentSettings.user_id == user_id
        ).first()

        current_cash = Decimal(str(settings.cash_balance)) if settings else Decimal("0")

        if current_cash < cost:
            raise ValueError(
                f"Efectivo insuficiente. Disponible: {float(current_cash):.2f}, "
                f"Necesario: {float(cost):.2f}"
            )

        # Descontar del cash balance (antes del commit, misma transacción)
        settings.cash_balance = current_cash - cost

        investment = Investment(
            user_id=user_id,
            symbol=investment_data.symbol,
            company_name=investment_data.company_name,
            shares=investment_data.shares,
            average_price=investment_data.average_price,
            purchase_date=investment_data.purchase_date,
            status=InvestmentStatus.ACTIVE,
            notes=investment_data.notes
        )

        db.add(investment)
        db.commit()
        db.refresh(investment)

        logger.info(
            f"Created investment {investment.id} for user {user_id}: {investment.symbol}, "
            f"deducted {cost} from cash (remaining: {settings.cash_balance})"
        )
        return investment
    
    @staticmethod
    def update_investment(
        db: Session,
        investment_id: UUID,
        investment_data: InvestmentUpdate,
        user_id: UUID
    ) -> Optional[Investment]:
        """
        Actualizar inversión existente
        
        Args:
            db: Sesión de base de datos
            investment_id: ID de la inversión
            investment_data: Datos a actualizar
            user_id: ID del usuario
            
        Returns:
            Inversión actualizada o None
        """
        investment = InvestmentService.get_investment_by_id(db, investment_id, user_id)
        
        if not investment:
            return None
        
        # Actualizar solo los campos proporcionados
        update_data = investment_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(investment, field, value)
        
        db.commit()
        db.refresh(investment)
        
        logger.info(f"Updated investment {investment_id}")
        return investment
    
    @staticmethod
    def delete_investment(db: Session, investment_id: UUID, user_id: UUID) -> bool:
        """
        Eliminar inversión
        
        Args:
            db: Sesión de base de datos
            investment_id: ID de la inversión
            user_id: ID del usuario
            
        Returns:
            True si se eliminó, False si no existía
        """
        investment = InvestmentService.get_investment_by_id(db, investment_id, user_id)
        
        if not investment:
            return False
        
        db.delete(investment)
        db.commit()
        
        logger.info(f"Deleted investment {investment_id}")
        return True
    
    @staticmethod
    def convert_to_enriched(investment: Investment) -> EnrichedInvestment:
        """
        Convertir Investment a EnrichedInvestment sin enriquecer con datos de mercado
        Útil para inversiones vendidas donde no necesitamos cotización actual
        
        Args:
            investment: Inversión a convertir
            
        Returns:
            EnrichedInvestment con datos de la inversión original
        """
        shares = float(investment.shares)
        avg_price = float(investment.average_price)
        
        # Para inversiones vendidas, usar el precio de venta si existe
        if investment.status == InvestmentStatus.SOLD and investment.sale_price:
            current_price = float(investment.sale_price)
        else:
            current_price = avg_price
        
        total_value = shares * current_price
        total_invested = shares * avg_price
        total_gain_loss = total_value - total_invested
        total_gain_loss_percent = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0
        
        return EnrichedInvestment(
            id=investment.id,
            user_id=investment.user_id,
            symbol=investment.symbol,
            company_name=investment.company_name,
            shares=investment.shares,
            average_price=investment.average_price,
            purchase_date=investment.purchase_date,
            notes=investment.notes,
            created_at=investment.created_at,
            updated_at=investment.updated_at,
            status=investment.status,
            sale_price=investment.sale_price,
            sale_date=investment.sale_date,
            current_price=current_price,
            change_percent=0.0,  # No aplicable para vendidas
            total_value=total_value,
            total_gain_loss=total_gain_loss,
            total_gain_loss_percent=total_gain_loss_percent,
            day_change=0.0  # No aplicable para vendidas
        )
    
    @staticmethod
    async def enrich_investments(investments: List[Investment]) -> List[EnrichedInvestment]:
        """
        Enriquecer inversiones con datos de mercado actuales
        
        Args:
            investments: Lista de inversiones
            
        Returns:
            Lista de inversiones enriquecidas con cálculos
        """
        if not investments:
            return []
        
        # Obtener cotizaciones actuales con el nuevo servicio unificado
        symbols = [inv.symbol for inv in investments]
        quotes = await stock_api_service.get_multiple_quotes(symbols)
        
        enriched = []
        for investment in investments:
            quote = quotes.get(investment.symbol)
            
            # Usar precio actual o el precio promedio como fallback
            current_price = quote.price if quote else float(investment.average_price)
            change_percent = quote.change_percent if quote else 0.0
            day_change_per_share = quote.change if quote else 0.0
            
            # Cálculos
            shares = float(investment.shares)
            avg_price = float(investment.average_price)
            
            total_value = shares * current_price
            total_invested = shares * avg_price
            total_gain_loss = total_value - total_invested
            total_gain_loss_percent = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0
            day_change = shares * day_change_per_share
            
            enriched.append(EnrichedInvestment(
                id=investment.id,
                user_id=investment.user_id,
                symbol=investment.symbol,
                company_name=investment.company_name,
                shares=investment.shares,
                average_price=investment.average_price,
                purchase_date=investment.purchase_date,
                notes=investment.notes,
                created_at=investment.created_at,
                updated_at=investment.updated_at,
                current_price=current_price,
                change_percent=change_percent,
                total_value=total_value,
                total_gain_loss=total_gain_loss,
                total_gain_loss_percent=total_gain_loss_percent,
                day_change=day_change
            ))
        
        logger.info(f"Enriched {len(enriched)} investments with market data")
        return enriched
    
    @staticmethod
    def calculate_portfolio_summary(
        enriched_investments: List[EnrichedInvestment],
        cash_balance: float = 0.0
    ) -> PortfolioSummary:
        """
        Calcular resumen del portfolio

        Args:
            enriched_investments: Lista de inversiones enriquecidas
            cash_balance: Efectivo no invertido del usuario

        Returns:
            Resumen del portfolio
        """
        if not enriched_investments:
            return PortfolioSummary(
                total_value=round(cash_balance, 2),
                total_invested=0.0,
                total_gain_loss=0.0,
                total_gain_loss_percent=0.0,
                day_change=0.0,
                day_change_percent=0.0,
                positions_count=0,
                cash_balance=round(cash_balance, 2),
                invested_value=0.0
            )

        # invested_value es el valor actual de las posiciones
        invested_value = sum(inv.total_value for inv in enriched_investments)
        total_invested = sum(float(inv.shares) * float(inv.average_price) for inv in enriched_investments)

        # P&L se calcula solo sobre las posiciones (no incluye cash)
        total_gain_loss = invested_value - total_invested
        total_gain_loss_percent = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0
        day_change = sum(inv.day_change for inv in enriched_investments)

        # Valor del portfolio al inicio del día (solo posiciones)
        portfolio_yesterday = invested_value - day_change
        day_change_percent = (day_change / portfolio_yesterday * 100) if portfolio_yesterday > 0 else 0

        # total_value incluye cash + posiciones
        total_value = invested_value + cash_balance

        return PortfolioSummary(
            total_value=round(total_value, 2),
            total_invested=round(total_invested, 2),
            total_gain_loss=round(total_gain_loss, 2),
            total_gain_loss_percent=round(total_gain_loss_percent, 2),
            day_change=round(day_change, 2),
            day_change_percent=round(day_change_percent, 2),
            positions_count=len(enriched_investments),
            cash_balance=round(cash_balance, 2),
            invested_value=round(invested_value, 2)
        )
    
    @staticmethod
    def generate_insights(
        enriched_investments: List[EnrichedInvestment],
        summary: PortfolioSummary
    ) -> List[InvestmentInsight]:
        """
        Generar insights y recomendaciones
        
        Args:
            enriched_investments: Lista de inversiones enriquecidas
            summary: Resumen del portfolio
            
        Returns:
            Lista de insights
        """
        insights = []
        
        # Insight de diversificación
        if summary.positions_count < 5:
            insights.append(InvestmentInsight(
                type="warning",
                title="Baja Diversificación",
                message=f"Tienes solo {summary.positions_count} posición(es). Considera diversificar en al menos 5-10 empresas diferentes para reducir el riesgo.",
                icon="⚠️"
            ))
        else:
            insights.append(InvestmentInsight(
                type="success",
                title="Buena Diversificación",
                message=f"Tu cartera está diversificada con {summary.positions_count} posiciones.",
                icon="✅"
            ))
        
        # Insight de rendimiento
        if summary.total_gain_loss_percent > 10:
            insights.append(InvestmentInsight(
                type="success",
                title="Excelente Rendimiento",
                message=f"Tu cartera ha generado un +{summary.total_gain_loss_percent:.2f}% de ganancia.",
                icon="🚀"
            ))
        elif summary.total_gain_loss_percent < -10:
            insights.append(InvestmentInsight(
                type="danger",
                title="Pérdidas Significativas",
                message=f"Tu cartera tiene pérdidas del {summary.total_gain_loss_percent:.2f}%. Considera revisar tu estrategia.",
                icon="⚠️"
            ))
        
        # Insight de concentración
        if enriched_investments and summary.total_value > 0:
            max_position_value = max(inv.total_value for inv in enriched_investments)
            max_position_percent = (max_position_value / summary.total_value) * 100
            
            if max_position_percent > 30:
                insights.append(InvestmentInsight(
                    type="warning",
                    title="Alta Concentración",
                    message=f"Una de tus posiciones representa más del 30% de tu cartera. Considera rebalancear.",
                    icon="⚖️"
                ))
        
        logger.info(f"Generated {len(insights)} insights")
        return insights


# Instancia global del servicio
investment_service = InvestmentService()
