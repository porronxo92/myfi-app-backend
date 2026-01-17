"""
Insights Service - Integración con Gemini AI
============================================

Servicio para generar insights cualitativos, recomendaciones y análisis
financieros personalizados utilizando Google Gemini AI a través del MCP.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import json
import os
from sqlalchemy.orm import Session

# Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not installed. Insights will use fallback mode.")

from app.services.mcp.financial_context import MCPFinancialContext
from app.services.analytics_service import AnalyticsService
from app.schemas.insights import (
    FinancialInsight,
    InsightType,
    InsightPriority,
    InsightAction,
    FinancialHealthResponse,
    FinancialHealthScore,
    RecommendationsResponse,
    SpendingRecommendation,
    MonthlyOutlookResponse,
    MonthlyOutlookPrediction,
    SavingsPlanResponse,
    SavingsGoal,
    SavingsPlanStep,
    CustomAnalysisResponse,
    CombinedAnalyticsInsightsResponse
)


class InsightsService:
    """
    Servicio de insights financieros con IA.
    
    Utiliza Gemini AI para generar análisis cualitativos, recomendaciones
    personalizadas y predicciones basadas en los datos financieros del usuario.
    """
    
    def __init__(self, db: Session, gemini_api_key: Optional[str] = None):
        self.db = db
        self.mcp = MCPFinancialContext(db)
        self.analytics = AnalyticsService(db)
        
        # Configurar Gemini
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model = None
        
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                print("✅ Gemini AI configured successfully")
            except Exception as e:
                print(f"⚠️ Error configuring Gemini: {e}")
                self.model = None
        else:
            print("⚠️ Gemini not available. Using fallback insights.")
    
    def _is_gemini_available(self) -> bool:
        """Verifica si Gemini está disponible."""
        return self.model is not None
    
    async def _call_gemini(
        self, 
        prompt: str, 
        context: Dict[str, Any],
        temperature: float = 0.7
    ) -> str:
        """
        Llama a Gemini AI con el prompt y contexto proporcionados.
        
        Args:
            prompt: Prompt principal
            context: Contexto financiero del usuario
            temperature: Creatividad de la respuesta (0.0-1.0)
        
        Returns:
            Respuesta generada por Gemini
        """
        if not self._is_gemini_available():
            return self._get_fallback_response(prompt, context)
        
        try:
            # Construir prompt completo
            full_prompt = self._build_full_prompt(prompt, context)
            
            # Generar respuesta
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=1000
                )
            )
            
            return response.text
        
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            return self._get_fallback_response(prompt, context)
    
    def _build_full_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """Construye el prompt completo con contexto MCP."""
        
        system_context = """
Eres un asesor financiero personal experto y cercano. Tu objetivo es ayudar a los usuarios
a entender mejor sus finanzas y tomar decisiones informadas.

REGLAS IMPORTANTES:
1. Sé conciso: máximo 2-3 frases por insight
2. Usa un tono amigable pero profesional (tutea al usuario)
3. Proporciona datos concretos cuando sea posible (cifras, porcentajes)
4. Enfócate en insights accionables, no en observaciones obvias
5. Sé positivo cuando el usuario haga bien las cosas
6. Cuando detectes problemas, ofrece soluciones realistas
7. Usa emojis ocasionalmente para hacer el mensaje más cercano

