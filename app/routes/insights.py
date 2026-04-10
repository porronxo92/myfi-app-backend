"""
Insights Routes - Endpoints para análisis con IA
=================================================

Endpoints para insights cualitativos, recomendaciones personalizadas
y análisis generados con Gemini AI.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.security import get_current_user, check_rate_limit, check_gemini_quota
from app.services.insights_service import InsightsService
from app.services.chat_service import ChatService
from app.schemas.insights import (
    FinancialInsight,
    FinancialHealthResponse,
    RecommendationsResponse,
    MonthlyOutlookResponse,
    SavingsPlanResponse,
    CustomAnalysisResponse,
    CustomAnalysisRequest,
    CombinedAnalyticsInsightsResponse
)
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/generate", response_model=list[FinancialInsight])
async def generate_insights(
    num_insights: int = Query(
        5,
        ge=1,
        le=10,
        description="Número de insights a generar (1-10)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit),
    __: User = Depends(check_gemini_quota)
):
    """
    Genera insights financieros personalizados usando Gemini AI.
    
    Analiza la situación financiera del usuario y genera recomendaciones,
    alertas y observaciones relevantes basadas en:
    - Patrones de gasto actuales
    - Cambios respecto a periodos anteriores
    - Transacciones inusuales
    - Oportunidades de ahorro
    - Gastos recurrentes
    
    Cada insight incluye:
    - Tipo (alert/positive/recommendation/neutral/prediction)
    - Prioridad (high/medium/low)
    - Icono representativo
    - Título y mensaje
    - Acción sugerida (opcional)
    
    **Tipos de insights:**
    - **Alert** ⚠️: Situaciones que requieren atención inmediata
    - **Positive** ✅: Reconocimiento de buenos hábitos financieros
    - **Recommendation** 💡: Sugerencias de optimización
    - **Neutral** ℹ️: Información relevante sin urgencia
    - **Prediction** 🔮: Predicciones sobre comportamiento futuro
    """
    try:
        user_id = current_user.id
        insights_service = InsightsService(db)
        
        insights = await insights_service.generate_financial_insights(
            user_id,
            num_insights
        )
        
        return insights
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar insights: {str(e)}"
        )


@router.get("/financial-health", response_model=FinancialHealthResponse)
async def get_financial_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit),
    __: User = Depends(check_gemini_quota)
):
    """
    Analiza la salud financiera general del usuario.
    
    Calcula un score de salud financiera (0-100) basado en:
    - **Tasa de ahorro** (40%): Capacidad de generar ahorros
    - **Control de gastos** (30%): Tendencia del balance mensual
    - **Estabilidad de ingresos** (30%): Variabilidad de ingresos
    
    **Grados:**
    - **A** (90-100): Excelente salud financiera
    - **B** (75-89): Buena salud, con pequeñas áreas de mejora
    - **C** (60-74): Salud aceptable, requiere atención
    - **D** (45-59): Necesita mejoras significativas
    - **F** (<45): Situación financiera crítica
    
    La respuesta incluye:
    - Score general y por categoría
    - Grado (A-F)
    - Insights específicos sobre salud financiera
    - Fortalezas identificadas
    - Áreas de mejora prioritarias
    """
    try:
        user_id = current_user.id
        insights_service = InsightsService(db)
        
        health = await insights_service.analyze_financial_health(user_id)
        
        return health
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al analizar salud financiera: {str(e)}"
        )


@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit),
    __: User = Depends(check_gemini_quota)
):
    """
    Genera recomendaciones personalizadas para optimizar gastos y aumentar ahorros.
    
    Analiza los datos financieros del usuario e identifica:
    - Categorías con gasto excesivo vs histórico
    - Suscripciones y gastos recurrentes altos
    - Oportunidades de ahorro realistas
    
    Para cada recomendación proporciona:
    - Categoría afectada
    - Gasto actual vs recomendado
    - Ahorro potencial mensual
    - Justificación basada en datos
    - Nivel de dificultad (easy/moderate/hard)
    
    Además incluye:
    - **Quick Wins**: Acciones rápidas con impacto inmediato
    - **Estrategias a largo plazo**: Cambios de hábitos sostenibles
    - **Ahorro total potencial**: Suma de todas las oportunidades
    
    **Niveles de dificultad:**
    - **Easy**: Cancelar suscripciones, reducir gastos pequeños
    - **Moderate**: Cambiar hábitos de consumo, buscar alternativas
    - **Hard**: Cambios estructurales (transporte, vivienda, etc.)
    """
    try:
        user_id = current_user.id
        insights_service = InsightsService(db)
        
        recommendations = await insights_service.get_spending_recommendations(user_id)
        
        return recommendations
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar recomendaciones: {str(e)}"
        )


@router.get("/monthly-outlook", response_model=MonthlyOutlookResponse)
async def get_monthly_outlook(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit),
    __: User = Depends(check_gemini_quota)
):
    """
    Predice cómo cerrará el mes actual basándose en el comportamiento hasta la fecha.
    
    Utiliza los datos del mes actual y patrones históricos para proyectar:
    - Ingresos esperados al cierre del mes
    - Gastos estimados (basado en ritmo actual)
    - Balance proyectado
    
    **Metodología de predicción:**
    - Ingresos: Promedio de últimos 3 meses
    - Gastos: Ritmo actual (€/día) × días restantes + gastos acumulados
    - Confianza: Mayor cuanto más avanzado el mes
    
    **Niveles de confianza:**
    - **High**: <7 días restantes (>85% del mes transcurrido)
    - **Medium**: 8-15 días restantes
    - **Low**: >15 días restantes
    
    La respuesta incluye:
    - Estado actual del mes (ingresos/gastos/balance hasta hoy)
    - Predicción con nivel de confianza
    - Alertas sobre categorías con gasto alto
    - Consejos para ajustar el rumbo si es necesario
    """
    try:
        user_id = current_user.id
        insights_service = InsightsService(db)
        
        outlook = await insights_service.predict_monthly_outlook(user_id)
        
        return outlook
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al predecir cierre de mes: {str(e)}"
        )


@router.post("/savings-plan", response_model=SavingsPlanResponse)
async def create_savings_plan(
    target_amount: float = Query(
        ...,
        gt=0,
        description="Monto objetivo a ahorrar"
    ),
    months: int = Query(
        12,
        ge=1,
        le=60,
        description="Plazo en meses para alcanzar el objetivo (1-60)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit),
    __: User = Depends(check_gemini_quota)
):
    """
    Genera un plan de ahorro personalizado para alcanzar un objetivo financiero.
    
    Analiza la situación actual del usuario y crea un plan paso a paso
    para alcanzar el objetivo en el plazo especificado.
    
    **Pasos del plan incluyen:**
    1. Eliminación de gastos innecesarios (suscripciones, etc.)
    2. Reducción de categorías con exceso de gasto
    3. Automatización de transferencias a ahorro
    
    Para cada paso:
    - Acción específica a tomar
    - Ahorro esperado
    - Plazo de implementación (immediate/short-term/long-term)
    
    **Evaluación de factibilidad:**
    - **Very Feasible**: El objetivo es alcanzable con ajustes menores
    - **Feasible**: Requiere disciplina pero es realista
    - **Challenging**: Necesita cambios significativos
    - **Unrealistic**: Objetivo muy ambicioso, se sugieren alternativas
    
    Si el plan es difícil de cumplir, se incluyen sugerencias alternativas:
    - Extender el plazo
    - Reducir el objetivo
    - Buscar fuentes adicionales de ingreso
    
    **Ejemplo de uso:**
    ```
    POST /api/insights/savings-plan?target_amount=5000&months=12
    
    → Plan para ahorrar €5,000 en 12 meses (€417/mes)
    ```
    """
    try:
        user_id = current_user.id
        insights_service = InsightsService(db)
        
        plan = await insights_service.generate_savings_plan(
            user_id,
            target_amount,
            months
        )
        
        return plan
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar plan de ahorro: {str(e)}"
        )


@router.post("/custom-analysis", response_model=CustomAnalysisResponse)
async def custom_analysis(
    request: CustomAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit),
    __: User = Depends(check_gemini_quota)
):
    """
    Responde preguntas personalizadas del usuario sobre sus finanzas usando Gemini AI.
    
    Permite al usuario hacer preguntas en lenguaje natural y obtener respuestas
    contextualizadas basadas en sus datos financieros reales.
    
    **Ejemplos de preguntas:**
    - "¿En qué categoría gasto más dinero?"
    - "¿Cómo puedo ahorrar €500 este mes?"
    - "¿Mis gastos están aumentando o disminuyendo?"
    - "¿Cuánto gasto en promedio en restaurantes?"
    - "¿Tengo suscripciones que debería cancelar?"
    
    **Request body:**
    ```json
    {
      "question": "¿En qué puedo reducir gastos este mes?",
      "context": {
        "focus_category": "Alimentación",
        "target_savings": 200
      }
    }
    ```
    
    **Respuesta incluye:**
    - Respuesta en lenguaje natural de Gemini
    - Datos de soporte relevantes (cifras, categorías, etc.)
    - Insights relacionados (opcional)
    - Preguntas de seguimiento sugeridas
    
    El análisis considera automáticamente:
    - Resumen financiero del mes actual
    - Desglose por categorías
    - Comparación con mes anterior
    - Contexto adicional proporcionado por el usuario
    """
    try:
        user_id = current_user.id
        insights_service = InsightsService(db)
        
        analysis = await insights_service.custom_analysis(
            user_id,
            request.question,
            request.context
        )
        
        return analysis
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar análisis personalizado: {str(e)}"
        )


@router.get("/dashboard", response_model=CombinedAnalyticsInsightsResponse)
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit),
    __: User = Depends(check_gemini_quota)
):
    """
    Endpoint optimizado para el dashboard principal.
    
    Retorna en una sola llamada todos los datos necesarios para renderizar
    el dashboard de analytics e insights:
    
    **Analytics incluidos:**
    - Resumen del mes actual
    - Desglose por categorías
    - Tendencias de últimos 6 meses
    
    **Insights incluidos:**
    - 4 insights principales generados con IA
    - Score de salud financiera
    
    **Quick Stats:**
    - Cambio de balance vs mes anterior
    - Tasa de ahorro actual
    - Categoría con mayor gasto
    - Número de transacciones del mes
    
    **Ventajas de este endpoint:**
    - ✅ Reduce latencia (1 request vs 5+)
    - ✅ Datos coherentes (snapshot atómico)
    - ✅ Optimizado para renderizado inicial
    - ✅ Menor carga en frontend y backend
    
    **Uso recomendado:**
    ```typescript
    // En vez de múltiples llamadas:
    // - GET /analytics/summary
    // - GET /analytics/categories
    // - GET /analytics/trends
    // - GET /insights/generate
    // - GET /insights/financial-health
    
    // Usar solo:
    dashboardService.getDashboardData().subscribe(data => {
      this.analytics = data.analytics;
      this.insights = data.insights;
      this.healthScore = data.health_score;
      this.quickStats = data.quick_stats;
    });
    ```
    """
    try:
        user_id = current_user.id
        insights_service = InsightsService(db)
        
        dashboard_data = await insights_service.get_combined_dashboard_data(user_id)
        
        return dashboard_data
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener datos del dashboard: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit),
    __: User = Depends(check_gemini_quota)
):
    """
    Agente conversacional financiero con Gemini AI.

    SEGURIDAD:
    - Los mensajes se sanitizan antes de procesarse
    - Se detectan y bloquean intentos de prompt injection
    - El historial se valida y sanitiza
    - (Cuando está habilitado) El historial se almacena en servidor

    Permite al usuario conversar en lenguaje natural sobre sus finanzas.
    El agente tiene acceso a los datos financieros del usuario y puede:
    - Responder preguntas sobre cuentas, gastos, presupuestos, etc.
    - Proponer acciones (crear transacciones, categorías) que requieren confirmación

    **Request body:**
    ```json
    {
      "message": "¿Cuánto he gastado este mes en supermercado?",
      "conversation_history": [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "¡Hola! Soy MyFi..."}
      ]
    }
    ```

    **Response (informativa):**
    ```json
    {
      "message": "Este mes has gastado 234,50€ en Supermercado...",
      "proposed_action": null,
      "suggested_questions": ["¿Cuáles son mis mayores gastos?", ...],
      "timestamp": "2026-04-01T10:30:00Z"
    }
    ```

    **Response (con acción propuesta):**
    ```json
    {
      "message": "Voy a registrar el gasto. Confirma antes de guardar.",
      "proposed_action": {
        "type": "create_transaction",
        "description": "Crear gasto de -45€ en Mercadona",
        "endpoint": "POST /api/transactions",
        "data": { ... }
      },
      "suggested_questions": [],
      "timestamp": "2026-04-01T10:30:00Z"
    }
    ```

    **Flujo de confirmación:**
    1. El agente propone una acción (proposed_action != null)
    2. El frontend muestra un modal de confirmación al usuario
    3. Si confirma, el frontend llama directamente al endpoint indicado
    4. Si cancela, no se ejecuta nada

    **Notas:**
    - Los mensajes se sanitizan para prevenir prompt injection
    - Cada llamada consume 1 petición del límite diario de Gemini
    - El contexto financiero se carga automáticamente en cada mensaje
    """
    from app.services.chat_session_service import ChatSessionService
    from app.utils.logger import get_logger

    logger = get_logger(__name__)

    try:
        chat_service = ChatService(db, current_user.id)

        # Intentar usar sesiones del servidor si la tabla existe
        server_history = None
        session = None

        try:
            session_service = ChatSessionService(db)
            session = session_service.get_or_create_session(current_user.id)
            server_history = session_service.get_history(session.id)
            logger.debug(f"Usando historial del servidor ({len(server_history)} mensajes)")
        except Exception as e:
            # Tabla chat_sessions no existe aún, usar historial del frontend
            logger.debug(f"Sesiones de servidor no disponibles, usando frontend: {e}")
            server_history = None

        # Usar historial del servidor si está disponible, sino del frontend
        conversation_history = server_history if server_history is not None else request.conversation_history

        # Procesar mensaje (la sanitización está en ChatService)
        response = await chat_service.process_message(
            message=request.message,
            conversation_history=conversation_history
        )

        # Guardar en servidor si está disponible
        if session is not None:
            try:
                session_service.add_message(session.id, "user", request.message)
                session_service.add_message(session.id, "assistant", response.message)
            except Exception as e:
                logger.warning(f"Error guardando mensajes en servidor: {e}")

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el chat: {str(e)}"
        )
