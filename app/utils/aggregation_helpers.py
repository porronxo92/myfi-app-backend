"""
Utilidades de Agregación para Campos Encriptados
==================================================

Este módulo proporciona funciones de agregación que operan sobre datos
desencriptados en Python, ya que los campos financieros (amount, balance)
están encriptados con AES-256-GCM y no permiten operaciones SQL.

IMPORTANTE: Estas funciones cargan datos en memoria. Para datasets grandes
(>10,000 registros por usuario), considerar estrategias de caching o paginación.
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import date, datetime
from decimal import Decimal
from collections import defaultdict
from uuid import UUID


def sum_amounts(transactions: list, condition: Optional[Callable] = None) -> Decimal:
    """
    Suma montos de transacciones (con condición opcional).
    
    Args:
        transactions: Lista de objetos Transaction
        condition: Función opcional para filtrar (lambda t: t.type == 'income')
    
    Returns:
        Decimal: Suma total de montos
    
    Example:
        total_income = sum_amounts(transactions, lambda t: t.type == 'income')
    """
    total = Decimal("0.00")
    
    for t in transactions:
        if condition is None or condition(t):
            amount = t.amount if t.amount is not None else Decimal("0.00")
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
            total += amount
    
    return total


def sum_absolute_amounts(transactions: list, condition: Optional[Callable] = None) -> Decimal:
    """
    Suma valores absolutos de montos (útil para gastos).
    
    Args:
        transactions: Lista de objetos Transaction
        condition: Función opcional para filtrar
    
    Returns:
        Decimal: Suma total de |amount|
    """
    total = Decimal("0.00")
    
    for t in transactions:
        if condition is None or condition(t):
            amount = t.amount if t.amount is not None else Decimal("0.00")
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
            total += abs(amount)
    
    return total


def group_by_category(
    transactions: list,
    category_getter: Callable = lambda t: t.category.name if t.category else "Sin categoría",
    include_color: bool = True
) -> List[Dict[str, Any]]:
    """
    Agrupa transacciones por categoría con totales.
    
    Args:
        transactions: Lista de objetos Transaction
        category_getter: Función para obtener nombre de categoría
        include_color: Incluir color de la categoría
    
    Returns:
        Lista de diccionarios con 'category', 'total', 'count', 'color'
    """
    groups = defaultdict(lambda: {"total": Decimal("0.00"), "count": 0, "color": None})
    
    for t in transactions:
        category_name = category_getter(t)
        amount = t.amount if t.amount is not None else Decimal("0.00")
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        groups[category_name]["total"] += abs(amount)
        groups[category_name]["count"] += 1
        
        if include_color and t.category:
            groups[category_name]["color"] = t.category.color
    
    # Convertir a lista ordenada por total (descendente)
    result = [
        {
            "category": name,
            "total": float(data["total"]),
            "count": data["count"],
            "color": data["color"]
        }
        for name, data in groups.items()
    ]
    
    result.sort(key=lambda x: x["total"], reverse=True)
    return result


def group_by_month(
    transactions: list,
    value_getter: Callable = lambda t: abs(float(t.amount)) if t.amount else 0.0,
    aggregator: str = "sum"  # "sum", "avg", "count"
) -> Dict[str, Any]:
    """
    Agrupa transacciones por mes.
    
    Args:
        transactions: Lista de objetos Transaction
        value_getter: Función para extraer valor (default: |amount|)
        aggregator: Tipo de agregación ("sum", "avg", "count")
    
    Returns:
        Diccionario {month_key: aggregated_value}
    """
    groups = defaultdict(list)
    
    for t in transactions:
        if t.date:
            month_key = t.date.strftime("%Y-%m")
            groups[month_key].append(value_getter(t))
    
    result = {}
    for month_key, values in sorted(groups.items()):
        if aggregator == "sum":
            result[month_key] = sum(values)
        elif aggregator == "avg":
            result[month_key] = sum(values) / len(values) if values else 0.0
        elif aggregator == "count":
            result[month_key] = len(values)
        else:
            result[month_key] = sum(values)
    
    return result


def group_by_description(
    transactions: list,
    min_occurrences: int = 1
) -> List[Dict[str, Any]]:
    """
    Agrupa transacciones por descripción (merchant detection).
    
    Args:
        transactions: Lista de objetos Transaction
        min_occurrences: Mínimo de ocurrencias para incluir
    
    Returns:
        Lista de diccionarios con 'description', 'total', 'count', 'avg'
    """
    groups = defaultdict(lambda: {"total": Decimal("0.00"), "count": 0, "amounts": []})
    
    for t in transactions:
        desc = t.description if t.description else "Sin descripción"
        amount = t.amount if t.amount is not None else Decimal("0.00")
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        groups[desc]["total"] += abs(amount)
        groups[desc]["count"] += 1
        groups[desc]["amounts"].append(float(abs(amount)))
    
    # Filtrar por mínimo de ocurrencias y calcular promedios
    result = []
    for desc, data in groups.items():
        if data["count"] >= min_occurrences:
            avg = data["total"] / data["count"]
            result.append({
                "description": desc,
                "total": float(data["total"]),
                "count": data["count"],
                "avg": float(avg)
            })
    
    result.sort(key=lambda x: x["total"], reverse=True)
    return result


def calculate_summary(
    transactions: list,
    accounts: list = None
) -> Dict[str, Any]:
    """
    Calcula resumen financiero completo.
    
    Args:
        transactions: Lista de objetos Transaction
        accounts: Lista de objetos Account (para balance total)
    
    Returns:
        Diccionario con métricas financieras
    """
    total_income = sum_amounts(transactions, lambda t: t.type == 'income')
    total_expenses = sum_absolute_amounts(transactions, lambda t: t.type == 'expense')
    
    net_balance = float(total_income) - float(total_expenses)
    savings_rate = (net_balance / float(total_income) * 100) if float(total_income) > 0 else 0
    
    total_balance = Decimal("0.00")
    if accounts:
        for acc in accounts:
            balance = acc.balance if acc.balance is not None else Decimal("0.00")
            if not isinstance(balance, Decimal):
                balance = Decimal(str(balance))
            total_balance += balance
    
    return {
        "total_income": float(total_income),
        "total_expenses": float(total_expenses),
        "net_balance": net_balance,
        "savings_rate": round(savings_rate, 2),
        "total_balance": float(total_balance),
        "num_transactions": len(transactions)
    }


def filter_by_amount_range(
    transactions: list,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None
) -> list:
    """
    Filtra transacciones por rango de monto.
    
    Args:
        transactions: Lista de objetos Transaction
        min_amount: Monto mínimo (inclusive)
        max_amount: Monto máximo (inclusive)
    
    Returns:
        Lista filtrada de transacciones
    """
    result = []
    
    for t in transactions:
        amount = float(t.amount) if t.amount is not None else 0.0
        
        if min_amount is not None and amount < min_amount:
            continue
        if max_amount is not None and amount > max_amount:
            continue
        
        result.append(t)
    
    return result


def detect_anomalies(
    transactions: list,
    z_threshold: float = 2.0
) -> List[Dict[str, Any]]:
    """
    Detecta transacciones anómalas usando z-score.
    
    Args:
        transactions: Lista de objetos Transaction
        z_threshold: Umbral de z-score para considerar anomalía
    
    Returns:
        Lista de transacciones anómalas con razón
    """
    if len(transactions) < 3:
        return []
    
    import statistics
    
    amounts = [abs(float(t.amount)) for t in transactions if t.amount is not None]
    
    if len(amounts) < 2:
        return []
    
    mean = statistics.mean(amounts)
    stdev = statistics.stdev(amounts) if len(amounts) > 1 else 0
    
    if stdev == 0:
        return []
    
    anomalies = []
    for t in transactions:
        if t.amount is None:
            continue
        
        amount = abs(float(t.amount))
        z_score = (amount - mean) / stdev
        
        if abs(z_score) >= z_threshold:
            anomalies.append({
                "id": str(t.id),
                "date": t.date.isoformat() if t.date else None,
                "description": t.description,
                "amount": float(t.amount),
                "type": t.type,
                "category": t.category.name if t.category else None,
                "z_score": round(z_score, 2),
                "reason": f"{'Alto' if z_score > 0 else 'Bajo'} comparado con media ({round(mean, 2)})"
            })
    
    return anomalies


def detect_recurring(
    transactions: list,
    min_occurrences: int = 2,
    amount_tolerance: float = 0.10  # 10% de variación
) -> List[Dict[str, Any]]:
    """
    Detecta gastos recurrentes (suscripciones).
    
    Args:
        transactions: Lista de objetos Transaction
        min_occurrences: Mínimo de apariciones para ser recurrente
        amount_tolerance: Tolerancia de variación en monto
    
    Returns:
        Lista de gastos recurrentes
    """
    # Agrupar por descripción similar
    groups = defaultdict(list)
    
    for t in transactions:
        if t.type != 'expense' or t.amount is None:
            continue
        
        desc = t.description.lower().strip() if t.description else ""
        groups[desc].append(t)
    
    recurring = []
    
    for desc, txns in groups.items():
        if len(txns) < min_occurrences:
            continue
        
        amounts = [abs(float(t.amount)) for t in txns]
        avg_amount = sum(amounts) / len(amounts)
        
        # Verificar si los montos son similares (dentro del tolerance)
        all_similar = all(
            abs(a - avg_amount) / avg_amount <= amount_tolerance
            for a in amounts
        ) if avg_amount > 0 else False
        
        if all_similar:
            dates = sorted([t.date for t in txns if t.date])
            
            # Calcular frecuencia aproximada
            if len(dates) >= 2:
                days_diff = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                avg_days = sum(days_diff) / len(days_diff)
                
                if avg_days <= 7:
                    frequency = "weekly"
                elif avg_days <= 15:
                    frequency = "bi-weekly"
                elif avg_days <= 35:
                    frequency = "monthly"
                elif avg_days <= 95:
                    frequency = "quarterly"
                else:
                    frequency = "annual"
            else:
                frequency = "unknown"
            
            recurring.append({
                "description": txns[0].description,
                "category": txns[0].category.name if txns[0].category else None,
                "avg_amount": round(avg_amount, 2),
                "frequency": frequency,
                "occurrences": len(txns),
                "last_date": dates[-1].isoformat() if dates else None,
                "annual_cost": round(avg_amount * 12, 2) if frequency == "monthly" else round(avg_amount * len(txns), 2)
            })
    
    recurring.sort(key=lambda x: x["annual_cost"], reverse=True)
    return recurring
