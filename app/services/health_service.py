"""
Health Service
==============

Servicio para generar informes de salud financiera usando Gemini AI.
"""

import logging
import json
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from datetime import datetime, date
from uuid import UUID

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.config import settings

logger = logging.getLogger(__name__)


async def generate_health_report(
    db: Session,
    user_id: str,
    year: int,
    account_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genera un informe completo de salud financiera usando Gemini AI.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        year: Año a analizar
        account_id: ID de cuenta específica (opcional)
    
    Returns:
        Dict con el informe de salud financiera
    """
    logger.info(f"Generando informe de salud para user_id={user_id}, year={year}")
    
    # 1. Recopilar datos financieros
    user_data = await collect_user_financial_data(db, user_id, year, account_id)
    
    # 2. Generar prompt para Gemini
    prompt = generate_health_analysis_prompt(user_data)
    
    # LOG: Mostrar el prompt completo que se enviará a Gemini
    logger.info("=" * 80)
    logger.info("📤 PROMPT ENVIADO A GEMINI:")
    logger.info("=" * 80)
    logger.info(prompt)
    logger.info("=" * 80)
    
    # 3. Llamar a Gemini (por ahora retorna datos mock)
    try:
        gemini_response = await call_gemini_api(prompt)
        
        # LOG: Mostrar la respuesta de Gemini
        logger.info("=" * 80)
        logger.info("📥 RESPUESTA RECIBIDA DE GEMINI:")
        logger.info("=" * 80)
        logger.info(gemini_response)
        logger.info("=" * 80)
        
        health_report = json.loads(gemini_response)
        logger.info("✅ Respuesta de Gemini parseada exitosamente")
    except Exception as e:
        logger.warning(f"⚠️ Error llamando a Gemini, usando análisis local: {str(e)}")
        # Fallback: generar análisis local
        health_report = generate_local_health_analysis(user_data)
        
        # LOG: Mostrar que se está usando análisis local
        logger.info("=" * 80)
        logger.info("🔄 USANDO ANÁLISIS LOCAL (FALLBACK):")
        logger.info("=" * 80)
        logger.info(json.dumps(health_report, indent=2, ensure_ascii=False))
        logger.info("=" * 80)
    
    # 4. Validar estructura
    validate_health_report(health_report)
    
    return health_report


async def collect_user_financial_data(
    db: Session,
    user_id: str,
    year: int,
    account_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Recopila todos los datos financieros necesarios para el análisis.
    """
    user_uuid = UUID(user_id)
    account_uuid = UUID(account_id) if account_id else None
    
    # Información de cuentas
    accounts_query = db.query(Account).filter(Account.user_id == user_uuid)
    if account_uuid:
        accounts_query = accounts_query.filter(Account.id == account_uuid)
    accounts = accounts_query.all()
    
    # Balance inicial (31 dic año anterior)
    initial_balance = get_initial_balance(db, user_uuid, year, account_uuid)
    
    # Balance actual
    current_balance = sum([float(a.balance) for a in accounts])
    
    # Desglose detallado de cuentas con número de movimientos
    accounts_detail = []
    for account in accounts:
        # Contar movimientos del año para esta cuenta
        transaction_count = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.account_id == account.id,
                extract('year', Transaction.date) == year
            )
        ).scalar() or 0
        
        accounts_detail.append({
            'name': account.name,
            'bank': account.bank_name or 'No especificado',
            'type': account.type,
            'balance': float(account.balance),
            'currency': account.currency,
            'transaction_count': transaction_count,
            'is_active': account.is_active
        })
    
    # Resumen anual
    annual_summary = calculate_annual_summary(db, user_uuid, year, account_uuid)
    
    # Desglose mensual
    monthly_breakdown = calculate_monthly_breakdown(db, user_uuid, year, account_uuid)
    
    # Top categorías
    top_categories = get_top_categories(db, user_uuid, year, account_uuid)
    
    # Gastos recurrentes
    recurring_expenses = detect_recurring_expenses(db, user_uuid, year, account_uuid)
    
    # Anomalías
    anomalies = detect_anomalies(db, user_uuid, year, account_uuid)
    
    return {
        'year': year,
        'account_info': {
            'total_accounts': len(accounts),
            'account_names': ', '.join([a.name for a in accounts]) if account_uuid else 'Todas las cuentas',
            'current_balance': current_balance,
            'initial_balance': initial_balance
        },
        'accounts_detail': accounts_detail,
        'annual_summary': annual_summary,
        'monthly_breakdown': monthly_breakdown,
        'top_categories': top_categories,
        'recurring_expenses': recurring_expenses,
        'anomalies': anomalies
    }


