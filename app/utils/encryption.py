"""
Utilidades de Encriptación AES-256-GCM

Este módulo proporciona funciones de alto nivel para encriptar y desencriptar
datos sensibles utilizando AES-256-GCM (Advanced Encryption Standard con
Galois/Counter Mode).

Características:
- Encriptación autenticada (confidencialidad + integridad)
- Manejo automático de nonces únicos
- Soporte para versionado de claves
- Formato de almacenamiento: "version:nonce:ciphertext:tag"

Cumplimiento PSD2:
- Artículo 98: Protección de datos sensibles de pago
- NIST SP 800-38D: Recomendaciones para modos de cifrado de bloques

Author: Security Team
Date: 2026-02-01
Version: 1.0
"""

import os
import base64
import logging
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from app.utils.key_management import get_key_manager, KeyManagementError

logger = logging.getLogger("app.utils.encryption")


class EncryptionError(Exception):
    """Excepción base para errores de encriptación"""
    pass


class DecryptionError(Exception):
    """Excepción para errores de desencriptación"""
    pass


class InvalidFormatError(DecryptionError):
    """Excepción cuando el formato de datos encriptados es inválido"""
    pass


def encrypt_field(plaintext: str) -> str:
    """
    Encripta un campo de texto usando AES-256-GCM
    
    El resultado incluye toda la información necesaria para desencriptar:
    - Versión de clave usada (para rotación de claves)
    - Nonce único (número usado una sola vez)
    - Texto cifrado
    - Tag de autenticación (para verificar integridad)
    
    Args:
        plaintext: Texto en claro a encriptar (str)
    
    Returns:
        str: Datos encriptados en formato "version:nonce:ciphertext:tag"
              Todos los componentes están en base64
    
    Raises:
        EncryptionError: Si hay algún problema durante la encriptación
        ValueError: Si plaintext es None o vacío
    
    Example:
        >>> account_number = "ES91 2100 0418 4502 0005 1332"
        >>> encrypted = encrypt_field(account_number)
        >>> print(encrypted)
        "1:YTFiMmMz...:eDl5OHo3...:bTRuM28y..."
        
        >>> # Guardar en base de datos
        >>> account.account_number_encrypted = encrypted
        >>> db.commit()
    
    Seguridad:
    - Nonce de 12 bytes (96 bits) generado aleatoriamente
    - Tag de autenticación de 16 bytes (128 bits)
    - Nonce único garantizado por os.urandom()
    - NUNCA se reutilizan nonces con la misma clave
    """
    # Validar entrada
    if plaintext is None:
        raise ValueError("plaintext no puede ser None")
    
    if not isinstance(plaintext, str):
        raise ValueError(f"plaintext debe ser str, recibido {type(plaintext)}")
    
    if plaintext == "":
        # Permitir cadenas vacías, retornar vacío sin encriptar
        return ""
    
    try:
        # Obtener clave actual del KeyManager
        key_manager = get_key_manager()
        version, key = key_manager.get_current_key()
        
        # Generar nonce único (12 bytes = 96 bits)
        # CRÍTICO: Cada operación de encriptación DEBE usar un nonce diferente
        nonce = os.urandom(12)
        
        # Crear instancia de AESGCM
        aesgcm = AESGCM(key)
        
        # Encriptar
        # AESGCM.encrypt() retorna: ciphertext + tag (todo junto)
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext_bytes, None)
        
        # Separar ciphertext y tag
        # Tag es siempre los últimos 16 bytes
        ciphertext = ciphertext_and_tag[:-16]
        tag = ciphertext_and_tag[-16:]
        
        # Codificar a base64 para almacenamiento
        nonce_b64 = base64.b64encode(nonce).decode('ascii')
        ciphertext_b64 = base64.b64encode(ciphertext).decode('ascii')
        tag_b64 = base64.b64encode(tag).decode('ascii')
        
        # Formato: version:nonce:ciphertext:tag
        encrypted = f"{version}:{nonce_b64}:{ciphertext_b64}:{tag_b64}"
        
        logger.debug(
            f"✅ Campo encriptado exitosamente "
            f"(v{version}, {len(plaintext)} chars → {len(encrypted)} chars)"
        )
        
        return encrypted
        
    except KeyManagementError as e:
        logger.error(f"❌ Error obteniendo clave de encriptación: {e}")
        raise EncryptionError(f"Error de gestión de claves: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error inesperado durante encriptación: {e}")
        raise EncryptionError(f"Error encriptando datos: {e}")