CONTEXTO FINANCIERO DEL USUARIO:
"""
        
        context_str = json.dumps(context, indent=2, ensure_ascii=False)
        
        return f"{system_context}\n{context_str}\n\nTAREA:\n{prompt}"
    
    def _get_fallback_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """Respuesta de fallback cuando Gemini no está disponible."""
        
        # Análisis básico sin IA
        if "summary" in context:
            summary = context["summary"]
            savings_rate = summary.get("savings_rate", 0)
            
            if savings_rate > 20:
                return f"Tu tasa de ahorro es excelente ({savings_rate:.1f}%). Mantén este buen hábito."
            elif savings_rate > 10:
                return f"Tu tasa de ahorro es buena ({savings_rate:.1f}%). Considera aumentarla gradualmente."
            else:
                return f"Tu tasa de ahorro es baja ({savings_rate:.1f}%). Identifica áreas donde puedas reducir gastos."
        
        return "Análisis en proceso. Por favor, intenta de nuevo más tarde."
    
    async def generate_financial_insights(
        self, 
        user_id: UUID, 
        num_insights: int = 5
    ) -> List[FinancialInsight]:
        """
        Genera insights financieros personalizados.
        
        Args:
            user_id: ID del usuario
            num_insights: Número de insights a generar (default 5)
        
        Returns:
            Lista de FinancialInsight generados
        """
        # Recopilar contexto financiero
        summary = self.mcp.get_user_financial_summary(user_id, 'current_month')
        spending = self.mcp.get_spending_by_category(user_id, 'current_month')
        unusual = self.mcp.get_unusual_transactions(user_id, threshold=2.0)
        recurring = self.mcp.get_recurring_expenses(user_id)
        comparison = self.mcp.compare_periods(user_id, 'current_month', 'last_month')
        
        context = {
            "summary": summary,
            "spending_by_category": spending[:5],  # Top 5
            "unusual_transactions": unusual[:3],  # Top 3
            "recurring_expenses": recurring[:5],
            "comparison_with_last_month": comparison["summary_comparison"]
        }
        
        # Prompt para Gemini
        prompt = f"""
Analiza la situación financiera del usuario y genera {num_insights} insights valiosos.

Para cada insight, proporciona:
1. Tipo (alert/positive/recommendation/neutral)
2. Prioridad (high/medium/low)
3. Título breve (máx 80 caracteres)
4. Mensaje conciso (2-3 frases)

Enfócate en:
- Cambios significativos respecto al mes anterior
- Gastos inusuales o preocupantes
- Oportunidades de ahorro
- Reconocimiento de buenos hábitos
- Alertas sobre suscripciones o gastos recurrentes altos

