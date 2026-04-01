"""
Chat Service - Agente Conversacional con Gemini
================================================

Implementa la lógica del agente conversacional usando Gemini con function calling.
El agente puede responder preguntas sobre finanzas y proponer acciones que
requieren confirmación del usuario.
"""

import json
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import settings
from app.schemas.chat import ChatMessage, ChatResponse, ProposedAction
from app.services.chat_context_builder import ChatContextBuilder
from app.models.account import Account
from app.models.category import Category
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================
# DEFINICIONES DE FUNCIONES PARA GEMINI
# ============================================

TOOL_DEFINITIONS = [
    {
        "name": "create_transaction",
        "description": """
        Crea una nueva transacción (gasto o ingreso).
        Usa esta función cuando el usuario quiera registrar un gasto o ingreso.
        Ejemplos: "añade un gasto de 45€ en Mercadona", "registra que cobré 1500€ de sueldo"
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "account_name": {
                    "type": "string",
                    "description": "Nombre de la cuenta donde registrar (si no se especifica, usar la cuenta principal)"
                },
                "amount": {
                    "type": "number",
                    "description": "Monto de la transacción (positivo)"
                },
                "description": {
                    "type": "string",
                    "description": "Descripción o concepto de la transacción"
                },
                "transaction_type": {
                    "type": "string",
                    "enum": ["expense", "income"],
                    "description": "Tipo: expense para gastos, income para ingresos"
                },
                "category_name": {
                    "type": "string",
                    "description": "Nombre de la categoría (debe existir en las categorías del usuario)"
                },
                "date": {
                    "type": "string",
                    "description": "Fecha en formato YYYY-MM-DD (si no se especifica, usar hoy)"
                }
            },
            "required": ["amount", "description", "transaction_type"]
        }
    },
    {
        "name": "create_category",
        "description": """
        Crea una nueva categoría para clasificar transacciones.
        Usa esta función cuando el usuario quiera crear una categoría que no existe.
        Ejemplos: "crea la categoría Veterinario", "añade una categoría para gastos de mascota"
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre de la nueva categoría"
                },
                "category_type": {
                    "type": "string",
                    "enum": ["expense", "income"],
                    "description": "Tipo: expense para gastos, income para ingresos"
                },
                "color": {
                    "type": "string",
                    "description": "Color en formato hexadecimal (#RRGGBB). Si no se especifica, usar un color por defecto"
                }
            },
            "required": ["name", "category_type"]
        }
    }
]

# Colores por defecto para categorías según tipo
DEFAULT_COLORS = {
    "expense": ["#EF4444", "#F97316", "#F59E0B", "#84CC16", "#06B6D4", "#8B5CF6", "#EC4899"],
    "income": ["#10B981", "#14B8A6", "#0EA5E9", "#6366F1", "#22C55E"]
}


