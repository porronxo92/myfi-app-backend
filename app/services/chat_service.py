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
    # ============================================
    # TRANSACCIONES
    # ============================================
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
        "name": "update_transaction",
        "description": """
        Modifica una transacción existente.
        Usa esta función cuando el usuario quiera editar o corregir una transacción.
        Necesitas el ID de la transacción (puedes buscarlo en el contexto de transacciones recientes).
        Ejemplos: "cambia el monto del gasto de Mercadona a 50€", "corrige la categoría del último gasto"
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "ID (UUID) de la transacción a modificar"
                },
                "amount": {
                    "type": "number",
                    "description": "Nuevo monto (opcional)"
                },
                "description": {
                    "type": "string",
                    "description": "Nueva descripción (opcional)"
                },
                "category_name": {
                    "type": "string",
                    "description": "Nueva categoría (opcional)"
                },
                "date": {
                    "type": "string",
                    "description": "Nueva fecha en formato YYYY-MM-DD (opcional)"
                }
            },
            "required": ["transaction_id"]
        }
    },
    {
        "name": "delete_transaction",
        "description": """
        Elimina una transacción existente.
        Usa esta función cuando el usuario quiera borrar una transacción.
        Ejemplos: "elimina el gasto de Mercadona", "borra la última transacción"
        IMPORTANTE: Esta acción es irreversible. Confirma siempre con el usuario.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "ID (UUID) de la transacción a eliminar"
                },
                "description_confirm": {
                    "type": "string",
                    "description": "Descripción de la transacción para confirmar (seguridad)"
                }
            },
            "required": ["transaction_id"]
        }
    },
    # ============================================
    # CATEGORÍAS
    # ============================================
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
    },
    {
        "name": "update_category",
        "description": """
        Modifica una categoría existente.
        Usa esta función cuando el usuario quiera cambiar el nombre o color de una categoría.
        Ejemplos: "renombra la categoría Ocio a Entretenimiento", "cambia el color de Supermercado a verde"
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "category_name": {
                    "type": "string",
                    "description": "Nombre actual de la categoría a modificar"
                },
                "new_name": {
                    "type": "string",
                    "description": "Nuevo nombre (opcional)"
                },
                "new_color": {
                    "type": "string",
                    "description": "Nuevo color en formato hexadecimal (#RRGGBB) (opcional)"
                }
            },
            "required": ["category_name"]
        }
    },
    {
        "name": "delete_category",
        "description": """
        Elimina una categoría existente.
        Usa esta función cuando el usuario quiera borrar una categoría.
        Las transacciones asociadas quedarán sin categoría asignada.
        Ejemplos: "elimina la categoría Veterinario", "borra la categoría Otros gastos"
        IMPORTANTE: Esta acción es irreversible.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "category_name": {
                    "type": "string",
                    "description": "Nombre de la categoría a eliminar"
                }
            },
            "required": ["category_name"]
        }
    },
    # ============================================
    # CUENTAS
    # ============================================
    {
        "name": "create_account",
        "description": """
        Crea una nueva cuenta bancaria o de efectivo.
        Usa esta función cuando el usuario quiera añadir una cuenta nueva.
        Ejemplos: "crea una cuenta de ahorro en ING", "añade mi cuenta de Revolut"
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre descriptivo de la cuenta"
                },
                "account_type": {
                    "type": "string",
                    "enum": ["checking", "savings", "investment", "credit_card", "cash"],
                    "description": "Tipo: checking (corriente), savings (ahorro), investment (inversión), credit_card (tarjeta crédito), cash (efectivo)"
                },
                "balance": {
                    "type": "number",
                    "description": "Saldo inicial de la cuenta (por defecto 0)"
                },
                "bank_name": {
                    "type": "string",
                    "description": "Nombre del banco (opcional)"
                },
                "currency": {
                    "type": "string",
                    "description": "Moneda ISO (EUR, USD, etc.). Por defecto EUR"
                }
            },
            "required": ["name", "account_type"]
        }
    },
    {
        "name": "update_account",
        "description": """
        Modifica una cuenta existente.
        Usa esta función cuando el usuario quiera editar datos de una cuenta.
        Ejemplos: "cambia el nombre de mi cuenta Santander a Cuenta Principal", "actualiza el saldo de efectivo a 200€"
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "account_name": {
                    "type": "string",
                    "description": "Nombre actual de la cuenta a modificar"
                },
                "new_name": {
                    "type": "string",
                    "description": "Nuevo nombre (opcional)"
                },
                "new_balance": {
                    "type": "number",
                    "description": "Nuevo saldo (opcional)"
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Si la cuenta está activa (opcional)"
                }
            },
            "required": ["account_name"]
        }
    },
    {
        "name": "delete_account",
        "description": """
        Elimina una cuenta existente.
        Usa esta función cuando el usuario quiera borrar una cuenta.
        IMPORTANTE: Esto eliminará también todas las transacciones de esa cuenta.
        Ejemplos: "elimina mi cuenta de Revolut", "borra la cuenta de efectivo"
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "account_name": {
                    "type": "string",
                    "description": "Nombre de la cuenta a eliminar"
                }
            },
            "required": ["account_name"]
        }
    },
    # ============================================
    # OPERACIONES BATCH (múltiples items)
    # ============================================
    {
        "name": "create_accounts_batch",
        "description": """
        Crea MÚLTIPLES cuentas de una sola vez.
        USA ESTA FUNCIÓN cuando el usuario quiera crear varias cuentas en un solo mensaje.
        Ejemplos: "crea estas cuentas: ING, Revolut, MyInvestor", "añade mis cuentas de ahorro e inversión"
        IMPORTANTE: Usa esta función SIEMPRE que el usuario mencione más de una cuenta a crear.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "accounts": {
                    "type": "array",
                    "description": "Array de cuentas a crear",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Nombre de la cuenta"},
                            "account_type": {"type": "string", "enum": ["checking", "savings", "investment", "credit_card", "cash"]},
                            "bank_name": {"type": "string", "description": "Nombre del banco"},
                            "balance": {"type": "number", "description": "Saldo inicial"},
                            "currency": {"type": "string", "description": "Moneda (EUR por defecto)"}
                        },
                        "required": ["name", "account_type"]
                    }
                }
            },
            "required": ["accounts"]
        }
    },
    {
        "name": "create_categories_batch",
        "description": """
        Crea MÚLTIPLES categorías de una sola vez.
        USA ESTA FUNCIÓN cuando el usuario quiera crear varias categorías en un solo mensaje.
        Ejemplos: "crea las categorías: Comida, Transporte, Ocio", "añade categorías de gasto para hogar"
        IMPORTANTE: Usa esta función SIEMPRE que el usuario mencione más de una categoría a crear.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "categories": {
                    "type": "array",
                    "description": "Array de categorías a crear",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Nombre de la categoría"},
                            "category_type": {"type": "string", "enum": ["expense", "income"]},
                            "color": {"type": "string", "description": "Color hexadecimal (#RRGGBB)"}
                        },
                        "required": ["name", "category_type"]
                    }
                }
            },
            "required": ["categories"]
        }
    },
    {
        "name": "create_transactions_batch",
        "description": """
        Crea MÚLTIPLES transacciones de una sola vez.
        USA ESTA FUNCIÓN cuando el usuario quiera registrar varios gastos o ingresos en un solo mensaje.
        Ejemplos: "añade estos gastos: 50€ Mercadona, 30€ gasolina, 15€ café", "registra mis compras del fin de semana"
        IMPORTANTE: Usa esta función SIEMPRE que el usuario mencione más de una transacción a crear.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "transactions": {
                    "type": "array",
                    "description": "Array de transacciones a crear",
                    "items": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "number", "description": "Monto (positivo)"},
                            "description": {"type": "string", "description": "Descripción"},
                            "transaction_type": {"type": "string", "enum": ["expense", "income"]},
                            "category_name": {"type": "string", "description": "Nombre de categoría"},
                            "account_name": {"type": "string", "description": "Nombre de cuenta"},
                            "date": {"type": "string", "description": "Fecha YYYY-MM-DD"}
                        },
                        "required": ["amount", "description", "transaction_type"]
                    }
                }
            },
            "required": ["transactions"]
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
7. Cuando el usuario pida crear, modificar o eliminar algo, usa la función correspondiente
8. Para montos, usa siempre el formato español: 1.234,56 €
9. Para operaciones de UPDATE o DELETE, busca primero el ID en el contexto financiero
10. SIEMPRE pide confirmación antes de eliminar (el sistema mostrará un modal)

