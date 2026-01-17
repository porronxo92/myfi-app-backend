"""
Servicio de lógica de negocio para presupuestos
"""

from sqlalchemy.orm import Session
from sqlalchemy import extract, and_, func as sql_func
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
import uuid

from app.models.budget import Budget
from app.models.budget_item import BudgetItem
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.budget import (
    BudgetProgress, ItemProgress, BudgetSummary,
    OverspentCategory, SuggestedBudget, SuggestedBudgetItem,
    BudgetComparison, CategoryComparison
)


def calculate_budget_progress(db: Session, budget_id: uuid.UUID) -> BudgetProgress:
    """
    Calcula el progreso completo de un presupuesto
    
    Args:
        db: Sesión de base de datos
        budget_id: ID del presupuesto
        
    Returns:
        BudgetProgress con todos los datos calculados
    """
    # Obtener el presupuesto
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise ValueError("Presupuesto no encontrado")
    
    items_progress = []
    total_spent = Decimal(0)
    total_allocated = Decimal(0)
    
    # Calcular progreso de cada partida
    for item in budget.items:
        spent = item.calculate_spent_amount(db)
        remaining = item.get_remaining_amount(db)
        percent_used = item.get_consumption_percent(db)
        status = item.get_status(db)
        
        # Contar transacciones de esta categoría en el período
        # JOIN con Account para filtrar por user_id
        from app.models.account import Account
        transaction_count = db.query(sql_func.count(Transaction.id)).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            and_(
                Transaction.category_id == item.category_id,
                Account.user_id == budget.user_id,
                extract('month', Transaction.date) == budget.month,
                extract('year', Transaction.date) == budget.year,
                Transaction.type == 'expense'
            )
        ).scalar()
        
        items_progress.append(ItemProgress(
            id=item.id,
            category_id=item.category_id,
            category_name=item.category.name,
            allocated=item.allocated_amount,
            spent=spent,
            remaining=remaining,
            percent_used=round(percent_used, 2),
            status=status,
            transaction_count=transaction_count or 0
        ))
        
        total_spent += spent
        total_allocated += item.allocated_amount
    
    # Calcular totales
    total_remaining = total_allocated - total_spent
    percent_used = float((total_spent / total_allocated) * 100) if total_allocated > 0 else 0.0
    
    # Determinar estado general
    if percent_used >= 100:
        status = 'over'
    elif percent_used >= 80:
        status = 'warning'
    else:
        status = 'ok'
    
    return BudgetProgress(
        budget_id=budget.id,
        month=budget.month,
        year=budget.year,
        total_allocated=total_allocated,
        total_spent=total_spent,
        total_remaining=total_remaining,
        percent_used=round(percent_used, 2),
        status=status,
        items=items_progress
    )


def get_budget_summary(db: Session, budget_id: uuid.UUID) -> BudgetSummary:
    """
    Genera un resumen ejecutivo del presupuesto
    
    Args:
        db: Sesión de base de datos
        budget_id: ID del presupuesto
        
    Returns:
        BudgetSummary con análisis del presupuesto
    """
    progress = calculate_budget_progress(db, budget_id)
    
    overspent_categories = []
    categories_at_risk = []
    categories_ok = []
    
    for item in progress.items:
        if item.status == 'over':
            overspent_categories.append(item.category_name)
        elif item.status == 'warning':
            categories_at_risk.append(item.category_name)
        else:
            categories_ok.append(item.category_name)
    
    return BudgetSummary(
        budget_id=progress.budget_id,
        month=progress.month,
        year=progress.year,
        total_allocated=progress.total_allocated,
        total_spent=progress.total_spent,
        total_remaining=progress.total_remaining,
        percent_used=progress.percent_used,
        status=progress.status,
        overspent_categories=overspent_categories,
        categories_at_risk=categories_at_risk,
        categories_ok=categories_ok
    )


def get_overspent_categories(db: Session, budget_id: uuid.UUID) -> List[OverspentCategory]:
    """
    Identifica las categorías que han superado su presupuesto
    
    Args:
        db: Sesión de base de datos
        budget_id: ID del presupuesto
        
    Returns:
        Lista de OverspentCategory ordenada por mayor desviación
    """
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise ValueError("Presupuesto no encontrado")
    
    overspent = []
    
    for item in budget.items:
        spent = item.calculate_spent_amount(db)
        
        if spent > item.allocated_amount:
            overspent_amount = spent - item.allocated_amount
            percent_over = float((overspent_amount / item.allocated_amount) * 100) if item.allocated_amount > 0 else 0.0
            
            overspent.append(OverspentCategory(
                category_id=item.category_id,
                category_name=item.category.name,
                allocated=item.allocated_amount,
                spent=spent,
                overspent_amount=overspent_amount,
                percent_over=round(percent_over, 2)
            ))
    
    # Ordenar por mayor desviación
    overspent.sort(key=lambda x: x.overspent_amount, reverse=True)
    
    return overspent


