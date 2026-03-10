"""
Sistema de Gestión de Claves de Encriptación

Este módulo implementa un sistema seguro de gestión de claves maestras
con soporte para versionado y rotación de claves sin interrupciones.

Cumplimiento PSD2:
- Artículo 97: Requisitos de seguridad de credenciales
- EBA Guidelines: Gestión segura de claves criptográficas

Author: Security Team
Date: 2026-02-01
Version: 1.0
"""

import os
import base64
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("app.utils.key_management")


class KeyManagementError(Exception):
    """Excepción base para errores de gestión de claves"""
    pass


class MasterKeyNotFoundError(KeyManagementError):
    """Excepción cuando no se encuentra la clave maestra"""
    pass


class InvalidKeyVersionError(KeyManagementError):
    """Excepción cuando se solicita una versión de clave inválida"""
    pass


@dataclass
class KeyInfo:
    """
    Información sobre una clave de encriptación
    
    Attributes:
        version: Versión de la clave (1, 2, 3, ...)
        key: Clave de encriptación en bytes (32 bytes para AES-256)
        created_at: Timestamp de creación
        algorithm: Algoritmo de encriptación (default: AES-256-GCM)
        is_active: Si es la clave activa actualmente
    """
    version: int
    key: bytes
    created_at: datetime
    algorithm: str = "AES-256-GCM"
    is_active: bool = False