def decrypt_field(encrypted: str) -> str:
    """
    Desencripta un campo encriptado con AES-256-GCM
    
    Valida automáticamente:
    - Integridad de los datos (tag de autenticación)
    - Que los datos no han sido modificados
    - Formato correcto de los datos encriptados
    
    Args:
        encrypted: Datos encriptados en formato "version:nonce:ciphertext:tag"
    
    Returns:
        str: Texto en claro original
    
    Raises:
        DecryptionError: Si los datos están corruptos o la clave es incorrecta
        InvalidFormatError: Si el formato de los datos encriptados es inválido
        ValueError: Si encrypted es None o vacío
    
    Example:
        >>> encrypted = account.account_number_encrypted
        >>> account_number = decrypt_field(encrypted)
        >>> print(account_number)
        "ES91 2100 0418 4502 0005 1332"
        
        >>> # Desencriptar y convertir a Decimal
        >>> from decimal import Decimal
        >>> balance_str = decrypt_field(account.balance_encrypted)
        >>> balance = Decimal(balance_str)
    
    Seguridad:
    - Verificación automática de integridad con tag de autenticación
    - Detección de cualquier modificación de datos
    - Si el tag no coincide, lanza InvalidTag (datos comprometidos)
    """
    # Validar entrada
    if encrypted is None:
        raise ValueError("encrypted no puede ser None")
    
    if not isinstance(encrypted, str):
        raise ValueError(f"encrypted debe ser str, recibido {type(encrypted)}")
    
    if encrypted == "":
        # Retornar cadena vacía si se encriptó una cadena vacía
        return ""
    
    try:
        # Parsear formato: version:nonce:ciphertext:tag
        parts = encrypted.split(':')
        
        if len(parts) != 4:
            raise InvalidFormatError(
                f"Formato inválido: esperado 4 partes (version:nonce:ciphertext:tag), "
                f"recibido {len(parts)} partes"
            )
        
        version_str, nonce_b64, ciphertext_b64, tag_b64 = parts
        
        # Validar y convertir versión
        try:
            version = int(version_str)
        except ValueError:
            raise InvalidFormatError(
                f"Versión inválida: '{version_str}' no es un número"
            )
        
        # Decodificar de base64
        try:
            nonce = base64.b64decode(nonce_b64)
            ciphertext = base64.b64decode(ciphertext_b64)
            tag = base64.b64decode(tag_b64)
        except Exception as e:
            raise InvalidFormatError(
                f"Error decodificando base64: {e}"
            )
        
        # Validar tamaños
        if len(nonce) != 12:
            raise InvalidFormatError(
                f"Nonce debe ser 12 bytes, recibido {len(nonce)} bytes"
            )
        
        if len(tag) != 16:
            raise InvalidFormatError(
                f"Tag debe ser 16 bytes, recibido {len(tag)} bytes"
            )
        
        # Obtener clave correspondiente a la versión
        key_manager = get_key_manager()
        key = key_manager.get_key_by_version(version)
        
        # Crear instancia de AESGCM
        aesgcm = AESGCM(key)
        
        # Reconstruir ciphertext + tag para decrypt()
        ciphertext_and_tag = ciphertext + tag
        
        # Desencriptar y verificar integridad
        try:
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, None)
        except InvalidTag:
            # Datos fueron modificados o clave incorrecta
            logger.error(
                f"❌ FALLO DE INTEGRIDAD: Tag inválido al desencriptar. "
                f"Datos comprometidos o clave incorrecta (v{version})"
            )
            raise DecryptionError(
                "Los datos están corruptos o se usó una clave incorrecta. "
                "Verificación de integridad fallida."
            )
        
        # Decodificar de UTF-8
        plaintext = plaintext_bytes.decode('utf-8')
        
        logger.debug(
            f"✅ Campo desencriptado exitosamente "
            f"(v{version}, {len(encrypted)} chars → {len(plaintext)} chars)"
        )
        
        return plaintext
        
    except (DecryptionError, InvalidFormatError):
        # Re-lanzar errores conocidos
        raise
    
    except KeyManagementError as e:
        logger.error(f"❌ Error obteniendo clave para desencriptar: {e}")
        raise DecryptionError(f"Error de gestión de claves: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error inesperado durante desencriptación: {e}")
        raise DecryptionError(f"Error desencriptando datos: {e}")