def get_initial_balance(db: Session, user_id: UUID, year: int, account_id: Optional[UUID] = None) -> float:
    """Calcula el balance al final del año anterior."""
    end_of_previous_year = date(year - 1, 12, 31)
    
    # Obtener cuentas del usuario
    accounts_query = db.query(Account).filter(Account.user_id == user_id)
    if account_id:
        accounts_query = accounts_query.filter(Account.id == account_id)
    accounts = accounts_query.all()
    account_ids = [acc.id for acc in accounts]
    
    if not account_ids:
        return 0.0
    
    query = db.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.account_id.in_(account_ids),
            Transaction.date <= end_of_previous_year
        )
    )
    
    total = query.scalar()
    return float(total) if total else 0.0


def calculate_annual_summary(db: Session, user_id: UUID, year: int, account_id: Optional[UUID] = None) -> Dict:
    """Calcula el resumen anual."""
    # Obtener cuentas del usuario
    accounts_query = db.query(Account).filter(Account.user_id == user_id)
    if account_id:
        accounts_query = accounts_query.filter(Account.id == account_id)
    accounts = accounts_query.all()
    account_ids = [acc.id for acc in accounts]
    
    if not account_ids:
        return {
            'total_income': 0.0,
            'total_expenses': 0.0,
            'net_balance': 0.0,
            'avg_savings_rate': 0.0,
            'months_with_data': 0,
            'balance_change': 0.0,
            'balance_change_percent': 0.0
        }
    
    # Total ingresos
    total_income = db.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.account_id.in_(account_ids),
            extract('year', Transaction.date) == year,
            Transaction.type == 'income'
        )
    ).scalar() or 0
    
    # Total gastos
    total_expenses = db.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.account_id.in_(account_ids),
            extract('year', Transaction.date) == year,
            Transaction.type == 'expense'
        )
    ).scalar() or 0
    
    # Meses con datos
    months_with_data = db.query(func.count(func.distinct(extract('month', Transaction.date)))).filter(
        and_(
            Transaction.account_id.in_(account_ids),
            extract('year', Transaction.date) == year
        )
    ).scalar() or 0
    
    net_balance = float(total_income) - abs(float(total_expenses))
    avg_savings_rate = (net_balance / float(total_income) * 100) if total_income > 0 else 0
    
    return {
        'total_income': float(total_income),
        'total_expenses': abs(float(total_expenses)),
        'net_balance': net_balance,
        'avg_savings_rate': avg_savings_rate,
        'months_with_data': months_with_data,
        'balance_change': net_balance,
        'balance_change_percent': (net_balance / float(total_income) * 100) if total_income > 0 else 0
    }


def calculate_monthly_breakdown(db: Session, user_id: UUID, year: int, account_id: Optional[UUID] = None) -> List[Dict]:
    """Calcula el desglose mensual."""
    # Obtener cuentas del usuario
    accounts_query = db.query(Account).filter(Account.user_id == user_id)
    if account_id:
        accounts_query = accounts_query.filter(Account.id == account_id)
    accounts = accounts_query.all()
    account_ids = [acc.id for acc in accounts]
    
    monthly_data = []
    
    for month in range(1, 13):
        if not account_ids:
            monthly_data.append({
                'month': month,
                'income': 0.0,
                'expenses': 0.0,
                'balance': 0.0,
                'savings_rate': 0.0
            })
            continue
        
        # Ingresos del mes
        income = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.account_id.in_(account_ids),
                extract('year', Transaction.date) == year,
                extract('month', Transaction.date) == month,
                Transaction.type == 'income'
            )
        ).scalar() or 0
        
        # Gastos del mes
        expenses = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.account_id.in_(account_ids),
                extract('year', Transaction.date) == year,
                extract('month', Transaction.date) == month,
                Transaction.type == 'expense'
            )
        ).scalar() or 0
        
        income_val = float(income)
        expenses_val = abs(float(expenses))
        balance = income_val - expenses_val
        savings_rate = (balance / income_val * 100) if income_val > 0 else 0
        
        monthly_data.append({
            'month': month,
            'income': income_val,
            'expenses': expenses_val,
            'balance': balance,
            'savings_rate': savings_rate
        })
    
    return monthly_data


