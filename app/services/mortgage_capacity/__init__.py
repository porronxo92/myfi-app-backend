"""
Mortgage Capacity Module
========================

Módulo para el cálculo de capacidad hipotecaria del usuario.
Analiza el perfil financiero y determina el precio máximo de vivienda
que el usuario puede permitirse.

Componentes:
- models: FinancialProfile, CalculationConfig
- calculator: MortgageCapacityCalculator
- service: Orquestación y obtención de datos
"""

from .models import FinancialProfile, CalculationConfig
from .calculator import MortgageCapacityCalculator
from .service import MortgageCapacityService

__all__ = [
    "FinancialProfile",
    "CalculationConfig",
    "MortgageCapacityCalculator",
    "MortgageCapacityService"
]
