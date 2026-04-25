"""
Script de Instalación y Validación - Sistema de Encriptación PSD2

Este script:
1. Instala las dependencias necesarias
2. Genera claves de encriptación si no existen
3. Valida la configuración
4. Ejecuta tests básicos

Ejecutar con:
    python scripts/setup_encryption.py

Author: Security Team
Date: 2026-02-01
"""

import os
import sys
import subprocess
import base64
from pathlib import Path

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Imprime encabezado destacado"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    """Imprime mensaje de éxito"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    """Imprime advertencia"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    """Imprime error"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    """Imprime información"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def check_python_version():
    """Verifica versión de Python"""
    print_info("Verificando versión de Python...")
    
    if sys.version_info < (3, 9):
        print_error(f"Python 3.9+ requerido. Versión actual: {sys.version}")
        return False
    
    print_success(f"Python {sys.version_info.major}.{sys.version_info.minor} ✓")
    return True

def install_dependencies():
    """Instala dependencias desde requirements.txt"""
    print_info("Instalando dependencias...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True,
            check=True
        )
        print_success("Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error instalando dependencias: {e.stderr}")
        return False

def verify_cryptography():
    """Verifica que cryptography está instalada correctamente"""
    print_info("Verificando instalación de cryptography...")
    
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        print_success("Librería cryptography disponible ✓")
        return True
    except ImportError as e:
        print_error(f"Error importando cryptography: {e}")
        return False

def generate_encryption_key():
    """Genera una nueva clave de encriptación"""
    key = base64.b64encode(os.urandom(32)).decode()
    return key