class KeyManager:
    """
    Gestor centralizado de claves de encriptación
    
    Responsabilidades:
    - Cargar y validar claves maestras desde variables de entorno
    - Mantener múltiples versiones de claves (para rotación)
    - Proporcionar acceso seguro a claves por versión
    - Logging de operaciones críticas
    
    Ejemplo:
        >>> km = KeyManager()
        >>> version, key = km.get_current_key()
        >>> print(f"Usando clave v{version}")
    """
    
    def __init__(self):
        """
        Inicializa el gestor de claves
        
        Variables de entorno requeridas:
        - ENCRYPTION_MASTER_KEY: Clave maestra en base64 (32 bytes)
        - ENCRYPTION_KEY_VERSION: Versión actual (default: 1)
        
        Raises:
            MasterKeyNotFoundError: Si no se encuentra la clave maestra
            ValueError: Si la clave no tiene el tamaño correcto
        """
        self.keys: Dict[int, KeyInfo] = {}
        self.current_version: int = 1
        
        # Cargar configuración
        self._load_master_key()
        
        logger.info(
            f"✅ KeyManager inicializado - Versión activa: v{self.current_version}"
        )
    
    def _load_master_key(self) -> None:
        """
        Carga la clave maestra desde variables de entorno
        
        Valida:
        - Existencia de ENCRYPTION_MASTER_KEY
        - Formato base64 válido
        - Tamaño de 32 bytes (256 bits)
        
        Raises:
            MasterKeyNotFoundError: Si no existe la variable de entorno
            ValueError: Si el formato o tamaño es incorrecto
        """
        # Obtener clave de variable de entorno
        # Primero intenta desde settings (Pydantic), luego desde os.getenv()
        master_key_b64 = None
        
        try:
            from app.config import settings
            master_key_b64 = settings.ENCRYPTION_MASTER_KEY
            logger.debug("Clave obtenida desde Pydantic Settings")
        except Exception as e:
            logger.debug(f"No se pudo obtener clave desde settings: {e}")
            master_key_b64 = os.getenv("ENCRYPTION_MASTER_KEY")
            logger.debug("Clave obtenida desde os.getenv()")
        
        if not master_key_b64:
            error_msg = (
                "❌ ENCRYPTION_MASTER_KEY no configurada en variables de entorno.\n"
                "Genera una clave con:\n"
                "  python -c \"import os, base64; print(base64.b64encode(os.urandom(32)).decode())\"\n"
                "Y agrégala a tu archivo .env:\n"
                "  ENCRYPTION_MASTER_KEY=<clave_generada>"
            )
            logger.critical(error_msg)
            raise MasterKeyNotFoundError(error_msg)
        
        try:
            # Decodificar de base64
            master_key = base64.b64decode(master_key_b64)
        except Exception as e:
            raise ValueError(
                f"ENCRYPTION_MASTER_KEY no es base64 válido: {e}"
            )
        
        # Validar tamaño (debe ser 32 bytes para AES-256)
        if len(master_key) != 32:
            raise ValueError(
                f"ENCRYPTION_MASTER_KEY debe ser 32 bytes (256 bits), "
                f"recibido {len(master_key)} bytes"
            )
        
        # Obtener versión (default: 1)
        version_str = None
        try:
            from app.config import settings
            version_str = str(settings.ENCRYPTION_KEY_VERSION)
        except Exception:
            version_str = os.getenv("ENCRYPTION_KEY_VERSION", "1")
        
        try:
            self.current_version = int(version_str)
        except ValueError:
            logger.warning(
                f"ENCRYPTION_KEY_VERSION inválida '{version_str}', usando 1"
            )
            self.current_version = 1
        
        # Almacenar clave
        self.keys[self.current_version] = KeyInfo(
            version=self.current_version,
            key=master_key,
            created_at=datetime.now(),
            algorithm="AES-256-GCM",
            is_active=True
        )
        
        logger.info(
            f"🔑 Clave maestra v{self.current_version} cargada correctamente "
            f"({len(master_key)} bytes)"
        )
    
    def get_current_key(self) -> Tuple[int, bytes]:
        """
        Obtiene la clave activa actual para encriptación
        
        Usar esta función para ENCRIPTAR nuevos datos.
        
        Returns:
            Tuple[int, bytes]: (version, key)
                - version: Número de versión de la clave
                - key: Clave de encriptación en bytes (32 bytes)
        
        Example:
            >>> version, key = km.get_current_key()
            >>> cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
        """
        key_info = self.keys[self.current_version]
        
        logger.debug(
            f"Proporcionando clave v{self.current_version} para encriptación"
        )
        
        return (key_info.version, key_info.key)
    
    def get_key_by_version(self, version: int) -> bytes:
        """
        Obtiene una clave específica por su versión
        
        Usar esta función para DESENCRIPTAR datos que fueron encriptados
        con una versión específica de clave.
        
        Args:
            version: Número de versión de la clave solicitada
        
        Returns:
            bytes: Clave de encriptación (32 bytes)
        
        Raises:
            InvalidKeyVersionError: Si la versión no existe
        
        Example:
            >>> # Datos encriptados tienen formato "version:nonce:ciphertext:tag"
            >>> encrypted = "2:abc123...:def456...:ghi789..."
            >>> version = int(encrypted.split(':')[0])
            >>> key = km.get_key_by_version(version)
        """
        if version not in self.keys:
            available = list(self.keys.keys())
            raise InvalidKeyVersionError(
                f"Versión de clave {version} no encontrada. "
                f"Versiones disponibles: {available}"
            )
        
        key_info = self.keys[version]
        
        logger.debug(
            f"Proporcionando clave v{version} para desencriptación"
        )
        
        return key_info.key
    
    def add_key_version(
        self,
        version: int,
        key_b64: str,
        set_as_active: bool = False
    ) -> None:
        """
        Añade una nueva versión de clave al gestor
        
        Útil para:
        - Rotación de claves
        - Mantener claves antiguas para desencriptar datos históricos
        - Preparar migración gradual a nueva clave
        
        Args:
            version: Número de versión (debe ser > 0 y único)
            key_b64: Clave en formato base64 (32 bytes)
            set_as_active: Si establecer como clave activa
        
        Raises:
            ValueError: Si la versión ya existe o formato incorrecto
        
        Example:
            >>> # Preparar rotación de clave
            >>> new_key = base64.b64encode(os.urandom(32)).decode()
            >>> km.add_key_version(2, new_key, set_as_active=False)
            >>> # Migrar datos...
            >>> km.set_active_version(2)
        """
        if version in self.keys:
            raise ValueError(f"Ya existe una clave con versión {version}")
        
        # Decodificar y validar
        try:
            key = base64.b64decode(key_b64)
        except Exception as e:
            raise ValueError(f"Clave no es base64 válido: {e}")
        
        if len(key) != 32:
            raise ValueError(
                f"Clave debe ser 32 bytes, recibido {len(key)} bytes"
            )
        
        # Añadir clave
        self.keys[version] = KeyInfo(
            version=version,
            key=key,
            created_at=datetime.now(),
            algorithm="AES-256-GCM",
            is_active=set_as_active
        )
        
        # Actualizar versión activa si se solicitó
        if set_as_active:
            # Desactivar clave anterior
            if self.current_version in self.keys:
                self.keys[self.current_version].is_active = False
            
            self.current_version = version
            
            logger.warning(
                f"🔄 Nueva clave v{version} establecida como ACTIVA. "
                f"Nuevas encriptaciones usarán esta clave."
            )
        else:
            logger.info(
                f"➕ Clave v{version} añadida (inactiva). "
                f"Disponible para desencriptación."
            )
    
    def set_active_version(self, version: int) -> None:
        """
        Establece una versión de clave como activa
        
        Args:
            version: Versión a activar
        
        Raises:
            InvalidKeyVersionError: Si la versión no existe
        """
        if version not in self.keys:
            raise InvalidKeyVersionError(
                f"No existe clave con versión {version}"
            )
        
        # Desactivar clave anterior
        if self.current_version in self.keys:
            self.keys[self.current_version].is_active = False
        
        # Activar nueva clave
        self.keys[version].is_active = True
        self.current_version = version
        
        logger.warning(
            f"⚠️ Clave v{version} activada. Todas las nuevas encriptaciones "
            f"usarán esta versión."
        )
    
    def list_keys(self) -> list[KeyInfo]:
        """
        Lista todas las claves disponibles
        
        Returns:
            list[KeyInfo]: Lista de información de claves
        
        Example:
            >>> for key_info in km.list_keys():
            ...     print(f"v{key_info.version}: {key_info.algorithm} "
            ...           f"({'ACTIVA' if key_info.is_active else 'inactiva'})")
        """
        return list(self.keys.values())
    
    def validate_key_health(self) -> Dict[str, any]:
        """
        Valida el estado del sistema de claves
        
        Verifica:
        - Existencia de clave activa
        - Tamaños correctos
        - Versiones válidas
        
        Returns:
            dict: Reporte de salud del sistema
        
        Example:
            >>> health = km.validate_key_health()
            >>> if not health['is_healthy']:
            ...     logger.error(f"Problemas: {health['issues']}")
        """
        issues = []
        
        # Verificar que existe al menos una clave
        if not self.keys:
            issues.append("No hay claves cargadas")
        
        # Verificar que hay una clave activa
        active_keys = [k for k in self.keys.values() if k.is_active]
        if len(active_keys) == 0:
            issues.append("No hay clave activa")
        elif len(active_keys) > 1:
            issues.append(f"Múltiples claves activas: {[k.version for k in active_keys]}")
        
        # Verificar tamaños
        for version, key_info in self.keys.items():
            if len(key_info.key) != 32:
                issues.append(
                    f"Clave v{version} tiene tamaño incorrecto: "
                    f"{len(key_info.key)} bytes (esperado 32)"
                )
        
        # Verificar que current_version existe
        if self.current_version not in self.keys:
            issues.append(
                f"current_version={self.current_version} no existe en keys"
            )
        
        is_healthy = len(issues) == 0
        
        report = {
            "is_healthy": is_healthy,
            "total_keys": len(self.keys),
            "active_version": self.current_version,
            "available_versions": list(self.keys.keys()),
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        
        if is_healthy:
            logger.info("✅ Sistema de claves saludable")
        else:
            logger.error(f"❌ Problemas en sistema de claves: {issues}")
        
        return report


# Instancia global del KeyManager (singleton)
# Se inicializa una vez al importar el módulo
_key_manager_instance: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """
    Obtiene la instancia singleton del KeyManager
    
    Inicializa el KeyManager la primera vez que se llama,
    y devuelve la misma instancia en llamadas subsiguientes.
    
    Returns:
        KeyManager: Instancia global del gestor de claves
    
    Example:
        >>> from app.utils.key_management import get_key_manager
        >>> km = get_key_manager()
        >>> version, key = km.get_current_key()
    """
    global _key_manager_instance
    
    if _key_manager_instance is None:
        _key_manager_instance = KeyManager()
        logger.info("🔐 KeyManager singleton inicializado")
    
    return _key_manager_instance


# Para testing: función para resetear el singleton
def _reset_key_manager() -> None:
    """
    ⚠️ SOLO PARA TESTING ⚠️
    
    Resetea la instancia singleton del KeyManager.
    NO usar en producción.
    """
    global _key_manager_instance
    _key_manager_instance = None
    logger.warning("⚠️ KeyManager singleton reseteado (solo para testing)")
