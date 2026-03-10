"""
[DEPRECATED] SQLAlchemy Event Listeners para Encriptación

⚠️  ARCHIVO DEPRECADO ⚠️
Este módulo ya NO se usa con la nueva arquitectura de encriptación.

ARQUITECTURA ANTERIOR (dual-field):
- Campos encriptados separados (*_encrypted) 
- Campos en claro para índices
- Event listeners para sincronización

ARQUITECTURA ACTUAL (single-field + TypeDecorator):
- Campo único encriptado via TypeDecorator (AES-256-GCM)
- Encriptación/desencriptación automática transparente
- Filtrado y agregación en Python (no SQL)
- NO se necesitan event listeners ni campos duplicados

Ver app/utils/encryption.py para los TypeDecorators actuales:
- EncryptedNumeric
- EncryptedString
- EncryptedText

AUTOR: Security Team
FECHA: 2026-02-14 (Original)
DEPRECADO: 2026 (Migración a TypeDecorators)
"""

import warnings
import logging

logger = logging.getLogger(__name__)


def setup_encryption_redirects():
    """
    [DEPRECATED] Esta función ya no hace nada.
    
    Con la nueva arquitectura de encriptación (TypeDecorators),
    no se necesitan event listeners para sincronización.
    
    La encriptación es automática y transparente via TypeDecorators.
    """
    warnings.warn(
        "setup_encryption_redirects() está deprecada. "
        "La encriptación ahora es automática via TypeDecorators.",
        DeprecationWarning,
        stacklevel=2
    )
    logger.warning(
        "⚠️ setup_encryption_redirects() está deprecada. "
        "Los TypeDecorators manejan la encriptación automáticamente."
    )
    # No-op: no configurar nada
    return


def validate_encryption_setup() -> bool:
    """
    [DEPRECATED] Siempre retorna True.
    
    La validación ya no es necesaria con TypeDecorators.
    """
    warnings.warn(
        "validate_encryption_setup() está deprecada.",
        DeprecationWarning,
        stacklevel=2
    )
    return True


# ========================================
# CÓDIGO LEGACY COMENTADO (para referencia)
# ========================================
"""
# El código original de event listeners se mantiene comentado
# por si se necesita referencia histórica.
#
# Con la nueva arquitectura, este código ya NO se ejecuta.

# PARTE 1: Redirección de escrituras (evento 'set')
# @event.listens_for(Account.balance, 'set', retval=True)
# def redirect_balance_to_encrypted(target, value, oldvalue, initiator):
#     if value is not None and value != oldvalue:
#         if isinstance(value, (int, float)):
#             value = Decimal(str(value))
#         target.balance_encrypted = value
#     return value

# ... más event listeners eliminados (ver git history para código original) ...
"""