def suggest_budget_from_history(
    db: Session,
    user_id: uuid.UUID,
    target_month: int,
    target_year: int,
    months_back: int = 3
) -> SuggestedBudget:
    """
    Sugiere un presupuesto basado en el histórico de gastos del usuario
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        target_month: Mes para el que se sugiere el presupuesto
        target_year: Año para el que se sugiere el presupuesto
        months_back: Número de meses hacia atrás a analizar
        
    Returns:
        SuggestedBudget con partidas sugeridas
    """
    from datetime import date, timedelta
    from calendar import monthrange
    
    # Calcular el rango de fechas a analizar
    # Último día del mes anterior al target
    if target_month == 1:
        prev_month = 12
        prev_year = target_year - 1
    else:
        prev_month = target_month - 1
        prev_year = target_year
    
    _, last_day = monthrange(prev_year, prev_month)
    end_date = date(prev_year, prev_month, last_day)
    
    # Calcular inicio basado en months_back
    start_year = target_year
    start_month = target_month - months_back
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    
    start_date = date(start_year, start_month, 1)
    
    # Obtener todas las categorías de gasto usadas por el usuario
    # JOIN con Account para filtrar por user_id
    from app.models.account import Account
    categories_with_spending = db.query(
        Transaction.category_id,
        Category.name,
        sql_func.avg(Transaction.amount).label('avg_amount'),
        sql_func.sum(Transaction.amount).label('total_amount')
    ).join(
        Category, Transaction.category_id == Category.id
    ).join(
        Account, Transaction.account_id == Account.id
    ).filter(
        and_(
            Account.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= start_date,
            Transaction.date <= end_date
        )
    ).group_by(
        Transaction.category_id,
        Category.name
    ).all()
    
    suggested_items = []
    total_suggested = Decimal(0)
    
    for cat_id, cat_name, avg_amount, total_amount in categories_with_spending:
        # Calcular promedio mensual
        suggested_amount = Decimal(str(abs(avg_amount)))
        
        suggested_items.append(SuggestedBudgetItem(
            category_id=cat_id,
            category_name=cat_name,
            suggested_amount=suggested_amount,
            based_on_average=suggested_amount,
            months_analyzed=months_back
        ))
        
        total_suggested += suggested_amount
    
    # Ordenar por monto sugerido (mayor a menor)
    suggested_items.sort(key=lambda x: x.suggested_amount, reverse=True)
    
    month_names = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    return SuggestedBudget(
        suggested_for_month=target_month,
        suggested_for_year=target_year,
        total_suggested=total_suggested,
        items=suggested_items,
        analysis_period=f"Últimos {months_back} meses"
    )


def compare_budgets(db: Session, budget_id_1: uuid.UUID, budget_id_2: uuid.UUID) -> BudgetComparison:
    """
    Compara dos presupuestos del usuario
    
    Args:
        db: Sesión de base de datos
        budget_id_1: ID del primer presupuesto
        budget_id_2: ID del segundo presupuesto
        
    Returns:
        BudgetComparison con las diferencias
    """
    budget1 = db.query(Budget).filter(Budget.id == budget_id_1).first()
    budget2 = db.query(Budget).filter(Budget.id == budget_id_2).first()
    
    if not budget1 or not budget2:
        raise ValueError("Uno o ambos presupuestos no encontrados")
    
    if budget1.user_id != budget2.user_id:
        raise ValueError("Los presupuestos deben pertenecer al mismo usuario")
    
    month_names = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    budget1_period = f"{month_names[budget1.month]} {budget1.year}"
    budget2_period = f"{month_names[budget2.month]} {budget2.year}"
    
    # Crear diccionario de categorías de ambos presupuestos
    budget1_items = {item.category_id: item.allocated_amount for item in budget1.items}
    budget2_items = {item.category_id: item.allocated_amount for item in budget2.items}
    
    # Obtener todas las categorías únicas
    all_categories = set(budget1_items.keys()) | set(budget2_items.keys())
    
    category_comparisons = []
    
    for cat_id in all_categories:
        category = db.query(Category).filter(Category.id == cat_id).first()
        if not category:
            continue
        
        amount1 = budget1_items.get(cat_id, Decimal(0))
        amount2 = budget2_items.get(cat_id, Decimal(0))
        difference = amount2 - amount1
        
        if amount1 > 0:
            percent_change = float((difference / amount1) * 100)
        else:
            percent_change = 100.0 if amount2 > 0 else 0.0
        
        category_comparisons.append(CategoryComparison(
            category_name=category.name,
            budget1_amount=amount1,
            budget2_amount=amount2,
            difference=difference,
            percent_change=round(percent_change, 2)
        ))
    
    # Ordenar por mayor diferencia absoluta
    category_comparisons.sort(key=lambda x: abs(x.difference), reverse=True)
    
    total_difference = budget2.total_budget - budget1.total_budget
    
    return BudgetComparison(
        budget1_id=budget1.id,
        budget1_period=budget1_period,
        budget2_id=budget2.id,
        budget2_period=budget2_period,
        total_difference=total_difference,
        categories=category_comparisons
    )