class ChatService:
    """
    Servicio del agente conversacional financiero.

    Utiliza Gemini con function calling para:
    - Responder preguntas sobre finanzas del usuario
    - Proponer acciones (crear transacciones, categorías) que requieren confirmación
    """

    SYSTEM_PROMPT = """
Eres MyFi, un asistente financiero personal amigable y experto.

REGLAS IMPORTANTES:
1. Responde SIEMPRE en español, de forma natural, cercana y profesional
2. Tienes acceso completo a los datos financieros del usuario (cuentas, transacciones, presupuestos, etc.)
3. Sé conciso pero informativo. No uses más de 3-4 frases por respuesta a menos que se pida detalle
4. Usa emojis con moderación para hacer la conversación más amigable
5. Si no tienes datos suficientes para responder algo, dilo claramente
6. NO inventes datos que no estén en el contexto
7. Cuando el usuario pida crear algo (transacción, categoría), usa la función correspondiente
8. Para montos, usa siempre el formato español: 1.234,56 €

ACCIONES DISPONIBLES:
- create_transaction: Para registrar gastos o ingresos
- create_category: Para crear nuevas categorías

Cuando uses una función, el sistema pedirá confirmación al usuario antes de ejecutar.
Si el usuario menciona una categoría que no existe, sugiere crearla primero.

DATOS FINANCIEROS DEL USUARIO:
{context}
"""

    def __init__(self, db: Session, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.context_builder = ChatContextBuilder(db, user_id)
        self._model = None

    def _get_model(self):
        """Inicializa y retorna el modelo de Gemini."""
        if self._model is None:
            try:
                import google.generativeai as genai

                genai.configure(api_key=settings.GEMINI_API_KEY)

                # Configurar herramientas (function calling)
                tools = self._build_tools()

                self._model = genai.GenerativeModel(
                    model_name=settings.LLM_MODEL,
                    tools=tools,
                    system_instruction=None  # Lo pasaremos en el prompt
                )

                logger.info(f"Modelo Gemini inicializado: {settings.LLM_MODEL}")
            except ImportError:
                logger.error("google-generativeai no está instalado")
                raise Exception("google-generativeai package not installed")

        return self._model

    def _build_tools(self) -> List[Any]:
        """Construye las definiciones de herramientas para Gemini."""
        try:
            import google.generativeai as genai

            function_declarations = []
            for tool_def in TOOL_DEFINITIONS:
                func_decl = genai.protos.FunctionDeclaration(
                    name=tool_def["name"],
                    description=tool_def["description"].strip(),
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            k: genai.protos.Schema(
                                type=self._map_type(v.get("type", "string")),
                                description=v.get("description", ""),
                                enum=v.get("enum")
                            )
                            for k, v in tool_def["parameters"]["properties"].items()
                        },
                        required=tool_def["parameters"].get("required", [])
                    )
                )
                function_declarations.append(func_decl)

            return [genai.protos.Tool(function_declarations=function_declarations)]

        except Exception as e:
            logger.error(f"Error construyendo herramientas: {e}")
            return []

    def _map_type(self, type_str: str) -> Any:
        """Mapea tipos de JSON Schema a tipos de Gemini."""
        import google.generativeai as genai

        type_map = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.INTEGER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT
        }
        return type_map.get(type_str, genai.protos.Type.STRING)

    async def process_message(
        self,
        message: str,
        conversation_history: List[ChatMessage]
    ) -> ChatResponse:
        """
        Procesa un mensaje del usuario y genera una respuesta.

        Args:
            message: Mensaje actual del usuario
            conversation_history: Historial de mensajes previos

        Returns:
            ChatResponse con la respuesta del agente y posible acción propuesta
        """
        logger.info(f"Procesando mensaje para user_id: {self.user_id}")

        try:
            # 1. Construir contexto financiero
            financial_context = self.context_builder.build()

            # 2. Construir el prompt del sistema con el contexto
            system_prompt = self.SYSTEM_PROMPT.format(
                context=json.dumps(financial_context, indent=2, ensure_ascii=False)
            )

            # 3. Construir historial de conversación para Gemini
            gemini_history = self._build_gemini_history(conversation_history, system_prompt)

            # 4. Llamar a Gemini
            model = self._get_model()
            chat = model.start_chat(history=gemini_history)

            response = chat.send_message(message)

            # 5. Procesar la respuesta
            return self._process_gemini_response(response, financial_context)

        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            return ChatResponse(
                message=f"Lo siento, ha ocurrido un error al procesar tu mensaje. Por favor, inténtalo de nuevo.",
                proposed_action=None,
                suggested_questions=["¿Cuál es mi saldo actual?", "¿Cuánto he gastado este mes?"]
            )

    def _build_gemini_history(
        self,
        history: List[ChatMessage],
        system_prompt: str
    ) -> List[Dict[str, Any]]:
        """Construye el historial en formato Gemini."""
        import google.generativeai as genai

        gemini_history = []

        # Añadir el system prompt como primer mensaje del usuario
        # (Gemini no tiene un system prompt separado como OpenAI)
        if history:
            gemini_history.append(
                genai.protos.Content(
                    role="user",
                    parts=[genai.protos.Part(text=system_prompt + "\n\nUsuario: " + history[0].content)]
                )
            )

            # Añadir la primera respuesta del asistente
            if len(history) > 1:
                gemini_history.append(
                    genai.protos.Content(
                        role="model",
                        parts=[genai.protos.Part(text=history[1].content)]
                    )
                )

            # Añadir el resto del historial
            for i in range(2, len(history)):
                msg = history[i]
                role = "user" if msg.role == "user" else "model"
                gemini_history.append(
                    genai.protos.Content(
                        role=role,
                        parts=[genai.protos.Part(text=msg.content)]
                    )
                )

        return gemini_history

    def _process_gemini_response(
        self,
        response: Any,
        financial_context: Dict[str, Any]
    ) -> ChatResponse:
        """Procesa la respuesta de Gemini y extrae texto y/o function calls."""
        proposed_action = None
        message_text = ""

        # Verificar si hay function calls
        for candidate in response.candidates:
            for part in candidate.content.parts:
                # Texto normal
                if hasattr(part, 'text') and part.text:
                    message_text += part.text

                # Function call
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    proposed_action = self._build_proposed_action(
                        fc.name,
                        dict(fc.args),
                        financial_context
                    )

        # Si no hay mensaje pero hay acción, generar mensaje descriptivo
        if not message_text and proposed_action:
            message_text = f"Entendido. {proposed_action.description}. Por favor, confirma para proceder."

        # Generar preguntas sugeridas
        suggested_questions = self._generate_suggested_questions(financial_context)

        return ChatResponse(
            message=message_text.strip() or "¿En qué más puedo ayudarte?",
            proposed_action=proposed_action,
            suggested_questions=suggested_questions
        )

    def _build_proposed_action(
        self,
        function_name: str,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[ProposedAction]:
        """Construye una ProposedAction a partir de un function call de Gemini."""

        if function_name == "create_transaction":
            return self._build_transaction_action(args, context)
        elif function_name == "create_category":
            return self._build_category_action(args, context)

        return None

    def _build_transaction_action(
        self,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ProposedAction:
        """Construye la acción para crear una transacción."""
        amount = float(args.get("amount", 0))
        description = args.get("description", "")
        tx_type = args.get("transaction_type", "expense")
        category_name = args.get("category_name")
        tx_date = args.get("date", date.today().isoformat())
        account_name = args.get("account_name")

        # Buscar la cuenta (primera activa si no se especifica)
        account = self._find_account(account_name, context)
        if not account:
            # Fallback a la primera cuenta
            accounts = context.get("cuentas", {}).get("cuentas", [])
            if accounts:
                account = accounts[0]

        # Buscar la categoría
        category_id = None
        if category_name:
            category = self.db.query(Category).filter(
                Category.user_id == self.user_id,
                Category.name.ilike(f"%{category_name}%")
            ).first()
            if category:
                category_id = str(category.id)

        # Formatear monto para visualización
        formatted_amount = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        type_label = "gasto" if tx_type == "expense" else "ingreso"

        return ProposedAction(
            type="create_transaction",
            description=f"Crear {type_label} de {formatted_amount} - {description}" +
                       (f" (categoría: {category_name})" if category_name else ""),
            endpoint="POST /api/transactions",
            data={
                "account_id": account.get("id") if account else None,
                "amount": -amount if tx_type == "expense" else amount,
                "date": tx_date,
                "description": description,
                "type": tx_type,
                "category_id": category_id,
                "source": "chat_agent"
            }
        )

    def _build_category_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para crear una categoría."""
        name = args.get("name", "")
        cat_type = args.get("category_type", "expense")
        color = args.get("color")

        # Asignar color por defecto si no se especifica
        if not color:
            import random
            colors = DEFAULT_COLORS.get(cat_type, DEFAULT_COLORS["expense"])
            color = random.choice(colors)

        type_label = "gasto" if cat_type == "expense" else "ingreso"

        return ProposedAction(
            type="create_category",
            description=f"Crear categoría '{name}' (tipo: {type_label})",
            endpoint="POST /api/categories",
            data={
                "name": name,
                "type": cat_type,
                "color": color
            }
        )

    def _find_account(
        self,
        account_name: Optional[str],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Busca una cuenta por nombre en el contexto."""
        if not account_name:
            return None

        accounts = context.get("cuentas", {}).get("cuentas", [])
        account_name_lower = account_name.lower()

        for acc in accounts:
            if account_name_lower in acc.get("nombre", "").lower():
                return acc

        return None

    def _generate_suggested_questions(self, context: Dict[str, Any]) -> List[str]:
        """Genera preguntas sugeridas basadas en el contexto."""
        questions = []

        # Basado en datos disponibles
        health = context.get("salud_financiera", {})
        budgets = context.get("presupuestos", [])
        categories = context.get("categorias_gasto", [])

        if health.get("tasa_ahorro_actual", 0) < 10:
            questions.append("¿Cómo puedo mejorar mi tasa de ahorro?")

        if budgets:
            exceeded = [b for b in budgets if b.get("estado") == "excedido"]
            if exceeded:
                questions.append(f"¿Por qué me he excedido en {exceeded[0]['categoria']}?")

        if categories:
            top_cat = categories[0].get("nombre", "")
            questions.append(f"¿Cómo ha evolucionado mi gasto en {top_cat}?")

        # Preguntas genéricas
        generic = [
            "¿Cuál es mi situación financiera actual?",
            "¿Cuánto he ahorrado este mes?",
            "¿Cuáles son mis mayores gastos?",
            "¿Cómo puedo reducir mis gastos?",
            "Muéstrame un resumen de mis cuentas"
        ]

        # Completar hasta 3 preguntas
        import random
        while len(questions) < 3 and generic:
            q = random.choice(generic)
            if q not in questions:
                questions.append(q)
                generic.remove(q)

        return questions[:3]