def get_top_categories(db: Session, user_id: UUID, year: int, account_id: Optional[UUID] = None) -> Dict:
    """Obtiene las categorías principales."""
    # Obtener cuentas del usuario
    accounts_query = db.query(Account).filter(Account.user_id == user_id)
    if account_id:
        accounts_query = accounts_query.filter(Account.id == account_id)
    accounts = accounts_query.all()
    account_ids = [acc.id for acc in accounts]
    
    if not account_ids:
        return {'expenses': []}
    
    # Top gastos
    expenses_query = db.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).join(
        Transaction, Transaction.category_id == Category.id
    ).filter(
        and_(
            Transaction.account_id.in_(account_ids),
            extract('year', Transaction.date) == year,
            Transaction.type == 'expense'
        )
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).limit(5)
    
    expenses_results = expenses_query.all()
    total_expenses = sum([abs(float(r.total)) for r in expenses_results])
    
    expenses_categories = [
        {
            'category': r.name,
            'total': abs(float(r.total)),
            'percentage': (abs(float(r.total)) / total_expenses * 100) if total_expenses > 0 else 0
        }
        for r in expenses_results
    ]
    
    return {
        'expenses': expenses_categories
    }


def detect_recurring_expenses(db: Session, user_id: UUID, year: int, account_id: Optional[UUID] = None) -> List[Dict]:
    """Detecta gastos recurrentes (placeholder)."""
    # TODO: Implementar lógica real de detección de gastos recurrentes
    return []


def detect_anomalies(db: Session, user_id: UUID, year: int, account_id: Optional[UUID] = None) -> List[Dict]:
    """Detecta anomalías en transacciones (placeholder)."""
    # TODO: Implementar detección de anomalías
    return []


