"""
Prompt Sanitizer - Protección contra Prompt Injection
=====================================================

Módulo de seguridad para detectar y mitigar intentos de prompt injection
en el sistema de chat conversacional con Gemini.

Estrategias implementadas:
1. Detección de patrones peligrosos (moderado, evita falsos positivos)
2. Sanitización de inputs del usuario
3. Validación del historial de conversación
4. Logging de intentos sospechosos
"""

import re
from typing import List, Tuple, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PromptSanitizer:
    """
    Sanitizador de prompts para prevenir ataques de prompt injection.

    Implementa detección moderada: bloquea patrones obvios de injection
    pero permite consultas legítimas que podrían tener falsos positivos.
    """

    # Patrones de injection conocidos (moderado - no demasiado agresivo)
    DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
        # Intentos de ignorar instrucciones (español)
        (r"ignora\s+(todas?\s+)?(las?\s+)?instrucciones", "ignore_instructions_es"),
        (r"olvida\s+(todo\s+)?(lo\s+)?anterior", "forget_previous_es"),
        (r"olvida\s+.*instrucciones", "forget_instructions_es"),
        (r"nuevas?\s+instrucciones", "new_instructions_es"),
        (r"cambia\s+tu\s+rol", "change_role_es"),
        (r"ahora\s+eres", "now_you_are_es"),
        (r"tu\s+nuevo\s+objetivo", "new_objective_es"),

        # Intentos de ignorar instrucciones (inglés)
        (r"ignore\s+(all\s+)?(previous\s+)?instructions", "ignore_instructions_en"),
        (r"ignore\s+(the\s+)?instructions", "ignore_instructions_en2"),
        (r"forget\s+(everything|all|previous)", "forget_previous_en"),
        (r"new\s+instructions", "new_instructions_en"),
        (r"you\s+are\s+now", "you_are_now_en"),
        (r"your\s+new\s+(role|goal|objective)", "new_role_en"),

        # Intentos de extraer información del sistema
        (r"(muestra|revela|ense[ñn]a)\s+(el\s+)?(system\s+)?prompt", "reveal_prompt_es"),
        (r"(show|reveal|display)\s+.*(system\s+)?prompt", "reveal_prompt_en"),
        (r"show\s+me\s+.*(system|prompt)", "show_prompt_en"),
        (r"(muestra|revela)\s+(el\s+)?(contenido|datos?)\s+(del\s+)?contexto", "reveal_context_es"),
        (r"(show|reveal)\s+(the\s+)?context\s+(data|content|json)", "reveal_context_en"),
        (r"dame\s+(todo\s+)?(el\s+)?json", "give_json_es"),
        (r"print\s+(all\s+)?internal", "print_internal"),

        # Intentos de acceder a datos de otros usuarios
        (r"datos?\s+de\s+otros?\s+usuarios?", "other_users_data_es"),
        (r"other\s+users?\s+(data|info)", "other_users_data_en"),
        (r"(all|every)\s+users?\s+", "all_users_en"),
        (r"(todos?\s+los?\s+)?usuarios", "all_users_es"),

        # Intentos de obtener credenciales/secretos
        (r"(api|secret)\s*key", "api_key"),
        (r"(password|contrase[ñn]a)", "password"),
        (r"(database|db)\s*(url|connection|credentials)", "db_credentials"),
        (r"(token|jwt)\s+secret", "token_secret"),

        # Intentos de manipular acciones
        (r"(ejecuta|ejecutar)\s+sin\s+(confirmaci[oó]n|preguntar)", "execute_without_confirm_es"),
        (r"execute\s+without\s+(confirm|asking)", "execute_without_confirm_en"),
        (r"bypass\s+(security|validation|auth)", "bypass_security"),
        (r"(saltar|omitir)\s+(validaci[oó]n|seguridad)", "bypass_security_es"),

        # Delimitadores sospechosos que podrían indicar injection
        (r"\]\s*\n.*instrucciones", "bracket_injection"),
        (r"<\/?system", "xml_system_tag"),
        (r"\{\"?system", "json_system"),
    ]

    # Patrones que detectamos pero NO bloqueamos (solo logging)
    SUSPICIOUS_PATTERNS: List[Tuple[str, str]] = [
        (r"como\s+(asistente|ia|ai)", "role_reference_es"),
        (r"as\s+an?\s+(ai|assistant)", "role_reference_en"),
        (r"(confidencial|secreto|interno)", "confidential_es"),
        (r"(confidential|secret|internal)", "confidential_en"),
    ]

    # Longitud máxima permitida para mensajes
    MAX_MESSAGE_LENGTH = 4000
    MAX_HISTORY_LENGTH = 50

    @classmethod
    def is_dangerous(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Detecta si el texto contiene patrones de prompt injection.

        Args:
            text: Texto a analizar

        Returns:
            Tupla (es_peligroso, nombre_del_patrón)
        """
        if not text:
            return False, None

        text_lower = text.lower()

        for pattern, name in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE | re.MULTILINE):
                return True, name

        return False, None

    @classmethod
    def is_suspicious(cls, text: str) -> bool:
        """
        Detecta si el texto es sospechoso (para logging, no bloqueo).

        Args:
            text: Texto a analizar

        Returns:
            True si contiene patrones sospechosos
        """
        if not text:
            return False

        text_lower = text.lower()

        # Primero verificar si es peligroso
        is_danger, _ = cls.is_dangerous(text)
        if is_danger:
            return True

        # Luego verificar patrones sospechosos
        for pattern, _ in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

        return False

    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        Sanitiza el texto removiendo o neutralizando patrones peligrosos.

        Args:
            text: Texto a sanitizar

        Returns:
            Texto sanitizado
        """
        if not text:
            return ""

        # Truncar si excede longitud máxima
        if len(text) > cls.MAX_MESSAGE_LENGTH:
            text = text[:cls.MAX_MESSAGE_LENGTH]
            logger.warning("Mensaje truncado por exceder longitud máxima")

        # Neutralizar delimitadores que podrían usarse para injection
        # Reemplazar secuencias de corchetes/llaves sospechosas
        text = re.sub(r'\]\s*\n\s*\[', '] [', text)
        text = re.sub(r'\}\s*\n\s*\{', '} {', text)

        # Escapar tags XML/HTML sospechosos
        text = re.sub(r'<\s*/?system', '&lt;system', text, flags=re.IGNORECASE)
        text = re.sub(r'<\s*/?instructions', '&lt;instructions', text, flags=re.IGNORECASE)

        return text

    @classmethod
    def validate_message(cls, message: str, user_id: str = "unknown") -> Tuple[bool, str]:
        """
        Valida un mensaje del usuario.

        Args:
            message: Mensaje a validar
            user_id: ID del usuario para logging

        Returns:
            Tupla (es_válido, mensaje_sanitizado_o_error)
        """
        if not message or not message.strip():
            return False, "Mensaje vacío"

        # Verificar longitud
        if len(message) > cls.MAX_MESSAGE_LENGTH:
            logger.warning(f"Mensaje muy largo de user {user_id}: {len(message)} chars")

        # Verificar patrones peligrosos
        is_danger, pattern = cls.is_dangerous(message)
        if is_danger:
            logger.warning(
                f"Posible prompt injection detectado | "
                f"user_id={user_id} | pattern={pattern} | "
                f"message_preview={message[:100]}..."
            )
            return False, "No puedo procesar ese tipo de mensaje."

        # Log si es sospechoso pero no bloqueante
        if cls.is_suspicious(message):
            logger.info(
                f"Mensaje sospechoso (no bloqueado) | "
                f"user_id={user_id} | message_preview={message[:100]}..."
            )

        # Sanitizar y retornar
        sanitized = cls.sanitize(message)
        return True, sanitized

    @classmethod
    def validate_history(
        cls,
        history: List[any],
        user_id: str = "unknown"
    ) -> List[any]:
        """
        Valida y sanitiza el historial de conversación.

        Args:
            history: Lista de ChatMessage
            user_id: ID del usuario para logging

        Returns:
            Historial validado y sanitizado
        """
        if not history:
            return []

        # Limitar longitud del historial
        if len(history) > cls.MAX_HISTORY_LENGTH:
            logger.warning(
                f"Historial muy largo de user {user_id}: {len(history)} mensajes, "
                f"truncando a {cls.MAX_HISTORY_LENGTH}"
            )
            history = history[-cls.MAX_HISTORY_LENGTH:]

        validated_history = []
        injection_attempts = 0

        for i, msg in enumerate(history):
            content = getattr(msg, 'content', '') if hasattr(msg, 'content') else str(msg)
            role = getattr(msg, 'role', 'user') if hasattr(msg, 'role') else 'user'

            # Validar rol
            if role not in ('user', 'assistant'):
                logger.warning(f"Rol inválido en historial: {role}")
                role = 'user'

            # Verificar injection en contenido
            is_danger, pattern = cls.is_dangerous(content)
            if is_danger:
                injection_attempts += 1
                logger.warning(
                    f"Injection detectada en historial | "
                    f"user_id={user_id} | index={i} | pattern={pattern}"
                )
                # Reemplazar contenido malicioso
                content = "[Contenido removido por seguridad]"
            else:
                # Sanitizar contenido
                content = cls.sanitize(content)

            # Reconstruir mensaje validado
            if hasattr(msg, '__class__') and hasattr(msg.__class__, '__name__'):
                # Es un objeto Pydantic, crear copia con contenido sanitizado
                try:
                    from app.schemas.chat import ChatMessage
                    validated_history.append(ChatMessage(role=role, content=content))
                except ImportError:
                    validated_history.append({"role": role, "content": content})
            else:
                validated_history.append({"role": role, "content": content})

        if injection_attempts > 0:
            logger.warning(
                f"Historial contenía {injection_attempts} intentos de injection | "
                f"user_id={user_id}"
            )

        return validated_history

    @classmethod
    def get_safe_response(cls) -> str:
        """
        Retorna una respuesta segura para cuando se detecta injection.
        """
        return (
            "No puedo procesar ese mensaje. "
            "¿En qué más puedo ayudarte con tus finanzas personales?"
        )
