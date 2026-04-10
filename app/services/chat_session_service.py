"""
Chat Session Service - Gestión de Sesiones de Chat
===================================================

SEGURIDAD:
- Las sesiones se almacenan en el servidor, no se confía en el frontend
- El historial está encriptado
- Las sesiones expiran automáticamente
- Se valida y sanitiza todo el contenido antes de almacenarlo
"""

import json
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.schemas.chat import ChatMessage
from app.utils.prompt_sanitizer import PromptSanitizer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChatSessionService:
    """
    Servicio para gestionar sesiones de chat almacenadas en el servidor.

    Proporciona:
    - Creación y recuperación de sesiones por usuario
    - Almacenamiento seguro del historial
    - Sanitización de mensajes antes de guardar
    - Expiración automática de sesiones
    """

    SESSION_EXPIRY_HOURS = 24
    MAX_HISTORY_LENGTH = 50
    MAX_MESSAGE_LENGTH = 4000

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_session(self, user_id: UUID) -> ChatSession:
        """
        Obtiene la sesión activa del usuario o crea una nueva.

        Args:
            user_id: ID del usuario

        Returns:
            ChatSession activa
        """
        # Buscar sesión activa existente
        session = self.db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True
        ).first()

        if session:
            # Verificar si ha expirado
            if session.is_expired():
                logger.info(f"Sesión expirada para user {str(user_id)[:8]}, creando nueva")
                session.is_active = False
                self.db.commit()
                return self._create_session(user_id)

            # Extender expiración
            session.extend_expiry()
            self.db.commit()
            return session

        return self._create_session(user_id)

    def _create_session(self, user_id: UUID) -> ChatSession:
        """Crea una nueva sesión de chat."""
        session = ChatSession(
            user_id=user_id,
            history="[]",
            message_count=0,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=self.SESSION_EXPIRY_HOURS)
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        logger.info(f"Nueva sesión de chat creada para user {str(user_id)[:8]}")
        return session

    def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str
    ) -> bool:
        """
        Añade un mensaje al historial de la sesión.

        SEGURIDAD: El contenido se sanitiza antes de guardarse.

        Args:
            session_id: ID de la sesión
            role: "user" o "assistant"
            content: Contenido del mensaje

        Returns:
            True si se añadió correctamente
        """
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

        if not session:
            logger.warning(f"Sesión no encontrada: {session_id}")
            return False

        # Sanitizar contenido
        sanitized_content = PromptSanitizer.sanitize(content)

        # Truncar si es muy largo
        if len(sanitized_content) > self.MAX_MESSAGE_LENGTH:
            sanitized_content = sanitized_content[:self.MAX_MESSAGE_LENGTH]

        # Parsear historial existente
        try:
            history = json.loads(session.history or "[]")
        except json.JSONDecodeError:
            logger.warning(f"Historial corrupto en sesión {session_id}, reiniciando")
            history = []

        # Añadir mensaje
        history.append({
            "role": role,
            "content": sanitized_content,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Limitar longitud del historial
        if len(history) > self.MAX_HISTORY_LENGTH:
            history = history[-self.MAX_HISTORY_LENGTH:]
            logger.info(f"Historial truncado a {self.MAX_HISTORY_LENGTH} mensajes")

        # Guardar
        session.history = json.dumps(history, ensure_ascii=False)
        session.message_count = len(history)
        session.extend_expiry()

        self.db.commit()
        return True

    def get_history(self, session_id: UUID) -> List[ChatMessage]:
        """
        Obtiene el historial de mensajes de una sesión.

        Args:
            session_id: ID de la sesión

        Returns:
            Lista de ChatMessage sanitizados
        """
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

        if not session:
            return []

        try:
            history_data = json.loads(session.history or "[]")
        except json.JSONDecodeError:
            logger.warning(f"Historial corrupto en sesión {session_id}")
            return []

        # Convertir a ChatMessage
        messages = []
        for msg in history_data:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Validar rol
            if role not in ("user", "assistant"):
                role = "user"

            messages.append(ChatMessage(role=role, content=content))

        return messages

    def clear_session(self, session_id: UUID) -> bool:
        """
        Limpia el historial de una sesión (mantiene la sesión activa).

        Args:
            session_id: ID de la sesión

        Returns:
            True si se limpió correctamente
        """
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

        if not session:
            return False

        session.history = "[]"
        session.message_count = 0
        self.db.commit()

        logger.info(f"Historial limpiado para sesión {session_id}")
        return True

    def end_session(self, session_id: UUID) -> bool:
        """
        Finaliza una sesión de chat.

        Args:
            session_id: ID de la sesión

        Returns:
            True si se finalizó correctamente
        """
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

        if not session:
            return False

        session.is_active = False
        self.db.commit()

        logger.info(f"Sesión finalizada: {session_id}")
        return True

    def cleanup_expired_sessions(self) -> int:
        """
        Limpia sesiones expiradas (para ejecutar periódicamente).

        Returns:
            Número de sesiones limpiadas
        """
        now = datetime.utcnow()

        expired = self.db.query(ChatSession).filter(
            ChatSession.is_active == True,
            ChatSession.expires_at < now
        ).all()

        count = 0
        for session in expired:
            session.is_active = False
            count += 1

        if count > 0:
            self.db.commit()
            logger.info(f"Limpiadas {count} sesiones expiradas")

        return count

    def get_active_session_for_user(self, user_id: UUID) -> Optional[ChatSession]:
        """
        Obtiene la sesión activa de un usuario sin crear una nueva.

        Args:
            user_id: ID del usuario

        Returns:
            ChatSession o None si no hay sesión activa
        """
        return self.db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True
        ).first()
