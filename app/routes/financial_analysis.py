"""
Financial Analysis Routes - Análisis Financiero Avanzado
=========================================================

Endpoints para análisis financiero avanzado incluyendo
cálculo de capacidad hipotecaria.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.security import get_current_user, check_rate_limit
from app.services.mortgage_capacity import (
    MortgageCapacityService,
    CalculationConfig
)
from app.schemas.mortgage_capacity import (
    MortgageCapacityResponse,
    TargetPriceResponse,
    FinancialProfileSummary,
    MortgageConfigRequest,
    TargetPriceRequest
)

router = APIRouter(prefix="/api/financial-analysis", tags=["financial-analysis"])


@router.get("/mortgage-capacity", response_model=MortgageCapacityResponse)
async def calculate_mortgage_capacity(
    months_to_analyze: int = Query(
        default=6,
        ge=3,
        le=24,
        description="Meses de histórico a analizar (3-24)"
    ),
    interest_rate: Optional[float] = Query(
        default=None,
        ge=0,
        le=0.20,
        description="Tasa de interés anual (ej: 0.03 = 3%). Default: 3%"
    ),
    years: Optional[int] = Query(
        default=None,
        ge=5,
        le=40,
        description="Plazo de la hipoteca en años. Default: 30"
    ),
    down_payment_ratio: Optional[float] = Query(
        default=None,
        ge=0,
        le=0.50,
        description="Porcentaje de entrada (ej: 0.20 = 20%). Default: 20%"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Calcula la capacidad hipotecaria del usuario.

    Analiza el perfil financiero del usuario basándose en sus transacciones
    históricas y determina:

    - **Precio máximo de vivienda** que puede permitirse
    - **Cuota mensual** recomendada
    - **Entrada requerida**
    - **Nivel de riesgo** financiero
    - **Escenarios alternativos** (conservador, equilibrado, agresivo)

    ## Metodología

    El cálculo considera:
    1. Ingresos promedio y su estabilidad
    2. Gastos fijos vs variables
    3. Deudas existentes
    4. Tasa de ahorro histórica

    ## Escenarios

    - **Conservative (25%)**: Máxima seguridad financiera
    - **Balanced (30%)**: Equilibrio razonable
    - **Aggressive (35%)**: Mayor riesgo, mayor vivienda

    ## Interpretación del Risk Score

    - **low**: Perfil financiero sólido
    - **medium**: Perfil aceptable con algunas consideraciones
    - **high**: Se recomienda mejorar situación antes de comprar
    """
    try:
        user_id = current_user.id
        service = MortgageCapacityService(db)

        # Construir configuración si hay parámetros personalizados
        config = None
        if any([interest_rate, years, down_payment_ratio]):
            config = CalculationConfig(
                interest_rate=interest_rate or 0.03,
                years=years or 30,
                down_payment_ratio=down_payment_ratio or 0.20
            )

        result = await service.calculate_mortgage_capacity(
            user_id=user_id,
            config=config,
            months_to_analyze=months_to_analyze
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Parámetros inválidos: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular capacidad hipotecaria: {str(e)}"
        )


@router.post("/mortgage-capacity", response_model=MortgageCapacityResponse)
async def calculate_mortgage_capacity_with_config(
    config: MortgageConfigRequest = Body(
        ...,
        description="Configuración personalizada para el cálculo"
    ),
    months_to_analyze: int = Query(
        default=6,
        ge=3,
        le=24,
        description="Meses de histórico a analizar"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Calcula la capacidad hipotecaria con configuración personalizada.

    Similar al endpoint GET pero permite configurar todos los parámetros
    a través del body de la solicitud.

    ## Configuración

    - `interest_rate`: Tasa de interés anual (0-20%)
    - `years`: Plazo en años (5-40)
    - `down_payment_ratio`: Porcentaje de entrada (0-50%)
    - `max_debt_ratio`: Ratio máximo deuda/ingresos (20-50%)
    - `safety_margin`: Margen de seguridad adicional (0-30%)
    """
    try:
        user_id = current_user.id
        service = MortgageCapacityService(db)

        # Convertir request a CalculationConfig
        calc_config = CalculationConfig(
            interest_rate=config.interest_rate,
            years=config.years,
            down_payment_ratio=config.down_payment_ratio,
            max_debt_ratio=config.max_debt_ratio,
            safety_margin=config.safety_margin
        )

        result = await service.calculate_mortgage_capacity(
            user_id=user_id,
            config=calc_config,
            months_to_analyze=months_to_analyze
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Configuración inválida: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular capacidad hipotecaria: {str(e)}"
        )


@router.post("/mortgage-capacity/target-price", response_model=TargetPriceResponse)
async def analyze_target_price(
    request: TargetPriceRequest = Body(
        ...,
        description="Precio objetivo y configuración opcional"
    ),
    months_to_analyze: int = Query(
        default=6,
        ge=3,
        le=24,
        description="Meses de histórico a analizar"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Analiza la viabilidad de un precio objetivo de vivienda.

    Responde a la pregunta: "¿Puedo permitirme una casa de X euros?"

    ## Análisis

    Calcula:
    - Si el precio objetivo es alcanzable con el perfil actual
    - Cuánto falta (o sobra) respecto a la cuota máxima
    - Qué ratio de deuda resultaría
    - Recomendación personalizada

    ## Comparación

    Incluye comparación con la capacidad máxima calculada:
    - Diferencia en euros
    - Porcentaje respecto al máximo

    ## Recomendaciones

    - Si viable: Consejos sobre el nivel de riesgo
    - Si no viable: Sugerencias para alcanzar el objetivo
    """
    try:
        user_id = current_user.id
        service = MortgageCapacityService(db)

        # Convertir configuración si existe
        config = None
        if request.config:
            config = CalculationConfig(
                interest_rate=request.config.interest_rate,
                years=request.config.years,
                down_payment_ratio=request.config.down_payment_ratio,
                max_debt_ratio=request.config.max_debt_ratio,
                safety_margin=request.config.safety_margin
            )

        result = await service.calculate_for_target_price(
            user_id=user_id,
            target_price=request.target_price,
            config=config,
            months_to_analyze=months_to_analyze
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Parámetros inválidos: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al analizar precio objetivo: {str(e)}"
        )


@router.get("/financial-profile", response_model=FinancialProfileSummary)
async def get_financial_profile_summary(
    months_to_analyze: int = Query(
        default=6,
        ge=3,
        le=24,
        description="Meses de histórico a analizar"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    Obtiene un resumen del perfil financiero del usuario.

    Proporciona una vista general de la situación financiera incluyendo:

    - **Ingresos**: Promedio mensual y estabilidad
    - **Gastos**: Desglose entre fijos y variables
    - **Deudas**: Pagos actuales de deuda
    - **Capacidad**: Ingreso disponible después de gastos
    - **Ahorro**: Tasa de ahorro histórica
    - **Salud**: Evaluación general de salud financiera

    ## Health Status

    - **excellent**: Tasa de ahorro > 20%
    - **good**: Tasa de ahorro 10-20%
    - **fair**: Tasa de ahorro 5-10%
    - **needs_improvement**: Tasa de ahorro 0-5%
    - **critical**: Sin capacidad de ahorro

    Este endpoint es útil para mostrar un dashboard de situación
    financiera antes de calcular la capacidad hipotecaria.
    """
    try:
        user_id = current_user.id
        service = MortgageCapacityService(db)

        result = await service.get_financial_profile_summary(
            user_id=user_id,
            months=months_to_analyze
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener perfil financiero: {str(e)}"
        )