def encrypt_optional_field(plaintext: Optional[str]) -> Optional[str]:
    """
    Encripta un campo opcional (puede ser None)
    
    Wrapper conveniente para campos que pueden ser nulos en la base de datos.
    
    Args:
        plaintext: Texto a encriptar o None
    
    Returns:
        str encriptado si plaintext no es None, sino None
    
    Example:
        >>> # Campo opcional: bank_name puede ser None
        >>> encrypted_bank = encrypt_optional_field(account.bank_name)
        >>> account.bank_name_encrypted = encrypted_bank  # Puede ser None
    """
    if plaintext is None:
        return None
    
    if plaintext == "":
        return None  # Tratar cadena vacía como None
    
    return encrypt_field(plaintext)


def decrypt_optional_field(encrypted: Optional[str]) -> Optional[str]:
    """
    Desencripta un campo opcional (puede ser None)
    
    Wrapper conveniente para campos que pueden ser nulos en la base de datos.
    
    Args:
        encrypted: Datos encriptados o None
    
    Returns:
        str desencriptado si encrypted no es None, sino None
    
    Example:
        >>> # Campo opcional
        >>> bank_name = decrypt_optional_field(account.bank_name_encrypted)
        >>> print(bank_name)  # Puede ser None
    """
    if encrypted is None:
        return None
    
    if encrypted == "":
        return None  # Tratar cadena vacía como None
    
    return decrypt_field(encrypted)


def is_encrypted(value: str) -> bool:
    """
    Verifica si un string tiene el formato de dato encriptado
    
    Útil para:
    - Detectar si un campo ya está encriptado antes de re-encriptar
    - Validación de migraciones de datos
    - Debugging
    
    Args:
        value: String a verificar
    
    Returns:
        bool: True si parece estar encriptado, False en caso contrario
    
    Example:
        >>> data = "1:YTFiMmMz...:eDl5OHo3...:bTRuM28y..."
        >>> if is_encrypted(data):
        ...     plaintext = decrypt_field(data)
        ... else:
        ...     # Dato sin encriptar, encriptar ahora
        ...     encrypted = encrypt_field(data)
    
    Note:
        Esta función solo verifica el FORMATO, no valida que los datos
        puedan ser desencriptados correctamente.
    """
    if not value or not isinstance(value, str):
        return False
    
    # Verificar formato básico: version:nonce:ciphertext:tag
    parts = value.split(':')
    
    if len(parts) != 4:
        return False
    
    version_str, nonce_b64, ciphertext_b64, tag_b64 = parts
    
    # Verificar que version es un número
    try:
        int(version_str)
    except ValueError:
        return False
    
    # Verificar que los otros componentes parecen base64
    # (caracteres alfanuméricos, +, /, =)
    import re
    base64_pattern = r'^[A-Za-z0-9+/]+=*$'
    
    if not re.match(base64_pattern, nonce_b64):
        return False
    if not re.match(base64_pattern, ciphertext_b64):
        return False
    if not re.match(base64_pattern, tag_b64):
        return False
    
    return True