def generate_health_analysis_prompt(user_data: Dict) -> str:
    """
    Genera el prompt optimizado para Gemini con los datos financieros del usuario.
    """
    year = user_data.get('year')
    account_info = user_data.get('account_info', {})
    accounts_detail = user_data.get('accounts_detail', [])
    annual_summary = user_data.get('annual_summary', {})
    monthly_breakdown = user_data.get('monthly_breakdown', [])
    top_categories = user_data.get('top_categories', {})
    recurring_expenses = user_data.get('recurring_expenses', [])
    anomalies = user_data.get('anomalies', [])
    
    prompt = f"""Eres un asesor financiero personal experto, empático y analítico.

Tu tarea es analizar la salud financiera del usuario para el año {year} y generar un informe completo en formato JSON. 

═══════════════════════════════════════════════════════════════════════
📊 DATOS FINANCIEROS DEL USUARIO - AÑO {year}
═══════════════════════════════════════════════════════════════════════

🏦 INFORMACIÓN GENERAL DE CUENTAS:
- Número de cuentas activas: {account_info.get('total_accounts', 0)}
- Cuenta(s) analizada(s): {account_info.get('account_names', 'Todas las cuentas')}
- Balance total actual: €{account_info.get('current_balance', 0):.2f}
- Balance inicial (1 enero {year}): €{account_info.get('initial_balance', 0):.2f}

💳 DESGLOSE DETALLADO DE CUENTAS:
{_format_accounts_detail(accounts_detail)}

💰 RESUMEN ANUAL ({year}):
- Total ingresos acumulados: €{annual_summary.get('total_income', 0):.2f}
- Total gastos acumulados: €{annual_summary.get('total_expenses', 0):.2f}
- Balance neto del año: €{annual_summary.get('net_balance', 0):.2f}
- Tasa de ahorro promedio: {annual_summary.get('avg_savings_rate', 0):.1f}%
- Meses con datos: {annual_summary.get('months_with_data', 0)} de 12

📈 DESGLOSE MENSUAL:
{_format_monthly_breakdown(monthly_breakdown)}

🏷️ TOP 5 CATEGORÍAS DE GASTO:
{_format_top_categories(top_categories.get('expenses', []))}

═══════════════════════════════════════════════════════════════════════
🎯 INSTRUCCIONES PARA EL ANÁLISIS
═══════════════════════════════════════════════════════════════════════

DEBES GENERAR UN JSON con la siguiente estructura EXACTA (sin markdown, solo JSON puro):

{{
  "health_score": <número entero del 0 al 100>,
  "score_category": "<excelente|buena|mejorable|crítica>",
  "summary": {{
    "main_insight": "<insight principal en 1-2 frases máximo>",
    "period_analyzed": "Año {year}"
  }},
  "strengths": [
    "<fortaleza 1: ser específico con datos>",
    "<fortaleza 2: mencionar logros concretos>"
  ],
  "weaknesses": [
    "<debilidad 1: identificar problema específico>",
    "<debilidad 2: mencionar área de mejora con datos>"
  ],
  "alerts": [
    {{
      "type": "<critical|warning|info|success>",
      "title": "<título breve y claro>",
      "message": "<descripción del problema o situación>",
      "action": "<acción concreta y específica que el usuario puede tomar>"
    }}
  ],
  "recommendations": [
    {{
      "category": "<ahorro|gasto|inversión|presupuesto>",
      "title": "<título de la recomendación>",
      "description": "<explicación detallada con datos específicos del usuario>",
      "potential_saving": <número: ahorro mensual estimado en euros, 0 si no aplica>
    }}
  ],
  "predictions": {{
    "end_of_year_balance": <balance proyectado para 31 dic {year}>,
    "projected_savings": <ahorro total proyectado para {year}>,
    "risk_level": "<low|medium|high>",
    "confidence": <número del 0-100: confianza en la predicción>
  }}
}}

Criterios health_score:
- 80-100: "excelente" (tasa ahorro ≥30%, balance creciente)
- 60-79: "buena" (tasa ahorro 10-29%, balance positivo)
- 40-59: "mejorable" (tasa ahorro <10% o balance estancado)
- 0-39: "crítica" (tasa ahorro negativa o balance negativo)

Responde ÚNICAMENTE con el JSON válido. Sin texto adicional, sin markdown, sin explicaciones.

DIRECTRICES:
- Sé específico con números y porcentajes
- Prioriza alertas críticas (cuentas negativas, gastos excesivos)
- Recomendaciones deben ser accionables y realistas
- El health_score debe reflejar la salud financiera real
- Menciona categorías específicas donde se puede optimizar
- Usa meses naturales para referir a periodos (ej: "Mes 3" para marzo)
- Situate en el contexto del dia en que se genera el informe: {datetime.now().strftime('%d/%m/%Y')} con respecto al inicio del año {year} 

"""
    
    return prompt


def _format_monthly_breakdown(monthly_data: List[Dict]) -> str:
    """Formatea el desglose mensual para el prompt."""
    if not monthly_data:
        return "No hay datos mensuales disponibles."
    
    # Nombres de meses en español
    month_names = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    
    lines = []
    for month_data in monthly_data:
        month = month_data.get('month')
        income = month_data.get('income', 0)
        expenses = month_data.get('expenses', 0)
        balance = month_data.get('balance', 0)
        savings_rate = month_data.get('savings_rate', 0)
        
        if income > 0 or expenses > 0:  # Solo mostrar meses con datos
            month_name = month_names[month - 1] if 1 <= month <= 12 else f"Mes {month}"
            lines.append(
                f"  {month_name}: Ingresos €{income:.2f} | Gastos €{expenses:.2f} | "
                f"Balance €{balance:.2f} | Tasa ahorro {savings_rate:.1f}%"
            )
    
    return "\n".join(lines) if lines else "No hay datos mensuales disponibles."


def _format_top_categories(categories: List[Dict]) -> str:
    """Formatea las categorías principales."""
    if not categories:
        return "No hay categorías de gasto registradas."
    
    lines = []
    for i, cat in enumerate(categories[:5], 1):
        name = cat.get('category', 'Sin categoría')
        total = cat.get('total', 0)
        percentage = cat.get('percentage', 0)
        lines.append(f"  {i}. {name}: €{total:.2f} ({percentage:.1f}% del total)")
    
    return "\n".join(lines)


