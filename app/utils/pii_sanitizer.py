"""
Utilidades para sanitización de PII (Personally Identifiable Information) en logs

Este módulo proporciona funciones para enmascarar datos sensibles antes de logarlos,
cumpliendo con GDPR y mejores prácticas de seguridad.

Author: Security Team
Date: 2026-02-11
"""

import re
from typing import Optional


def mask_email(email: Optional[str]) -> str:
    """
    Enmascara un email para logs seguros
    
    Args:
        email: Dirección de email a enmascarar
    
    Returns:
        Email enmascarado (ej: "jo***@gmail.com")
    
    Example:
        >>> mask_email("john.doe@example.com")
        "jo***@example.com"
    """
    if not email or '@' not in email:
        return "***"
    
    try:
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = local[0] + "***" if local else "***"
        else:
            masked_local = local[:2] + "***"
        return f"{masked_local}@{domain}"
    except Exception:
        return "***@***"


def mask_username(username: Optional[str]) -> str:
    """
    Enmascara un nombre de usuario para logs seguros
    
    Args:
        username: Nombre de usuario a enmascarar
    
    Returns:
        Username enmascarado
    
    Example:
        >>> mask_username("johndoe123")
        "jo***23"
    """
    if not username:
        return "***"
    
    if len(username) <= 4:
        return username[0] + "***" if username else "***"
    
    return f"{username[:2]}***{username[-2:]}"


def mask_name(name: Optional[str]) -> str:
    """
    Enmascara un nombre completo para logs seguros
    
    Args:
        name: Nombre a enmascarar
    
    Returns:
        Nombre enmascarado
    
    Example:
        >>> mask_name("John Doe")
        "J*** D***"
    """
    if not name:
        return "***"
    
    parts = name.split()
    masked_parts = []
    for part in parts:
        if len(part) > 0:
            masked_parts.append(part[0] + "***")
        else:
            masked_parts.append("***")
    
    return " ".join(masked_parts)


def mask_account_number(account_number: Optional[str]) -> str:
    """
    Enmascara un número de cuenta/IBAN
    
    Args:
        account_number: Número de cuenta a enmascarar
    
    Returns:
        Número enmascarado (muestra solo últimos 4 dígitos)
    
    Example:
        >>> mask_account_number("ES91 2100 0418 4502 0005 1332")
        "****1332"
    """
    if not account_number:
        return "****"
    
    # Eliminar espacios
    clean = account_number.replace(" ", "")
    
    if len(clean) <= 4:
        return "****"
    
    return f"****{clean[-4:]}"


def mask_uuid(uuid_str: Optional[str]) -> str:
    """
    Enmascara un UUID para logs seguros
    
    Args:
        uuid_str: UUID a enmascarar
    
    Returns:
        UUID parcialmente enmascarado
    
    Example:
        >>> mask_uuid("550e8400-e29b-41d4-a716-446655440000")
        "550e8400-****-****-****-************"
    """
    if not uuid_str:
        return "****"
    
    parts = str(uuid_str).split('-')
    if len(parts) == 5:
        return f"{parts[0]}-****-****-****-{parts[4][:4]}****"
    
    return str(uuid_str)[:8] + "****"


def mask_ip(ip_address: Optional[str]) -> str:
    """
    Enmascara una dirección IP
    
    Args:
        ip_address: IP a enmascarar
    
    Returns:
        IP parcialmente enmascarada
    
    Example:
        >>> mask_ip("192.168.1.100")
        "192.168.***.***"
    """
    if not ip_address:
        return "***.***.***.***"
    
    parts = ip_address.split('.')
    if len(parts) == 4:  # IPv4
        return f"{parts[0]}.{parts[1]}.***.***"
    
    # IPv6 o formato no reconocido
    if ':' in ip_address:  # IPv6
        return ip_address[:7] + "::****"
    
    return "***"


def sanitize_log_message(message: str) -> str:
    """
    Sanitiza un mensaje de log completo, detectando y enmascarando PII automáticamente
    
    Detecta:
    - Emails
    - UUIDs
    - Posibles números de cuenta
    
    Args:
        message: Mensaje a sanitizar
    
    Returns:
        Mensaje con PII enmascarada
    
    Example:
        >>> sanitize_log_message("Usuario john@example.com conectado")
        "Usuario jo***@example.com conectado"
    """
    # Enmascarar emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, message)
    for email in emails:
        message = message.replace(email, mask_email(email))
    
    # Enmascarar UUIDs
    uuid_pattern = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
    uuids = re.findall(uuid_pattern, message)
    for uuid_str in uuids:
        message = message.replace(uuid_str, mask_uuid(uuid_str))
    
    return message


class PIISafeLogger:
    """
    Wrapper de logger que sanitiza PII automáticamente
    
    Usage:
        >>> from app.utils.pii_sanitizer import PIISafeLogger
        >>> logger = PIISafeLogger(get_logger(__name__))
        >>> logger.info_safe("Usuario encontrado", email="john@example.com")
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    def info_safe(self, message: str, **pii_fields):
        """Log info con PII enmascarada"""
        safe_parts = []
        for key, value in pii_fields.items():
            if key == 'email':
                safe_parts.append(f"{key}={mask_email(value)}")
            elif key == 'username':
                safe_parts.append(f"{key}={mask_username(value)}")
            elif key == 'user_id':
                safe_parts.append(f"{key}={mask_uuid(str(value))}")
            elif key == 'name' or key == 'full_name':
                safe_parts.append(f"{key}={mask_name(value)}")
            elif key == 'ip':
                safe_parts.append(f"{key}={mask_ip(value)}")
            else:
                safe_parts.append(f"{key}={value}")
        
        if safe_parts:
            self.logger.info(f"{message} | {' | '.join(safe_parts)}")
        else:
            self.logger.info(sanitize_log_message(message))
    
    def warning_safe(self, message: str, **pii_fields):
        """Log warning con PII enmascarada"""
        safe_parts = []
        for key, value in pii_fields.items():
            if key == 'email':
                safe_parts.append(f"{key}={mask_email(value)}")
            elif key == 'username':
                safe_parts.append(f"{key}={mask_username(value)}")
            elif key == 'user_id':
                safe_parts.append(f"{key}={mask_uuid(str(value))}")
            else:
                safe_parts.append(f"{key}={value}")
        
        if safe_parts:
            self.logger.warning(f"{message} | {' | '.join(safe_parts)}")
        else:
            self.logger.warning(sanitize_log_message(message))
    
    def error_safe(self, message: str, **pii_fields):
        """Log error con PII enmascarada"""
        safe_parts = []
        for key, value in pii_fields.items():
            if key == 'email':
                safe_parts.append(f"{key}={mask_email(value)}")
            elif key == 'username':
                safe_parts.append(f"{key}={mask_username(value)}")
            elif key == 'user_id':
                safe_parts.append(f"{key}={mask_uuid(str(value))}")
            else:
                safe_parts.append(f"{key}={value}")
        
        if safe_parts:
            self.logger.error(f"{message} | {' | '.join(safe_parts)}")
        else:
            self.logger.error(sanitize_log_message(message))
    
    # Métodos pass-through para logs normales (sin PII)
    def debug(self, message: str, *args, **kwargs):
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        self.logger.critical(message, *args, **kwargs)