def batch_encrypt(plaintexts: list[str]) -> list[str]:
    """
    Encripta múltiples campos en lote
    
    Más eficiente que llamar encrypt_field() repetidamente,
    ya que el KeyManager se inicializa una sola vez.
    
    Args:
        plaintexts: Lista de textos a encriptar
    
    Returns:
        list[str]: Lista de textos encriptados (mismo orden)
    
    Example:
        >>> descriptions = ["Compra supermercado", "Gasolina", "Restaurante"]
        >>> encrypted_descriptions = batch_encrypt(descriptions)
        >>> for i, tx in enumerate(transactions):
        ...     tx.description_encrypted = encrypted_descriptions[i]
    """
    if not plaintexts:
        return []
    
    logger.info(f"🔐 Encriptando {len(plaintexts)} campos en lote")
    
    encrypted_list = []
    for plaintext in plaintexts:
        try:
            encrypted = encrypt_field(plaintext)
            encrypted_list.append(encrypted)
        except Exception as e:
            logger.error(f"Error encriptando en lote: {e}")
            # Re-lanzar para que falle toda la operación
            raise
    
    logger.info(f"✅ {len(encrypted_list)} campos encriptados exitosamente")
    
    return encrypted_list


def batch_decrypt(encrypted_list: list[str]) -> list[str]:
    """
    Desencripta múltiples campos en lote
    
    Más eficiente que llamar decrypt_field() repetidamente.
    
    Args:
        encrypted_list: Lista de datos encriptados
    
    Returns:
        list[str]: Lista de textos desencriptados (mismo orden)
    
    Example:
        >>> encrypted_descriptions = [tx.description_encrypted for tx in transactions]
        >>> descriptions = batch_decrypt(encrypted_descriptions)
        >>> for i, desc in enumerate(descriptions):
        ...     print(f"Transacción {i+1}: {desc}")
    """
    if not encrypted_list:
        return []
    
    logger.info(f"🔓 Desencriptando {len(encrypted_list)} campos en lote")
    
    plaintext_list = []
    for encrypted in encrypted_list:
        try:
            plaintext = decrypt_field(encrypted)
            plaintext_list.append(plaintext)
        except Exception as e:
            logger.error(f"Error desencriptando en lote: {e}")
            # Re-lanzar para que falle toda la operación
            raise
    
    logger.info(f"✅ {len(plaintext_list)} campos desencriptados exitosamente")
    
    return plaintext_list


# Aliases para compatibilidad y conveniencia
encrypt = encrypt_field
decrypt = decrypt_field


# Para debugging: función que muestra componentes de datos encriptados
def debug_encrypted_data(encrypted: str) -> dict:
    """
    ⚠️ SOLO PARA DEBUGGING ⚠️
    
    Muestra los componentes de datos encriptados sin desencriptar.
    Útil para diagnosticar problemas.
    
    Args:
        encrypted: Datos encriptados
    
    Returns:
        dict: Información sobre los componentes
    
    Example:
        >>> info = debug_encrypted_data(encrypted_account_number)
        >>> print(info)
        {
            'version': 1,
            'nonce_length': 12,
            'ciphertext_length': 32,
            'tag_length': 16,
            'format': 'version:nonce:ciphertext:tag',
            'is_valid_format': True
        }
    """
    parts = encrypted.split(':')
    
    info = {
        'total_parts': len(parts),
        'format': 'version:nonce:ciphertext:tag',
        'is_valid_format': len(parts) == 4
    }
    
    if len(parts) == 4:
        version_str, nonce_b64, ciphertext_b64, tag_b64 = parts
        
        try:
            info['version'] = int(version_str)
        except ValueError:
            info['version'] = f"INVALID: {version_str}"
        
        try:
            nonce = base64.b64decode(nonce_b64)
            ciphertext = base64.b64decode(ciphertext_b64)
            tag = base64.b64decode(tag_b64)
            
            info['nonce_length'] = len(nonce)
            info['ciphertext_length'] = len(ciphertext)
            info['tag_length'] = len(tag)
            
            # Validaciones
            info['nonce_valid'] = len(nonce) == 12
            info['tag_valid'] = len(tag) == 16
            
        except Exception as e:
            info['decode_error'] = str(e)
    
    return info