def check_env_file():
    """Verifica existencia de archivo .env"""
    print_info("Verificando archivo .env...")
    
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if not env_path.exists():
        print_warning("Archivo .env no encontrado")
        
        if env_example_path.exists():
            print_info("Creando .env desde .env.example...")
            
            # Copiar .env.example a .env
            with open(env_example_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print_success(".env creado desde plantilla")
            return True
        else:
            print_error("No se encuentra .env.example")
            return False
    else:
        print_success(".env encontrado ✓")
        return True

def update_env_with_keys():
    """Actualiza .env con claves generadas si no existen"""
    print_info("Verificando claves en .env...")
    
    env_path = Path(".env")
    
    if not env_path.exists():
        print_error(".env no existe")
        return False
    
    # Leer contenido actual
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Variables a verificar/generar
    keys_to_check = {
        'JWT_SECRET_KEY': None,
        'REFRESH_TOKEN_SECRET_KEY': None,
        'ENCRYPTION_MASTER_KEY': None
    }
    
    needs_update = False
    
    # Verificar qué claves faltan
    for line in lines:
        line = line.strip()
        for key in keys_to_check:
            if line.startswith(f"{key}="):
                value = line.split('=', 1)[1]
                # Verificar si es valor de ejemplo/placeholder
                if value and not value.startswith('REEMPLAZAR') and not value.startswith('your-'):
                    keys_to_check[key] = value
    
    # Generar claves faltantes
    for key, value in keys_to_check.items():
        if value is None:
            needs_update = True
            if key == 'ENCRYPTION_MASTER_KEY':
                # Clave de 32 bytes en base64
                new_value = generate_encryption_key()
                print_warning(f"{key} no configurada, generando...")
            else:
                # JWT keys (48 chars)
                import secrets
                new_value = secrets.token_urlsafe(48)
                print_warning(f"{key} no configurada, generando...")
            
            keys_to_check[key] = new_value
            print_success(f"{key} generada ✓")
    
    if needs_update:
        # Actualizar archivo .env
        new_lines = []
        for line in lines:
            updated = False
            for key, value in keys_to_check.items():
                if line.strip().startswith(f"{key}="):
                    new_lines.append(f"{key}={value}\n")
                    updated = True
                    break
            if not updated:
                new_lines.append(line)
        
        # Escribir archivo actualizado
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print_success("Archivo .env actualizado con nuevas claves")
        
        # Mostrar las claves generadas
        print(f"\n{Colors.BOLD}⚠️  IMPORTANTE: Guarda estas claves en lugar seguro{Colors.END}")
        for key, value in keys_to_check.items():
            print(f"\n{Colors.YELLOW}{key}:{Colors.END}")
            print(f"  {value}")
        
        print(f"\n{Colors.BOLD}⚠️  Las claves han sido guardadas en .env{Colors.END}")
        print(f"{Colors.BOLD}⚠️  Haz backup del archivo .env en ubicación segura{Colors.END}\n")
    else:
        print_success("Todas las claves están configuradas ✓")
    
    return True

def run_basic_tests():
    """Ejecuta tests básicos de encriptación"""
    print_info("Ejecutando tests básicos...")
    
    try:
        # Cargar variables de entorno
        from dotenv import load_dotenv
        load_dotenv()
        
        # Importar módulos
        from app.utils.encryption import encrypt_field, decrypt_field, is_encrypted
        from app.utils.key_management import get_key_manager
        
        # Test 1: KeyManager
        print_info("Test 1: Inicialización de KeyManager...")
        km = get_key_manager()
        version, key = km.get_current_key()
        assert len(key) == 32, "Clave debe ser 32 bytes"
        print_success("KeyManager funciona correctamente")
        
        # Test 2: Encriptación básica
        print_info("Test 2: Encriptación/Desencriptación...")
        test_data = "ES91 2100 0418 4502 0005 1332"
        encrypted = encrypt_field(test_data)
        assert is_encrypted(encrypted), "Dato no parece encriptado"
        decrypted = decrypt_field(encrypted)
        assert decrypted == test_data, "Dato desencriptado no coincide"
        print_success("Encriptación funciona correctamente")
        
        # Test 3: Formato
        print_info("Test 3: Formato de datos encriptados...")
        parts = encrypted.split(':')
        assert len(parts) == 4, "Formato incorrecto"
        print_success("Formato correcto")
        
        # Test 4: Unicode
        print_info("Test 4: Caracteres Unicode...")
        unicode_data = "Juan Pérez García - Ñoño"
        encrypted_unicode = encrypt_field(unicode_data)
        decrypted_unicode = decrypt_field(encrypted_unicode)
        assert decrypted_unicode == unicode_data
        print_success("Unicode funciona correctamente")
        
        print_success("\n✅ Todos los tests básicos pasaron correctamente\n")
        return True
        
    except Exception as e:
        print_error(f"Error en tests: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_full_tests():
    """Ejecuta suite completa de tests con pytest"""
    print_info("Ejecutando suite completa de tests...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_encryption.py", "-v"],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        
        if result.returncode == 0:
            print_success("Todos los tests pasaron ✅")
            return True
        else:
            print_error("Algunos tests fallaron")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print_warning("pytest no instalado, saltando tests completos")
        print_info("Instalar con: pip install pytest")
        return True
    except Exception as e:
        print_error(f"Error ejecutando tests: {e}")
        return False

def print_next_steps():
    """Imprime pasos siguientes"""
    print_header("PRÓXIMOS PASOS")
    
    print(f"{Colors.BOLD}1. Configurar base de datos:{Colors.END}")
    print(f"   - Actualizar DATABASE_URL en .env")
    print(f"   - Ejecutar migraciones: alembic upgrade head\n")
    
    print(f"{Colors.BOLD}2. Variables de entorno adicionales:{Colors.END}")
    print(f"   - GEMINI_API_KEY (para análisis IA)")
    print(f"   - FINNHUB_API_KEY (para datos de mercado)")
    print(f"   - Revisar .env.example para lista completa\n")
    
    print(f"{Colors.BOLD}3. Iniciar aplicación:{Colors.END}")
    print(f"   - Desarrollo: uvicorn app.main:app --reload")
    print(f"   - Producción: uvicorn app.main:app --host 0.0.0.0 --port 8000\n")
    
    print(f"{Colors.BOLD}4. Documentación:{Colors.END}")
    print(f"   - PSD2 Compliance: docs/PSD2_COMPLIANCE.md")
    print(f"   - Guía Encriptación: docs/ENCRYPTION_GUIDE.md\n")
    
    print(f"{Colors.BOLD}⚠️  IMPORTANTE - SEGURIDAD:{Colors.END}")
    print(f"   - NUNCA commitear el archivo .env a git")
    print(f"   - Hacer backup de ENCRYPTION_MASTER_KEY en lugar seguro")
    print(f"   - Cambiar todas las claves antes de ir a producción")
    print(f"   - Usar HTTPS en producción\n")

def main():
    """Función principal"""
    print_header("SETUP - SISTEMA DE ENCRIPTACIÓN PSD2")
    
    # Paso 1: Verificar Python
    if not check_python_version():
        sys.exit(1)
    
    # Paso 2: Instalar dependencias
    if not install_dependencies():
        print_error("Instalación fallida")
        sys.exit(1)
    
    # Paso 3: Verificar cryptography
    if not verify_cryptography():
        print_error("cryptography no está disponible")
        sys.exit(1)
    
    # Paso 4: Verificar/crear .env
    if not check_env_file():
        print_error("No se pudo configurar .env")
        sys.exit(1)
    
    # Paso 5: Generar claves si faltan
    if not update_env_with_keys():
        print_error("No se pudieron generar claves")
        sys.exit(1)
    
    # Paso 6: Tests básicos
    if not run_basic_tests():
        print_error("Tests básicos fallaron")
        sys.exit(1)
    
    # Paso 7: Tests completos (opcional)
    print("\n")
    response = input("¿Ejecutar suite completa de tests? (s/N): ").lower()
    if response == 's':
        run_full_tests()
    
    # Éxito
    print_header("✅ INSTALACIÓN COMPLETADA")
    print_success("Sistema de encriptación PSD2 configurado correctamente\n")
    
    print_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Instalación cancelada por usuario{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