ACCIONES DISPONIBLES (CRUD):

📝 TRANSACCIONES:
- create_transaction: Crear gasto o ingreso
- update_transaction: Modificar una transacción existente
- delete_transaction: Eliminar una transacción
- create_transactions_batch: ⚡ Crear MÚLTIPLES transacciones de una vez

📂 CATEGORÍAS:
- create_category: Crear nueva categoría
- update_category: Modificar nombre/color de categoría
- delete_category: Eliminar categoría (transacciones quedan sin categoría)
- create_categories_batch: ⚡ Crear MÚLTIPLES categorías de una vez

💳 CUENTAS:
- create_account: Crear nueva cuenta bancaria/efectivo
- update_account: Modificar datos de cuenta
- delete_account: Eliminar cuenta (¡CUIDADO! elimina sus transacciones)
- create_accounts_batch: ⚡ Crear MÚLTIPLES cuentas de una vez

⚡ IMPORTANTE - OPERACIONES BATCH:
Cuando el usuario pida crear MÁS DE UN elemento del mismo tipo, USA SIEMPRE la función _batch correspondiente.
Por ejemplo:
- "Crea cuentas ING, Revolut y MyInvestor" → usa create_accounts_batch
- "Añade categorías Comida, Transporte y Ocio" → usa create_categories_batch
- "Registra estos gastos: 50€ Mercadona, 30€ gasolina" → usa create_transactions_batch

