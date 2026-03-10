"""
Tests Unitarios para Sistema de Encriptación

Tests para validar:
- Encriptación/desencriptación básica
- Gestión de claves (KeyManager)
- Manejo de errores
- Formato de datos encriptados
- Integridad de datos

Author: Security Team
Date: 2026-02-01
Version: 1.0
"""

import pytest
import os
import base64
from unittest.mock import patch, MagicMock

# Importar módulos a testear
from app.utils.encryption import (
    encrypt_field,
    decrypt_field,
    encrypt_optional_field,
    decrypt_optional_field,
    is_encrypted,
    batch_encrypt,
    batch_decrypt,
    EncryptionError,
    DecryptionError,
    InvalidFormatError,
    debug_encrypted_data
)

from app.utils.key_management import (
    KeyManager,
    get_key_manager,
    _reset_key_manager,
    KeyManagementError,
    MasterKeyNotFoundError,
    InvalidKeyVersionError
)


# ============================================
# FIXTURES
# ============================================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Configura variables de entorno para tests
    Se ejecuta automáticamente antes de cada test
    """
    # Generar clave de prueba (32 bytes)
    test_key = base64.b64encode(os.urandom(32)).decode()
    
    # Configurar variables de entorno
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", test_key)
    monkeypatch.setenv("ENCRYPTION_KEY_VERSION", "1")
    
    # Resetear singleton del KeyManager
    _reset_key_manager()
    
    yield
    
    # Cleanup
    _reset_key_manager()


@pytest.fixture
def sample_data():
    """Datos de ejemplo para tests"""
    return {
        "iban": "ES91 2100 0418 4502 0005 1332",
        "name": "Juan Pérez García",
        "balance": "1250.75",
        "description": "Pago de nómina mensual",
        "empty": "",
        "none": None
    }


# ============================================
# TESTS - ENCRIPTACIÓN BÁSICA
# ============================================

def test_encrypt_decrypt_simple(sample_data):
    """Test de encriptación y desencriptación básica"""
    plaintext = sample_data["iban"]
    
    # Encriptar
    encrypted = encrypt_field(plaintext)
    
    # Verificar que está encriptado (no es el texto original)
    assert encrypted != plaintext
    assert len(encrypted) > len(plaintext)
    
    # Desencriptar
    decrypted = decrypt_field(encrypted)
    
    # Verificar que se recupera el texto original
    assert decrypted == plaintext


def test_encrypt_decrypt_unicode(sample_data):
    """Test con caracteres Unicode (español, emojis)"""
    plaintext = sample_data["name"]  # Contiene 'é'
    
    encrypted = encrypt_field(plaintext)
    decrypted = decrypt_field(encrypted)
    
    assert decrypted == plaintext


def test_encrypt_decrypt_numbers(sample_data):
    """Test con números (balances, importes)"""
    plaintext = sample_data["balance"]
    
    encrypted = encrypt_field(plaintext)
    decrypted = decrypt_field(encrypted)
    
    assert decrypted == plaintext


def test_encrypt_empty_string(sample_data):
    """Test con cadena vacía"""
    plaintext = sample_data["empty"]
    
    encrypted = encrypt_field(plaintext)
    
    # Cadena vacía retorna cadena vacía sin encriptar
    assert encrypted == ""


def test_encrypt_none_raises_error(sample_data):
    """Test que None lanza error"""
    with pytest.raises(ValueError, match="no puede ser None"):
        encrypt_field(None)


def test_decrypt_empty_string(sample_data):
    """Test desencriptar cadena vacía"""
    decrypted = decrypt_field("")
    assert decrypted == ""


def test_decrypt_none_raises_error():
    """Test que desencriptar None lanza error"""
    with pytest.raises(ValueError, match="no puede ser None"):
        decrypt_field(None)


# ============================================
# TESTS - FORMATO DE DATOS ENCRIPTADOS
# ============================================

def test_encrypted_format(sample_data):
    """Test que el formato de datos encriptados es correcto"""
    plaintext = sample_data["iban"]
    encrypted = encrypt_field(plaintext)
    
    # Verificar formato: version:nonce:ciphertext:tag
    parts = encrypted.split(':')
    assert len(parts) == 4
    
    version, nonce_b64, ciphertext_b64, tag_b64 = parts
    
    # Versión debe ser número
    assert version.isdigit()
    assert int(version) >= 1
    
    # Todos los componentes deben ser base64 válido
    nonce = base64.b64decode(nonce_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    tag = base64.b64decode(tag_b64)
    
    # Verificar tamaños
    assert len(nonce) == 12  # 96 bits
    assert len(tag) == 16    # 128 bits
    assert len(ciphertext) >= 1  # Al menos 1 byte


def test_is_encrypted_function(sample_data):
    """Test función is_encrypted()"""
    plaintext = sample_data["iban"]
    encrypted = encrypt_field(plaintext)
    
    # Texto encriptado debe detectarse como encriptado
    assert is_encrypted(encrypted) is True
    
    # Texto plano no debe detectarse como encriptado
    assert is_encrypted(plaintext) is False
    assert is_encrypted("cualquier texto") is False
    assert is_encrypted("") is False
    assert is_encrypted(None) is False


# ============================================
# TESTS - CAMPOS OPCIONALES
# ============================================

def test_encrypt_optional_field_with_value(sample_data):
    """Test encriptar campo opcional con valor"""
    plaintext = sample_data["name"]
    
    encrypted = encrypt_optional_field(plaintext)
    
    assert encrypted is not None
    assert encrypted != plaintext
    
    decrypted = decrypt_optional_field(encrypted)
    assert decrypted == plaintext


def test_encrypt_optional_field_none():
    """Test encriptar campo opcional None"""
    encrypted = encrypt_optional_field(None)
    assert encrypted is None


def test_encrypt_optional_field_empty():
    """Test encriptar campo opcional vacío"""
    encrypted = encrypt_optional_field("")
    assert encrypted is None  # Cadena vacía se trata como None


def test_decrypt_optional_field_none():
    """Test desencriptar campo opcional None"""
    decrypted = decrypt_optional_field(None)
    assert decrypted is None


# ============================================
# TESTS - INTEGRIDAD DE DATOS
# ============================================

def test_modified_ciphertext_fails(sample_data):
    """Test que datos modificados fallan la verificación"""
    plaintext = sample_data["iban"]
    encrypted = encrypt_field(plaintext)
    
    # Modificar el ciphertext
    parts = encrypted.split(':')
    version, nonce, ciphertext, tag = parts
    
    # Cambiar un byte del ciphertext
    ciphertext_bytes = base64.b64decode(ciphertext)
    modified = bytearray(ciphertext_bytes)
    modified[0] ^= 0xFF  # Flip todos los bits del primer byte
    ciphertext_modified = base64.b64encode(modified).decode()
    
    # Reconstruir datos encriptados modificados
    encrypted_modified = f"{version}:{nonce}:{ciphertext_modified}:{tag}"
    
    # Desencriptación debe fallar
    with pytest.raises(DecryptionError, match="corruptos|incorrecta"):
        decrypt_field(encrypted_modified)


def test_modified_tag_fails(sample_data):
    """Test que tag modificado falla la verificación"""
    plaintext = sample_data["iban"]
    encrypted = encrypt_field(plaintext)
    
    # Modificar el tag
    parts = encrypted.split(':')
    version, nonce, ciphertext, tag = parts
    
    tag_bytes = base64.b64decode(tag)
    modified_tag = bytearray(tag_bytes)
    modified_tag[0] ^= 0xFF
    tag_modified = base64.b64encode(modified_tag).decode()
    
    encrypted_modified = f"{version}:{nonce}:{ciphertext}:{tag_modified}"
    
    # Desencriptación debe fallar
    with pytest.raises(DecryptionError):
        decrypt_field(encrypted_modified)


def test_wrong_nonce_fails(sample_data):
    """Test que nonce incorrecto falla"""
    plaintext = sample_data["iban"]
    encrypted = encrypt_field(plaintext)
    
    # Cambiar el nonce
    parts = encrypted.split(':')
    version, nonce, ciphertext, tag = parts
    
    # Generar nonce diferente
    new_nonce = base64.b64encode(os.urandom(12)).decode()
    
    encrypted_wrong_nonce = f"{version}:{new_nonce}:{ciphertext}:{tag}"
    
    # Desencriptación debe fallar
    with pytest.raises(DecryptionError):
        decrypt_field(encrypted_wrong_nonce)


# ============================================
# TESTS - FORMATO INVÁLIDO
# ============================================

def test_invalid_format_too_few_parts():
    """Test formato con menos de 4 partes"""
    invalid = "1:abc:def"  # Solo 3 partes
    
    with pytest.raises(InvalidFormatError, match="esperado 4 partes"):
        decrypt_field(invalid)


def test_invalid_format_too_many_parts():
    """Test formato con más de 4 partes"""
    invalid = "1:abc:def:ghi:jkl"  # 5 partes
    
    with pytest.raises(InvalidFormatError, match="esperado 4 partes"):
        decrypt_field(invalid)


def test_invalid_version():
    """Test con versión no numérica"""
    invalid = "abc:nonce:ciphertext:tag"
    
    with pytest.raises(InvalidFormatError, match="Versión inválida"):
        decrypt_field(invalid)


def test_invalid_base64():
    """Test con base64 inválido"""
    invalid = "1:not-base64!:also-invalid!:bad-base64!"
    
    with pytest.raises(InvalidFormatError, match="base64"):
        decrypt_field(invalid)


# ============================================
# TESTS - BATCH OPERATIONS
# ============================================

def test_batch_encrypt(sample_data):
    """Test encriptación en lote"""
    plaintexts = [
        sample_data["iban"],
        sample_data["name"],
        sample_data["description"]
    ]
    
    encrypted_list = batch_encrypt(plaintexts)
    
    assert len(encrypted_list) == len(plaintexts)
    
    for encrypted in encrypted_list:
        assert is_encrypted(encrypted)


def test_batch_decrypt(sample_data):
    """Test desencriptación en lote"""
    plaintexts = [
        sample_data["iban"],
        sample_data["name"],
        sample_data["description"]
    ]
    
    encrypted_list = batch_encrypt(plaintexts)
    decrypted_list = batch_decrypt(encrypted_list)
    
    assert decrypted_list == plaintexts


def test_batch_empty_list():
    """Test batch con lista vacía"""
    assert batch_encrypt([]) == []
    assert batch_decrypt([]) == []


# ============================================
# TESTS - KEY MANAGER
# ============================================

def test_key_manager_initialization():
    """Test inicialización del KeyManager"""
    km = get_key_manager()
    
    assert km is not None
    assert km.current_version == 1
    assert len(km.keys) >= 1


def test_key_manager_get_current_key():
    """Test obtener clave actual"""
    km = get_key_manager()
    version, key = km.get_current_key()
    
    assert version == 1
    assert isinstance(key, bytes)
    assert len(key) == 32  # AES-256 requiere 32 bytes


def test_key_manager_get_key_by_version():
    """Test obtener clave por versión"""
    km = get_key_manager()
    key = km.get_key_by_version(1)
    
    assert isinstance(key, bytes)
    assert len(key) == 32


def test_key_manager_invalid_version():
    """Test solicitar versión inexistente"""
    km = get_key_manager()
    
    with pytest.raises(InvalidKeyVersionError, match="no encontrada"):
        km.get_key_by_version(999)


def test_key_manager_add_key_version():
    """Test añadir nueva versión de clave"""
    km = get_key_manager()
    
    # Generar nueva clave
    new_key = base64.b64encode(os.urandom(32)).decode()
    
    # Añadir versión 2
    km.add_key_version(2, new_key, set_as_active=False)
    
    assert 2 in km.keys
    assert km.current_version == 1  # No activada
    
    # Activar versión 2
    km.set_active_version(2)
    assert km.current_version == 2


def test_key_manager_validate_health():
    """Test validación de salud del sistema"""
    km = get_key_manager()
    health = km.validate_key_health()
    
    assert health["is_healthy"] is True
    assert health["total_keys"] >= 1
    assert health["active_version"] == 1
    assert len(health["issues"]) == 0


def test_key_manager_missing_master_key(monkeypatch):
    """Test error cuando falta master key"""
    # Eliminar variable de entorno
    monkeypatch.delenv("ENCRYPTION_MASTER_KEY", raising=False)
    
    _reset_key_manager()
    
    with pytest.raises(MasterKeyNotFoundError, match="no configurada"):
        KeyManager()


def test_key_manager_invalid_key_size(monkeypatch):
    """Test error con tamaño de clave incorrecto"""
    # Clave de 16 bytes (debería ser 32)
    invalid_key = base64.b64encode(os.urandom(16)).decode()
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", invalid_key)
    
    _reset_key_manager()
    
    with pytest.raises(ValueError, match="32 bytes"):
        KeyManager()


# ============================================
# TESTS - ROTACIÓN DE CLAVES
# ============================================

def test_key_rotation_decrypt_old_data():
    """Test que datos encriptados con clave vieja se pueden desencriptar"""
    km = get_key_manager()
    
    # Encriptar con clave v1
    plaintext = "Datos importantes"
    encrypted_v1 = encrypt_field(plaintext)
    
    # Añadir y activar clave v2
    new_key = base64.b64encode(os.urandom(32)).decode()
    km.add_key_version(2, new_key, set_as_active=True)
    
    # Nuevas encriptaciones usan v2
    encrypted_v2 = encrypt_field("Nuevos datos")
    assert encrypted_v2.startswith("2:")
    
    # Pero datos viejos con v1 aún se pueden desencriptar
    decrypted_v1 = decrypt_field(encrypted_v1)
    assert decrypted_v1 == plaintext


# ============================================
# TESTS - DEBUG UTILITIES
# ============================================

def test_debug_encrypted_data(sample_data):
    """Test función de debugging"""
    plaintext = sample_data["iban"]
    encrypted = encrypt_field(plaintext)
    
    info = debug_encrypted_data(encrypted)
    
    assert info["is_valid_format"] is True
    assert info["total_parts"] == 4
    assert info["version"] == 1
    assert info["nonce_length"] == 12
    assert info["tag_length"] == 16
    assert info["nonce_valid"] is True
    assert info["tag_valid"] is True


# ============================================
# TESTS - UNICIDAD DE NONCES
# ============================================

def test_unique_nonces(sample_data):
    """Test que cada encriptación usa un nonce diferente"""
    plaintext = sample_data["iban"]
    
    # Encriptar el mismo texto 10 veces
    encrypted_list = [encrypt_field(plaintext) for _ in range(10)]
    
    # Extraer nonces
    nonces = [enc.split(':')[1] for enc in encrypted_list]
    
    # Verificar que todos son diferentes
    assert len(nonces) == len(set(nonces)), "Nonces duplicados detectados!"


# ============================================
# TESTS - PERFORMANCE (opcional)
# ============================================

def test_encryption_performance(sample_data, benchmark=None):
    """Test de performance de encriptación (si pytest-benchmark instalado)"""
    plaintext = sample_data["description"]
    
    if benchmark:
        result = benchmark(encrypt_field, plaintext)
        assert is_encrypted(result)
    else:
        # Si no hay benchmark, solo ejecutar
        import time
        start = time.time()
        for _ in range(100):
            encrypt_field(plaintext)
        elapsed = time.time() - start
        
        # 100 encriptaciones en menos de 1 segundo
        assert elapsed < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