Formato de respuesta (JSON):
[
  {{
    "type": "alert|positive|recommendation|neutral",
    "priority": "high|medium|low",
    "title": "Título del insight",
    "message": "Mensaje detallado pero conciso"
  }}
]
"""
        
        # Llamar a Gemini
        response_text = await self._call_gemini(prompt, context)
        
        # Parsear respuesta
        insights = self._parse_insights_response(response_text, user_id)
        
        return insights[:num_insights]
    
    def _parse_insights_response(
        self, 
        response_text: str, 
        user_id: UUID
    ) -> List[FinancialInsight]:
        """Parsea la respuesta de Gemini y crea objetos FinancialInsight."""
        
        insights = []
        
        try:
            # Intentar parsear como JSON
            # Buscar el array JSON en la respuesta
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed_insights = json.loads(json_str)
                
                for idx, item in enumerate(parsed_insights):
                    insight = FinancialInsight(
                        id=f"insight-{user_id}-{idx}",
                        type=InsightType(item.get("type", "neutral")),
                        priority=InsightPriority(item.get("priority", "medium")),
                        icon=self._get_icon_for_type(item.get("type", "neutral")),
                        title=item.get("title", "Insight Financiero"),
                        message=item.get("message", ""),
                        data_point=item.get("data_point"),
                        action=self._create_action_if_needed(item),
                        generated_at=datetime.now()
                    )
                    insights.append(insight)
        
        except json.JSONDecodeError:
            # Fallback: crear insights genéricos
            insights = self._create_fallback_insights(user_id)
        
        return insights
    
    def _get_icon_for_type(self, insight_type: str) -> str:
        """Retorna el emoji apropiado para cada tipo de insight."""
        icons = {
            "alert": "⚠️",
            "positive": "✅",
            "recommendation": "💡",
            "neutral": "ℹ️",
            "prediction": "🔮"
        }
        return icons.get(insight_type, "ℹ️")
    
    def _create_action_if_needed(self, item: Dict[str, Any]) -> Optional[InsightAction]:
        """Crea una acción si el insight lo requiere."""
        
        if item.get("action_route"):
            return InsightAction(
                label=item.get("action_label", "Ver detalle"),
                route=item["action_route"],
                action_type="navigate"
            )
        
        return None
    
    def _create_fallback_insights(self, user_id: UUID) -> List[FinancialInsight]:
        """Crea insights de fallback cuando Gemini falla."""
        
        return [
            FinancialInsight(
                id=f"fallback-{user_id}-1",
                type=InsightType.NEUTRAL,
                priority=InsightPriority.MEDIUM,
                icon="ℹ️",
                title="Análisis en Proceso",
                message="Estamos analizando tus datos financieros. Vuelve pronto para ver insights personalizados.",
                generated_at=datetime.now()
            )
        ]
    
    async def analyze_financial_health(self, user_id: UUID) -> FinancialHealthResponse:
        """
        Analiza la salud financiera general del usuario.
        
        Returns:
            FinancialHealthResponse con puntuación y análisis
        """
        # Recopilar datos
        summary = self.mcp.get_user_financial_summary(user_id, 'current_month')
        trends = self.mcp.get_monthly_trend(user_id, months=6)
        recurring = self.mcp.get_recurring_expenses(user_id)
        
        # Calcular puntuaciones por categoría
        savings_score = min(100, int(summary['savings_rate'] * 2.5))  # 40% savings = 100 pts
        
        # Score de control de gastos (basado en tendencia)
        if len(trends['balance']) >= 3:
            recent_avg = sum(trends['balance'][-3:]) / 3
            spending_control_score = min(100, max(0, int(recent_avg / 10)))
        else:
            spending_control_score = 50
        
        # Score de estabilidad de ingresos (basado en variación)
        if len(trends['income']) >= 3:
            income_variation = (max(trends['income']) - min(trends['income'])) / max(trends['income']) if max(trends['income']) > 0 else 0
            income_stability_score = max(0, int(100 - (income_variation * 100)))
        else:
            income_stability_score = 70
        
        # Score general (promedio ponderado)
        overall_score = int(
            savings_score * 0.4 +
            spending_control_score * 0.3 +
            income_stability_score * 0.3
        )
        
        # Determinar grado
        if overall_score >= 90:
            grade = "A"
        elif overall_score >= 75:
            grade = "B"
        elif overall_score >= 60:
            grade = "C"
        elif overall_score >= 45:
            grade = "D"
        else:
            grade = "F"
        
        # Generar insights específicos de salud
        health_insights = await self.generate_financial_insights(user_id, num_insights=3)
        
        # Identificar fortalezas y áreas de mejora
        strengths = []
        improvements = []
        
        if savings_score >= 70:
            strengths.append(f"Excelente tasa de ahorro ({summary['savings_rate']:.1f}%)")
        else:
            improvements.append("Aumentar la tasa de ahorro mensual")
        
        if income_stability_score >= 80:
            strengths.append("Ingresos estables y predecibles")
        else:
            improvements.append("Buscar fuentes de ingreso más estables")
        
        if spending_control_score >= 70:
            strengths.append("Buen control de gastos mensuales")
        else:
            improvements.append("Mejorar el control de gastos discrecionales")
        
        # Evaluar gastos recurrentes
        total_recurring = sum([item['annual_cost'] for item in recurring]) / 12
        if total_recurring > summary['total_income'] * 0.3:
            improvements.append("Revisar y reducir suscripciones y gastos fijos")
        
        return FinancialHealthResponse(
            user_id=str(user_id),
            analyzed_at=datetime.now(),
            health_score=FinancialHealthScore(
                overall_score=overall_score,
                category_scores={
                    "savings_rate": savings_score,
                    "spending_control": spending_control_score,
                    "income_stability": income_stability_score
                },
                grade=grade,
                summary=f"Tu salud financiera está en nivel {grade}. {'¡Excelente trabajo!' if overall_score >= 75 else 'Hay margen de mejora.'}"
            ),
            insights=health_insights,
            strengths=strengths,
            areas_of_improvement=improvements
        )
    
    async def get_spending_recommendations(self, user_id: UUID) -> RecommendationsResponse:
        """
        Genera recomendaciones personalizadas de optimización de gastos.
        
        Returns:
            RecommendationsResponse con recomendaciones accionables
        """
        # Obtener potencial de ahorro
        savings_potential = self.mcp.get_savings_potential(user_id)
        recurring = self.mcp.get_recurring_expenses(user_id)
        
        recommendations = []
        
        # Recomendaciones basadas en potencial de ahorro
        for opp in savings_potential[:3]:
            difficulty = "easy" if opp['potential_savings_monthly'] < 50 else \
                        "moderate" if opp['potential_savings_monthly'] < 150 else "hard"
            
            recommendations.append(SpendingRecommendation(
                category=opp['category'],
                current_spending=opp['current_spending'],
                recommended_spending=opp['historical_avg'],
                potential_savings=opp['potential_savings_monthly'],
                reasoning=opp['recommendation'],
                difficulty=difficulty
            ))
        
        # Recomendaciones basadas en gastos recurrentes
        high_recurring = [r for r in recurring if r['annual_cost'] > 500]
        for rec in high_recurring[:2]:
            recommendations.append(SpendingRecommendation(
                category=rec['category'],
                current_spending=rec['avg_amount'],
                recommended_spending=0,
                potential_savings=rec['avg_amount'],
                reasoning=f"Evalúa si realmente necesitas '{rec['description']}' ({rec['frequency']})",
                difficulty="easy"
            ))
        
        total_savings = sum([r.potential_savings for r in recommendations])
        
        # Quick wins
        quick_wins = [
            f"Cancelar {rec['description']} ahorra €{rec['avg_amount']:.2f}/mes"
            for rec in recurring[:3] if rec['frequency'] == 'mensual'
        ]
        
        # Estrategias a largo plazo
        long_term = [
            "Establecer presupuestos mensuales por categoría",
            "Automatizar transferencias a cuenta de ahorros el día de cobro",
            "Revisar gastos recurrentes cada 3 meses",
            "Comparar precios antes de compras mayores a €50"
        ]
        
        return RecommendationsResponse(
            user_id=str(user_id),
            generated_at=datetime.now(),
            total_potential_savings=total_savings,
            recommendations=recommendations,
            quick_wins=quick_wins[:3],
            long_term_strategies=long_term
        )
    
    async def predict_monthly_outlook(self, user_id: UUID) -> MonthlyOutlookResponse:
        """
        Predice el cierre del mes actual basándose en patrones históricos.
        
        Returns:
            MonthlyOutlookResponse con predicción y alertas
        """
        now = datetime.now()
        current_month = now.strftime("%Y-%m")
        days_in_month = 31  # Simplificado
        day_of_month = now.day
        days_remaining = days_in_month - day_of_month
        
        # Obtener situación actual
        current_summary = self.mcp.get_user_financial_summary(user_id, 'current_month')
        
        # Obtener histórico para predicción
        trends = self.mcp.get_monthly_trend(user_id, months=3)
        
        # Calcular promedios históricos
        avg_monthly_income = sum(trends['income']) / len(trends['income']) if trends['income'] else current_summary['total_income']
        avg_monthly_expenses = sum(trends['expenses']) / len(trends['expenses']) if trends['expenses'] else current_summary['total_expenses']
        
        # Proyectar basándose en el ritmo actual
        days_elapsed = day_of_month
        daily_expense_rate = current_summary['total_expenses'] / days_elapsed if days_elapsed > 0 else 0
        
        # Predicción
        predicted_income = avg_monthly_income  # Asumimos ingresos completos
        predicted_expenses = current_summary['total_expenses'] + (daily_expense_rate * days_remaining)
        predicted_balance = predicted_income - predicted_expenses
        
        # Nivel de confianza
        if days_remaining <= 7:
            confidence = "high"
        elif days_remaining <= 15:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Alertas
        alerts = []
        spending_by_cat = self.mcp.get_spending_by_category(user_id, 'current_month')
        
        for cat in spending_by_cat[:3]:
            if cat['percentage'] > 30:
                alerts.append(f"Gastos en '{cat['category_name']}' representan el {cat['percentage']:.0f}% del total")
        
        if predicted_balance < 0:
            alerts.append("⚠️ Predicción de balance negativo al cierre del mes")
        
        # Consejo
        if predicted_balance > current_summary['total_income'] * 0.15:
            advice = "Vas por buen camino. Mantén el control de gastos para cumplir tu objetivo."
        elif predicted_balance > 0:
            advice = "El margen es ajustado. Evita gastos innecesarios en lo que queda de mes."
        else:
            advice = "Reduce gastos urgentemente para evitar déficit. Prioriza solo lo esencial."
        
        return MonthlyOutlookResponse(
            user_id=str(user_id),
            current_month=current_month,
            days_remaining=days_remaining,
            current_status={
                "income_so_far": current_summary['total_income'],
                "expenses_so_far": current_summary['total_expenses'],
                "balance_so_far": current_summary['net_balance']
            },
            prediction=MonthlyOutlookPrediction(
                predicted_income=predicted_income,
                predicted_expenses=predicted_expenses,
                predicted_balance=predicted_balance,
                confidence=confidence,
                assumptions=[
                    "Ingresos similares al promedio de últimos 3 meses",
                    f"Ritmo de gasto actual (€{daily_expense_rate:.2f}/día) se mantiene"
                ]
            ),
            alerts=alerts,
            advice=advice
        )
    
    async def generate_savings_plan(
        self, 
        user_id: UUID, 
        target_amount: float,
        months: int = 12
    ) -> SavingsPlanResponse:
        """
        Genera un plan de ahorro personalizado.
        
        Args:
            user_id: ID del usuario
            target_amount: Monto objetivo a ahorrar
            months: Plazo en meses (default 12)
        
        Returns:
            SavingsPlanResponse con plan paso a paso
        """
        # Obtener situación actual
        summary = self.mcp.get_user_financial_summary(user_id, 'current_month')
        savings_potential = self.mcp.get_savings_potential(user_id)
        recurring = self.mcp.get_recurring_expenses(user_id)
        
        current_savings = summary['net_balance']
        monthly_needed = (target_amount - current_savings) / months if months > 0 else target_amount
        
        # Crear pasos del plan
        steps = []
        cumulative_savings = 0
        step_num = 1
        
        # Paso 1: Eliminar/reducir gastos recurrentes innecesarios
        for rec in recurring[:2]:
            if rec['frequency'] == 'mensual':
                steps.append(SavingsPlanStep(
                    step_number=step_num,
                    action=f"Cancelar o reducir '{rec['description']}'",
                    expected_savings=rec['avg_amount'],
                    timeframe="immediate"
                ))
                cumulative_savings += rec['avg_amount']
                step_num += 1
        
        # Paso 2: Reducir categorías con exceso de gasto
        for opp in savings_potential[:2]:
            if cumulative_savings < monthly_needed:
                steps.append(SavingsPlanStep(
                    step_number=step_num,
                    action=f"Reducir gastos en {opp['category']} a €{opp['historical_avg']:.0f}/mes",
                    expected_savings=opp['potential_savings_monthly'],
                    timeframe="short-term"
                ))
                cumulative_savings += opp['potential_savings_monthly']
                step_num += 1
        
        # Paso 3: Automatizar ahorro
        if cumulative_savings >= monthly_needed:
            steps.append(SavingsPlanStep(
                step_number=step_num,
                action=f"Programar transferencia automática de €{monthly_needed:.0f} el día de cobro",
                expected_savings=0,
                timeframe="immediate"
            ))
        
        # Evaluar factibilidad
        if cumulative_savings >= monthly_needed:
            feasibility = "very_feasible"
        elif cumulative_savings >= monthly_needed * 0.7:
            feasibility = "feasible"
        elif cumulative_savings >= monthly_needed * 0.5:
            feasibility = "challenging"
        else:
            feasibility = "unrealistic"
        
        # Sugerencias alternativas si es muy difícil
        alternatives = []
        if feasibility in ["challenging", "unrealistic"]:
            alternatives = [
                f"Considera extender el plazo a {months + 6} meses",
                f"Reduce el objetivo a €{target_amount * 0.7:.0f}",
                "Busca fuentes adicionales de ingreso"
            ]
        
        motivational = self._get_motivational_message(feasibility, target_amount, months)
        
        return SavingsPlanResponse(
            user_id=str(user_id),
            goal=SavingsGoal(
                target_amount=target_amount,
                current_savings=current_savings,
                months_to_achieve=months,
                monthly_savings_needed=monthly_needed
            ),
            plan_steps=steps,
            feasibility=feasibility,
            alternative_suggestions=alternatives,
            motivational_message=motivational
        )
    
    def _get_motivational_message(self, feasibility: str, target: float, months: int) -> str:
        """Genera mensaje motivacional según factibilidad."""
        
        messages = {
            "very_feasible": f"¡Excelente! Puedes alcanzar €{target:.0f} en {months} meses con estos pequeños ajustes. 🎯",
            "feasible": f"Con disciplina y estos cambios, alcanzarás €{target:.0f} en {months} meses. ¡Tú puedes! 💪",
            "challenging": f"Será un reto, pero no imposible. Considera ajustar el plazo o el objetivo. 🚀",
            "unrealistic": f"Este objetivo es muy ambicioso para {months} meses. Revisa las alternativas sugeridas. 💡"
        }
        
        return messages.get(feasibility, "Analiza el plan y ajústalo según tus posibilidades.")
    
    async def custom_analysis(
        self, 
        user_id: UUID, 
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CustomAnalysisResponse:
        """
        Responde preguntas personalizadas del usuario sobre sus finanzas.
        
        Args:
            user_id: ID del usuario
            question: Pregunta del usuario
            context: Contexto adicional opcional
        
        Returns:
            CustomAnalysisResponse con respuesta personalizada
        """
        # Recopilar contexto relevante
        summary = self.mcp.get_user_financial_summary(user_id, 'current_month')
        spending = self.mcp.get_spending_by_category(user_id, 'current_month')
        comparison = self.mcp.compare_periods(user_id, 'current_month', 'last_month')
        
        analysis_context = {
            "summary": summary,
            "spending": spending[:5],
            "comparison": comparison["summary_comparison"],
            "user_context": context or {}
        }
        
        # Prompt para análisis personalizado
        prompt = f"""
