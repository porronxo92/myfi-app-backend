#!/usr/bin/env python3
"""
Script de diagnóstico para verificar configuración de encriptación

Uso:
    python scripts/test_encryption_config.py
"""

import sys
import os
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Cargar .env explícitamente
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
print("=" * 60)
print("🔍 DIAGNÓSTICO DE CONFIGURACIÓN DE ENCRIPTACIÓN")
print("=" * 60)
print(f"\n1. Verificando archivo .env...")
print(f"   Ruta: {env_path}")
print(f"   Existe: {'✅ SÍ' if env_path.exists() else '❌ NO'}")

if env_path.exists():
    load_dotenv(env_path)
    print(f"   ✅ Archivo .env cargado correctamente")
else:
    print(f"   ⚠️  Archivo .env no encontrado")

print(f"\n2. Verificando variable ENCRYPTION_MASTER_KEY...")

# Verificar desde os.getenv()
env_key = os.getenv("ENCRYPTION_MASTER_KEY")
print(f"   Desde os.getenv(): {'✅ Configurada' if env_key else '❌ No encontrada'}")
if env_key:
    print(f"   Longitud: {len(env_key)} caracteres")
    # Mostrar solo primeros y últimos 4 caracteres
    if len(env_key) > 8:
        masked = env_key[:4] + "..." + env_key[-4:]
        print(f"   Valor (parcial): {masked}")

# Verificar desde settings
print(f"\n3. Verificando desde Pydantic Settings...")
try:
    from app.config import settings
    settings_key = settings.ENCRYPTION_MASTER_KEY
    print(f"   Desde settings:    {'✅ Configurada' if settings_key else '❌ No encontrada'}")
    if settings_key:
        print(f"   Longitud: {len(settings_key)} caracteres")
        print(f"   Versión de clave: {settings.ENCRYPTION_KEY_VERSION}")
except Exception as e:
    print(f"   ❌ Error al cargar settings: {e}")
    import traceback
    traceback.print_exc()

# Probar key_management
print(f"\n4. Verificando KeyManager...")
try:
    from app.utils.key_management import KeyManager
    
    km = KeyManager()
    version, key = km.get_current_key()
    
    print(f"   ✅ KeyManager inicializado correctamente")
    print(f"   Versión de clave activa: {version}")
    print(f"   Longitud de clave: {len(key)} bytes")
    
except Exception as e:
    print(f"   ❌ Error al inicializar KeyManager: {e}")
    import traceback
    traceback.print_exc()

# Probar encriptación/desencriptación
print(f"\n5. Probando encriptación/desencriptación...")
try:
    from app.utils.encryption import encrypt_field, decrypt_field
    
    test_value = "Hola Mundo! 🔐"
    print(f"   Texto original: {test_value}")
    
    encrypted = encrypt_field(test_value)
    print(f"   ✅ Encriptado: {encrypted[:50]}..." if len(encrypted) > 50 else f"   ✅ Encriptado: {encrypted}")
    
    decrypted = decrypt_field(encrypted)
    print(f"   Desencriptado: {decrypted}")
    
    if decrypted == test_value:
        print(f"   ✅ Encriptación/desencriptación funcionando correctamente")
    else:
        print(f"   ❌ ERROR: El valor desencriptado no coincide")
        print(f"      Esperado: {test_value}")
        print(f"      Obtenido: {decrypted}")
        
except Exception as e:
    print(f"   ❌ Error durante encriptación: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnóstico completado")
print("=" * 60)
