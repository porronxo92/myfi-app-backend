"""
Campos encriptados para modelos SQLAlchemy

Este módulo proporciona tipos de columna personalizados que manejan
encriptación/desencriptación de forma transparente usando AES-256-GCM.

Uso:
    from app.models.encrypted_fields import EncryptedString, EncryptedText
    
    class User(Base):
        # Campo encriptado automáticamente
        email_encrypted = Column(EncryptedString(255), nullable=True)
        
        # O usar el tipo Text para campos largos
        notes_encrypted = Column(EncryptedText, nullable=True)

Author: Security Team
Date: 2026-02-11
"""

from sqlalchemy import TypeDecorator, Text, String
from sqlalchemy.dialects.postgresql import TEXT
import logging

logger = logging.getLogger("app.models.encrypted_fields")


def _get_encryption_module():
    """
    Importación diferida del módulo de encriptación para evitar 
    dependencias circulares durante la inicialización.
    """
    try:
        from app.utils.encryption import encrypt_field, decrypt_field
        from app.utils.key_management import KeyManagementError
        return encrypt_field, decrypt_field, KeyManagementError
    except ImportError as e:
        logger.warning(f"Módulo de encriptación no disponible: {e}")
        return None, None, None


class EncryptedString(TypeDecorator):
    """
    Tipo de columna SQLAlchemy que encripta/desencripta strings automáticamente.
    
    Los datos se almacenan encriptados en la base de datos y se desencriptan
    automáticamente al leer.
    
    Attributes:
        impl: Tipo base de SQLAlchemy (String)
        cache_ok: Permitir cacheo de tipo
    
    Example:
        # En el modelo
        email_encrypted = Column(EncryptedString(255), nullable=True)
        
        # Al asignar, se encripta automáticamente
        user.email_encrypted = "user@example.com"
        db.commit()  # Se guarda encriptado
        
        # Al leer, se desencripta automáticamente  
        print(user.email_encrypted)  # "user@example.com"
    """
    
    impl = Text
    cache_ok = True
    
    def __init__(self, length=None, *args, **kwargs):
        """
        Args:
            length: Longitud máxima del string (antes de encriptar).
                   El texto encriptado será más largo.
        """
        super().__init__(*args, **kwargs)
        self.length = length
    
    def process_bind_param(self, value, dialect):
        """
        Encripta el valor antes de guardarlo en la BD.
        
        Args:
            value: Valor en texto plano
            dialect: Dialecto de BD (PostgreSQL, etc.)
        
        Returns:
            Valor encriptado o None si el valor es None/vacío
        """
        if value is None or value == "":
            return value
        
        encrypt_field, _, KeyManagementError = _get_encryption_module()
        
        if encrypt_field is None:
            # Encriptación no disponible, guardar en claro (modo desarrollo)
            logger.warning("Encriptación no disponible - guardando en texto plano")
            return value
        
        try:
            return encrypt_field(value)
        except KeyManagementError as e:
            logger.error(f"Error de gestión de claves: {e}")
            # En caso de error de claves, no guardar datos sensibles
            raise ValueError("No se puede guardar datos sensibles sin clave de encriptación configurada")
        except Exception as e:
            logger.error(f"Error encriptando campo: {e}")
            raise
    
    def process_result_value(self, value, dialect):
        """
        Desencripta el valor al leerlo de la BD.
        
        Args:
            value: Valor encriptado de la BD
            dialect: Dialecto de BD
        
        Returns:
            Valor desencriptado o None
        """
        if value is None or value == "":
            return value
        
        _, decrypt_field, KeyManagementError = _get_encryption_module()
        
        if decrypt_field is None:
            # Si no hay módulo de encriptación, devolver tal cual
            # (podría ser un dato no encriptado de migración)
            return value
        
        # Verificar si el valor parece estar encriptado (formato version:nonce:ciphertext:tag)
        if ':' not in value or value.count(':') != 3:
            # Valor en texto plano (datos pre-migración)
            logger.debug("Campo no encriptado detectado - retornando valor original")
            return value
        
        try:
            return decrypt_field(value)
        except KeyManagementError as e:
            logger.error(f"Error de gestión de claves al desencriptar: {e}")
            return None  # No exponer datos si hay error de claves
        except Exception as e:
            # Podría ser un valor no encriptado de antes de la migración
            logger.warning(f"Error desencriptando, asumiendo texto plano: {e}")
            return value


class EncryptedText(EncryptedString):
    """
    Versión de EncryptedString para campos TEXT largos.
    
    Mismo comportamiento que EncryptedString pero sin límite de longitud.
    """
    
    impl = Text
    cache_ok = True
    
    def __init__(self, *args, **kwargs):
        super(EncryptedString, self).__init__(*args, **kwargs)


class EncryptedNumeric(TypeDecorator):
    """
    Tipo de columna para encriptar valores numéricos.
    
    Convierte el número a string para encriptar, y lo reconvierte a Decimal al leer.
    
    Example:
        balance_encrypted = Column(EncryptedNumeric(), nullable=True)
        
        account.balance_encrypted = Decimal("1234.56")
        # Se guarda encriptado como string
        
        print(account.balance_encrypted)  # Decimal("1234.56")
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """Encripta el valor numérico"""
        if value is None:
            return value
        
        encrypt_field, _, KeyManagementError = _get_encryption_module()
        
        # Convertir a string
        str_value = str(value)
        
        if encrypt_field is None:
            return str_value
        
        try:
            return encrypt_field(str_value)
        except Exception as e:
            logger.error(f"Error encriptando campo numérico: {e}")
            raise
    
    def process_result_value(self, value, dialect):
        """Desencripta y convierte a Decimal"""
        from decimal import Decimal, InvalidOperation
        
        if value is None:
            return value
        
        # Si ya es un Decimal (columna numeric no migrada), devolverlo directamente
        if isinstance(value, Decimal):
            return value
        
        # Si es un número (int, float), convertir a Decimal
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        
        _, decrypt_field, _ = _get_encryption_module()
        
        # Verificar si está encriptado (solo para strings)
        if isinstance(value, str) and decrypt_field and ':' in value and value.count(':') == 3:
            try:
                value = decrypt_field(value)
            except Exception as e:
                logger.warning(f"Error desencriptando numérico: {e}")
        
        # Convertir a Decimal
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            logger.error(f"Valor numérico inválido: {value}")
            return None


# Alias para conveniencia
EncryptedField = EncryptedString