El usuario pregunta: "{question}"

Proporciona una respuesta clara, concisa y basada en sus datos financieros.
Incluye cifras concretas cuando sea relevante.
Si detectas oportunidades de mejora, menciόnalas.

Tu respuesta debe ser:
- Máximo 3-4 párrafos
- Lenguaje cercano (tutea al usuario)
- Datos específicos del contexto financiero
- Accionable si es posible
"""
        
        # Llamar a Gemini
        answer = await self._call_gemini(prompt, analysis_context)
        
        # Datos de soporte
        supporting_data = {}
        if "gast" in question.lower():
            supporting_data = {"spending_categories": spending[:3]}
        elif "ingreso" in question.lower() or "ingres" in question.lower():
            supporting_data = {"income": summary['total_income']}
        
        # Preguntas de seguimiento sugeridas
        follow_ups = [
            "¿Cómo puedo reducir mis gastos este mes?",
            "¿Cuánto puedo ahorrar realistamente?",
            "¿En qué categoría gasto más?"
        ]
        
        return CustomAnalysisResponse(
            user_id=str(user_id),
            question=question,
            answer=answer,
            supporting_data=supporting_data if supporting_data else None,
            related_insights=[],
            follow_up_questions=follow_ups
        )
    
    async def get_combined_dashboard_data(self, user_id: UUID) -> CombinedAnalyticsInsightsResponse:
        """
        Obtiene datos combinados de analytics + insights para el dashboard.
        
        Returns:
            CombinedAnalyticsInsightsResponse con todo lo necesario para el dashboard
        """
        # Analytics
        summary = await self.analytics.calculate_monthly_summary(user_id, 'current_month')
        categories = await self.analytics.get_category_breakdown(user_id, 'expense', 'current_month')
        trends = await self.analytics.get_spending_trends(user_id, months=6)
        
        # Insights
        insights = await self.generate_financial_insights(user_id, num_insights=4)
        health = await self.analyze_financial_health(user_id)
        
        # Stats rápidas
        last_month_summary = await self.analytics.calculate_monthly_summary(user_id, 'last_month')
        balance_change = ((summary.net_balance - last_month_summary.net_balance) / last_month_summary.net_balance * 100) if last_month_summary.net_balance != 0 else 0
        
        top_category = categories.categories[0].category_name if categories.categories else "N/A"
        
        return CombinedAnalyticsInsightsResponse(
            analytics={
                "summary": summary.dict(),
                "categories": categories.dict(),
                "trends": trends.dict()
            },
            insights=insights,
            health_score=health.health_score,
            quick_stats={
                "balance_vs_last_month": f"{'+' if balance_change > 0 else ''}{balance_change:.1f}%",
                "savings_rate": summary.savings_rate,
                "top_category": top_category,
                "num_transactions": summary.num_transactions
            }
        )