Cuando uses una función, el sistema pedirá confirmación al usuario antes de ejecutar.
Si el usuario menciona una categoría que no existe, sugiere crearla primero.
Para operaciones de eliminación, siempre advierte al usuario de las consecuencias.

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

        # Transacciones
        if function_name == "create_transaction":
            return self._build_create_transaction_action(args, context)
        elif function_name == "update_transaction":
            return self._build_update_transaction_action(args, context)
        elif function_name == "delete_transaction":
            return self._build_delete_transaction_action(args, context)
        # Categorías
        elif function_name == "create_category":
            return self._build_create_category_action(args, context)
        elif function_name == "update_category":
            return self._build_update_category_action(args, context)
        elif function_name == "delete_category":
            return self._build_delete_category_action(args, context)
        # Cuentas
        elif function_name == "create_account":
            return self._build_create_account_action(args, context)
        elif function_name == "update_account":
            return self._build_update_account_action(args, context)
        elif function_name == "delete_account":
            return self._build_delete_account_action(args, context)
        # Batch operations
        elif function_name == "create_accounts_batch":
            return self._build_accounts_batch_action(args, context)
        elif function_name == "create_categories_batch":
            return self._build_categories_batch_action(args, context)
        elif function_name == "create_transactions_batch":
            return self._build_transactions_batch_action(args, context)

        return None

    # ============================================
    # BUILDERS DE TRANSACCIONES
    # ============================================

    def _build_create_transaction_action(
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

    def _build_create_category_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
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

    # ============================================
    # BUILDERS DE UPDATE/DELETE TRANSACCIONES
    # ============================================

    def _build_update_transaction_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para actualizar una transacción."""
        tx_id = args.get("transaction_id", "")

        update_data = {}
        description_parts = []

        if args.get("amount"):
            update_data["amount"] = float(args["amount"])
            description_parts.append(f"monto: {args['amount']}€")

        if args.get("description"):
            update_data["description"] = args["description"]
            description_parts.append(f"descripción: {args['description']}")

        if args.get("category_name"):
            category = self.db.query(Category).filter(
                Category.user_id == self.user_id,
                Category.name.ilike(f"%{args['category_name']}%")
            ).first()
            if category:
                update_data["category_id"] = str(category.id)
                description_parts.append(f"categoría: {args['category_name']}")

        if args.get("date"):
            update_data["date"] = args["date"]
            description_parts.append(f"fecha: {args['date']}")

        return ProposedAction(
            type="update_transaction",
            description=f"Modificar transacción: {', '.join(description_parts)}" if description_parts else "Modificar transacción",
            endpoint=f"PUT /api/transactions/{tx_id}",
            data=update_data
        )

    def _build_delete_transaction_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para eliminar una transacción."""
        tx_id = args.get("transaction_id", "")
        confirm_desc = args.get("description_confirm", "")

        return ProposedAction(
            type="delete_transaction",
            description=f"⚠️ ELIMINAR transacción{': ' + confirm_desc if confirm_desc else ''} (irreversible)",
            endpoint=f"DELETE /api/transactions/{tx_id}",
            data={}
        )

    # ============================================
    # BUILDERS DE UPDATE/DELETE CATEGORÍAS
    # ============================================

    def _build_update_category_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para actualizar una categoría."""
        category_name = args.get("category_name", "")

        # Buscar la categoría por nombre
        category = self.db.query(Category).filter(
            Category.user_id == self.user_id,
            Category.name.ilike(f"%{category_name}%")
        ).first()

        category_id = str(category.id) if category else ""

        update_data = {}
        description_parts = []

        if args.get("new_name"):
            update_data["name"] = args["new_name"]
            description_parts.append(f"nombre: '{args['new_name']}'")

        if args.get("new_color"):
            update_data["color"] = args["new_color"]
            description_parts.append(f"color: {args['new_color']}")

        return ProposedAction(
            type="update_category",
            description=f"Modificar categoría '{category_name}': {', '.join(description_parts)}" if description_parts else f"Modificar categoría '{category_name}'",
            endpoint=f"PUT /api/categories/{category_id}",
            data=update_data
        )

    def _build_delete_category_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para eliminar una categoría."""
        category_name = args.get("category_name", "")

        # Buscar la categoría por nombre
        category = self.db.query(Category).filter(
            Category.user_id == self.user_id,
            Category.name.ilike(f"%{category_name}%")
        ).first()

        category_id = str(category.id) if category else ""

        return ProposedAction(
            type="delete_category",
            description=f"⚠️ ELIMINAR categoría '{category_name}' (las transacciones quedarán sin categoría)",
            endpoint=f"DELETE /api/categories/{category_id}",
            data={}
        )

    # ============================================
    # BUILDERS DE CUENTAS
    # ============================================

    def _build_create_account_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para crear una cuenta."""
        name = args.get("name", "")
        account_type = args.get("account_type", "checking")
        balance = float(args.get("balance", 0))
        bank_name = args.get("bank_name", "")
        currency = args.get("currency", "EUR")

        type_labels = {
            "checking": "corriente",
            "savings": "ahorro",
            "investment": "inversión",
            "credit_card": "tarjeta crédito",
            "cash": "efectivo"
        }
        type_label = type_labels.get(account_type, account_type)

        return ProposedAction(
            type="create_account",
            description=f"Crear cuenta '{name}' ({type_label})" + (f" en {bank_name}" if bank_name else ""),
            endpoint="POST /api/accounts",
            data={
                "name": name,
                "type": account_type,
                "balance": balance,
                "bank_name": bank_name or None,
                "currency": currency,
                "is_active": True
            }
        )

    def _build_update_account_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para actualizar una cuenta."""
        account_name = args.get("account_name", "")

        # Buscar la cuenta por nombre
        account = self._find_account(account_name, context)
        account_id = account.get("id", "") if account else ""

        update_data = {}
        description_parts = []

        if args.get("new_name"):
            update_data["name"] = args["new_name"]
            description_parts.append(f"nombre: '{args['new_name']}'")

        if args.get("new_balance") is not None:
            update_data["balance"] = float(args["new_balance"])
            formatted_balance = f"{args['new_balance']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
            description_parts.append(f"saldo: {formatted_balance}")

        if args.get("is_active") is not None:
            update_data["is_active"] = args["is_active"]
            description_parts.append(f"activa: {'Sí' if args['is_active'] else 'No'}")

        return ProposedAction(
            type="update_account",
            description=f"Modificar cuenta '{account_name}': {', '.join(description_parts)}" if description_parts else f"Modificar cuenta '{account_name}'",
            endpoint=f"PUT /api/accounts/{account_id}",
            data=update_data
        )

    def _build_delete_account_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para eliminar una cuenta."""
        account_name = args.get("account_name", "")

        # Buscar la cuenta por nombre
        account = self._find_account(account_name, context)
        account_id = account.get("id", "") if account else ""

        return ProposedAction(
            type="delete_account",
            description=f"⚠️ ELIMINAR cuenta '{account_name}' (¡SE BORRARÁN TODAS SUS TRANSACCIONES!)",
            endpoint=f"DELETE /api/accounts/{account_id}",
            data={}
        )

    # ============================================
    # BUILDERS BATCH (múltiples items)
    # ============================================

    def _build_accounts_batch_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para crear múltiples cuentas."""
        accounts_data = args.get("accounts", [])

        type_labels = {
            "checking": "corriente",
            "savings": "ahorro",
            "investment": "inversión",
            "credit_card": "tarjeta crédito",
            "cash": "efectivo"
        }

        # Construir datos para el batch
        items = []
        descriptions = []
        for acc in accounts_data:
            name = acc.get("name", "")
            account_type = acc.get("account_type", "checking")
            balance = float(acc.get("balance", 0))
            bank_name = acc.get("bank_name", "")
            currency = acc.get("currency", "EUR")

            items.append({
                "name": name,
                "type": account_type,
                "balance": balance,
                "bank_name": bank_name or None,
                "currency": currency,
                "is_active": True
            })

            type_label = type_labels.get(account_type, account_type)
            desc = f"'{name}' ({type_label})"
            if bank_name:
                desc += f" en {bank_name}"
            descriptions.append(desc)

        return ProposedAction(
            type="create_accounts_batch",
            description=f"Crear {len(items)} cuentas: {', '.join(descriptions)}",
            endpoint="POST /api/accounts/batch",
            data={"accounts": items}
        )

    def _build_categories_batch_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para crear múltiples categorías."""
        import random
        categories_data = args.get("categories", [])

        # Construir datos para el batch
        items = []
        descriptions = []
        for cat in categories_data:
            name = cat.get("name", "")
            cat_type = cat.get("category_type", "expense")
            color = cat.get("color")

            # Asignar color por defecto si no se especifica
            if not color:
                colors = DEFAULT_COLORS.get(cat_type, DEFAULT_COLORS["expense"])
                color = random.choice(colors)

            items.append({
                "name": name,
                "type": cat_type,
                "color": color
            })

            type_label = "gasto" if cat_type == "expense" else "ingreso"
            descriptions.append(f"'{name}' ({type_label})")

        return ProposedAction(
            type="create_categories_batch",
            description=f"Crear {len(items)} categorías: {', '.join(descriptions)}",
            endpoint="POST /api/categories/batch",
            data={"categories": items}
        )

    def _build_transactions_batch_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> ProposedAction:
        """Construye la acción para crear múltiples transacciones."""
        transactions_data = args.get("transactions", [])

        # Obtener cuenta por defecto
        accounts = context.get("cuentas", {}).get("cuentas", [])
        default_account = accounts[0] if accounts else None

        items = []
        descriptions = []
        total_expense = 0
        total_income = 0

        for tx in transactions_data:
            amount = float(tx.get("amount", 0))
            description = tx.get("description", "")
            tx_type = tx.get("transaction_type", "expense")
            category_name = tx.get("category_name")
            account_name = tx.get("account_name")
            tx_date = tx.get("date", date.today().isoformat())

            # Buscar cuenta
            account = self._find_account(account_name, context) if account_name else default_account

            # Buscar categoría
            category_id = None
            if category_name:
                category = self.db.query(Category).filter(
                    Category.user_id == self.user_id,
                    Category.name.ilike(f"%{category_name}%")
                ).first()
                if category:
                    category_id = str(category.id)

            items.append({
                "account_id": account.get("id") if account else None,
                "amount": -amount if tx_type == "expense" else amount,
                "date": tx_date,
                "description": description,
                "type": tx_type,
                "category_id": category_id,
                "source": "chat_agent"
            })

            # Acumular totales
            if tx_type == "expense":
                total_expense += amount
            else:
                total_income += amount

            formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + "€"
            descriptions.append(f"{description} ({formatted})")

        # Construir descripción resumen
        summary_parts = []
        if total_expense > 0:
            formatted_expense = f"{total_expense:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + "€"
            summary_parts.append(f"{formatted_expense} en gastos")
        if total_income > 0:
            formatted_income = f"{total_income:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + "€"
            summary_parts.append(f"{formatted_income} en ingresos")

        return ProposedAction(
            type="create_transactions_batch",
            description=f"Crear {len(items)} transacciones ({' y '.join(summary_parts)}): {', '.join(descriptions[:3])}" +
                       (f"..." if len(descriptions) > 3 else ""),
            endpoint="POST /api/transactions/batch",
            data={"transactions": items}
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