def _format_accounts_detail(accounts: List[Dict]) -> str:
    """Formatea el desglose detallado de cuentas."""
    if not accounts:
        return "No hay cuentas registradas."
    
    # Mapeo de tipos de cuenta a español
    account_types = {
        'checking': 'Cuenta corriente',
        'savings': 'Cuenta de ahorro',
        'investment': 'Cuenta de inversión',
        'credit_card': 'Tarjeta de crédito',
        'cash': 'Efectivo'
    }
    
    lines = []
    for i, acc in enumerate(accounts, 1):
        name = acc.get('name', 'Sin nombre')
        bank = acc.get('bank', 'No especificado')
        acc_type = account_types.get(acc.get('type', ''), acc.get('type', 'Desconocido'))
        balance = acc.get('balance', 0)
        currency = acc.get('currency', 'EUR')
        tx_count = acc.get('transaction_count', 0)
        status = '✓ Activa' if acc.get('is_active', True) else '✗ Inactiva'
        
        lines.append(
            f"  {i}. {name} ({bank})\n"
            f"     Tipo: {acc_type} | Balance: {currency}{balance:.2f} | Movimientos: {tx_count} | {status}"
        )
    
    return "\n".join(lines)


async def call_gemini_api(prompt: str) -> str:
    """
    Llama a la API de Gemini con el prompt generado.
    
    Args:
        prompt: Prompt completo para Gemini
    
    Returns:
        Respuesta JSON como string
    
    Raises:
        Exception: Si hay error en la llamada a Gemini
    """
    try:
        import google.generativeai as genai
        
        # Configurar API key
        genai.configure(api_key=settings.GEMINI_API_KEY)
        logger.info("🔑 Gemini API configurada correctamente")
        
        # Inicializar modelo
        model = genai.GenerativeModel(model_name=settings.LLM_MODEL)
        logger.info(f"🤖 Usando modelo: {settings.LLM_MODEL}")
        
        # Contar tokens de entrada
        count_response = model.count_tokens(prompt)
        input_tokens = count_response.total_tokens
        
        # Estimación de salida
        est_output_tokens = int(input_tokens * 0.8)  # Health reports suelen ser más concisos
        
        # Precios Nivel 1 (Tier 1) - Gemini 2.0 Flash
        # Input: $0.10 / 1M tokens | Output: $0.40 / 1M tokens
        cost_in = (input_tokens / 1_000_000) * 0.10
        cost_out = (est_output_tokens / 1_000_000) * 0.40
        total_est_cost = cost_in + cost_out

        logger.info(
            f"💰 ESTIMACIÓN DE COSTE - Modelo: {settings.LLM_MODEL} | "
            f"Tokens Entrada: {input_tokens} | "
            f"Tokens Salida (est): {est_output_tokens} | "
            f"Coste Total Est: ${total_est_cost:.6f}"
        )
        
        # Generar respuesta
        logger.info("🚀 Enviando prompt a Gemini...")
        response = model.generate_content(prompt)
        
        # Logs de consumo real
        if hasattr(response, 'usage_metadata'):
            actual_in = response.usage_metadata.prompt_token_count
            actual_out = response.usage_metadata.candidates_token_count
            actual_cost = ((actual_in / 1_000_000) * 0.10) + ((actual_out / 1_000_000) * 0.40)
            logger.info(
                f"💵 COSTE REAL FINAL - In: {actual_in} | Out: {actual_out} | "
                f"Coste: ${actual_cost:.6f}"
            )
        
        # Limpiar respuesta (eliminar markdown si lo hay)
        clean_response = response.text.replace("```json", "").replace("```", "").strip()
        
        logger.info("✅ Respuesta recibida de Gemini exitosamente")
        return clean_response
        
    except ImportError:
        logger.error("❌ google-generativeai no está instalado")
        raise Exception("google-generativeai package not installed")
    except Exception as e:
        logger.error(f"❌ Error llamando a Gemini API: {str(e)}")
        raise


