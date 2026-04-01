"""
Gemini Quota Service
====================

Servicio para gestionar cuotas de uso de Gemini AI por usuario.
Implementa tracking diario con reset automático.
"""

from datetime import date
from uuid import UUID
from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.gemini_usage import GeminiUsage
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("app.services.gemini_quota")


class GeminiQuotaService:
    """
    Servicio de cuotas para Gemini API.

    Funcionalidades:
    - check_quota(): Verifica si el usuario tiene cuota disponible
    - increment_usage(): Incrementa el contador de uso
    - get_remaining(): Obtiene cuota restante
    - check_and_increment(): Verifica e incrementa en una operación atómica
    """

    def __init__(self, db: Session):
        self.db = db
        self.daily_limit = settings.GEMINI_DAILY_LIMIT_PER_USER

    def _get_or_create_usage_record(self, user_id: UUID) -> GeminiUsage:
        """
        Obtiene o crea el registro de uso para hoy.

        Args:
            user_id: ID del usuario

        Returns:
            GeminiUsage: Registro de uso del día actual
        """
        today = date.today()

        usage = self.db.query(GeminiUsage).filter(
            and_(
                GeminiUsage.user_id == user_id,
                GeminiUsage.usage_date == today
            )
        ).first()

        if not usage:
            # Crear nuevo registro para hoy (reset automático)
            usage = GeminiUsage(
                user_id=user_id,
                usage_date=today,
                request_count=0
            )
            self.db.add(usage)
            self.db.flush()  # Para obtener el ID sin commit completo
            logger.info(f"Nuevo registro de cuota Gemini creado para user_id={user_id}")

        return usage

    def check_quota(self, user_id: UUID) -> bool:
        """
        Verifica si el usuario tiene cuota disponible.

        Args:
            user_id: ID del usuario

        Returns:
            bool: True si tiene cuota disponible, False si excedió el límite
        """
        usage = self._get_or_create_usage_record(user_id)
        return usage.request_count < self.daily_limit

    def increment_usage(self, user_id: UUID) -> int:
        """
        Incrementa el contador de uso del usuario.

        Args:
            user_id: ID del usuario

        Returns:
            int: Nuevo contador de uso
        """
        usage = self._get_or_create_usage_record(user_id)
        usage.request_count += 1
        self.db.commit()

        logger.info(
            f"Gemini usage incrementado: user_id={user_id}, "
            f"count={usage.request_count}/{self.daily_limit}"
        )

        return usage.request_count

    def get_remaining(self, user_id: UUID) -> Tuple[int, int, int]:
        """
        Obtiene información de cuota del usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[int, int, int]: (usado, restante, límite)
        """
        usage = self._get_or_create_usage_record(user_id)
        used = usage.request_count
        remaining = max(0, self.daily_limit - used)

        return (used, remaining, self.daily_limit)

    def check_and_increment(self, user_id: UUID) -> Tuple[bool, int, int]:
        """
        Verifica cuota e incrementa si está disponible (operación atómica).

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[bool, int, int]: (tiene_cuota, usado, límite)
        """
        usage = self._get_or_create_usage_record(user_id)

        if usage.request_count >= self.daily_limit:
            logger.warning(
                f"Cuota Gemini excedida: user_id={user_id}, "
                f"count={usage.request_count}/{self.daily_limit}"
            )
            return (False, usage.request_count, self.daily_limit)

        # Incrementar y commit
        usage.request_count += 1
        self.db.commit()

        logger.info(
            f"Gemini request autorizado: user_id={user_id}, "
            f"count={usage.request_count}/{self.daily_limit}"
        )

        return (True, usage.request_count, self.daily_limit)