def generate_local_health_analysis(user_data: Dict) -> Dict[str, Any]:
    """
    Genera un análisis de salud financiera local (fallback sin IA).
    """
    annual_summary = user_data.get('annual_summary', {})
    account_info = user_data.get('account_info', {})
    year = user_data.get('year')
    
    total_income = annual_summary.get('total_income', 0)
    total_expenses = annual_summary.get('total_expenses', 0)
    savings_rate = annual_summary.get('avg_savings_rate', 0)
    net_balance = annual_summary.get('net_balance', 0)
    current_balance = account_info.get('current_balance', 0)
    
    # Calcular score
    score = 0
    
    # Tasa de ahorro (30 puntos)
    if savings_rate >= 30:
        score += 30
    elif savings_rate >= 20:
        score += 25
    elif savings_rate >= 10:
        score += 18
    elif savings_rate >= 5:
        score += 10
    elif savings_rate >= 0:
        score += 5
    
    # Balance positivo (25 puntos)
    if net_balance > 0 and net_balance > total_income * 0.2:
        score += 25
    elif net_balance > 0:
        score += 15
    elif net_balance >= 0:
        score += 10
    
    # Control de gastos (25 puntos)
    if total_expenses < total_income * 0.7:
        score += 25
    elif total_expenses < total_income * 0.9:
        score += 15
    elif total_expenses <= total_income:
        score += 10
    
    # Ingresos (10 puntos)
    if total_income > 0:
        score += 10
    
    # Balance actual (10 puntos)
    if current_balance > 0:
        score += 10
    
    # Determinar categoría
    if score >= 80:
        category = "excelente"
    elif score >= 60:
        category = "buena"
    elif score >= 40:
        category = "mejorable"
    else:
        category = "crítica"
    
    # Generar fortalezas y debilidades
    strengths = []
    weaknesses = []
    alerts = []
    recommendations = []
    
    if savings_rate >= 20:
        strengths.append(f"Excelente tasa de ahorro del {savings_rate:.1f}%, muy por encima del promedio")
    elif savings_rate >= 10:
        strengths.append(f"Buena tasa de ahorro del {savings_rate:.1f}%")
    else:
        weaknesses.append(f"Tasa de ahorro baja ({savings_rate:.1f}%), objetivo recomendado: 20%")
        recommendations.append({
            "category": "ahorro",
            "title": "Incrementar tasa de ahorro",
            "description": f"Intenta reducir gastos en un 10% para aumentar tu tasa de ahorro del {savings_rate:.1f}% actual al 20%",
            "potential_saving": total_expenses * 0.1 / 12
        })
    
    if net_balance > 0:
        strengths.append(f"Balance positivo del año: €{net_balance:.2f}")
    else:
        weaknesses.append(f"Balance negativo en el año: €{net_balance:.2f}")
        alerts.append({
            "type": "warning",
            "title": "Balance negativo",
            "message": f"Tus gastos superaron los ingresos por €{abs(net_balance):.2f} en {year}",
            "action": "Revisa tus gastos principales y establece un presupuesto mensual"
        })
    
    # Predicciones
    months_remaining = 12 - annual_summary.get('months_with_data', 12)
    monthly_avg_income = total_income / max(annual_summary.get('months_with_data', 1), 1)
    monthly_avg_expenses = total_expenses / max(annual_summary.get('months_with_data', 1), 1)
    
    projected_income = total_income + (monthly_avg_income * months_remaining)
    projected_expenses = total_expenses + (monthly_avg_expenses * months_remaining)
    projected_savings = projected_income - projected_expenses
    
    end_of_year_balance = current_balance + (monthly_avg_income - monthly_avg_expenses) * months_remaining
    
    risk_level = "low" if savings_rate >= 20 else "medium" if savings_rate >= 10 else "high"
    confidence = 85 if annual_summary.get('months_with_data', 0) >= 6 else 60
    
    return {
        "health_score": score,
        "score_category": category,
        "summary": {
            "main_insight": f"Tu salud financiera es {category} con una tasa de ahorro del {savings_rate:.1f}%",
            "period_analyzed": f"Año {year}"
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        "alerts": alerts,
        "recommendations": recommendations,
        "predictions": {
            "end_of_year_balance": end_of_year_balance,
            "projected_savings": projected_savings,
            "risk_level": risk_level,
            "confidence": confidence
        }
    }


def validate_health_report(report: Dict) -> None:
    """
    Valida que el informe tenga la estructura esperada.
    """
    required_fields = [
        'health_score', 'score_category', 'summary',
        'strengths', 'weaknesses', 'alerts',
        'recommendations', 'predictions'
    ]
    
    for field in required_fields:
        if field not in report:
            raise ValueError(f"Campo requerido '{field}' no encontrado en el informe")
    
    # Validar rangos
    if not (0 <= report['health_score'] <= 100):
        raise ValueError("health_score debe estar entre 0 y 100")
    
    if report['score_category'] not in ['excelente', 'buena', 'mejorable', 'crítica']:
        raise ValueError("score_category no válida")
