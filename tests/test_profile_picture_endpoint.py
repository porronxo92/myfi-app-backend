"""
Test script para el endpoint PUT /api/users/me/profile-picture
"""
import requests
import base64
import sys

# Configuración
BASE_URL = "http://127.0.0.1:8000"
TEST_EMAIL = "ruben_cruz92@hotmail.com"  # Cambiar por un usuario válido
TEST_PASSWORD = "tu_password"  # Cambiar por la contraseña correcta

# Imagen de prueba pequeña (1x1 pixel PNG transparente en base64)
SMALL_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

# Formato data URL completo
DATA_URL = f"data:image/png;base64,{SMALL_PNG_BASE64}"


def login():
    """Login y obtener token"""
    print("=" * 60)
    print("1. LOGIN")
    print("=" * 60)
    
    response = requests.post(f"{BASE_URL}/api/users/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"✅ Login exitoso - Token obtenido")
        return token
    else:
        print(f"❌ Login fallido: {response.status_code}")
        print(f"   {response.text}")
        return None


def test_profile_picture_with_data_url(token):
    """Test con data URL completa"""
    print("\n" + "=" * 60)
    print("2. TEST: Actualizar con data URL")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    body = {
        "profile_picture": DATA_URL
    }
    
    response = requests.put(
        f"{BASE_URL}/api/users/me/profile-picture",
        json=body,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        user = response.json()
        print(f"✅ Foto de perfil actualizada")
        print(f"   Email: {user.get('email')}")
        print(f"   Profile picture (primeros 50 chars): {user.get('profile_picture', '')[:50]}...")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


def test_profile_picture_with_base64(token):
    """Test con base64 puro (sin data URL)"""
    print("\n" + "=" * 60)
    print("3. TEST: Actualizar con base64 puro")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    body = {
        "profile_picture": SMALL_PNG_BASE64
    }
    
    response = requests.put(
        f"{BASE_URL}/api/users/me/profile-picture",
        json=body,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        user = response.json()
        print(f"✅ Foto de perfil actualizada")
        print(f"   Email: {user.get('email')}")
        print(f"   Profile picture (primeros 50 chars): {user.get('profile_picture', '')[:50]}...")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


def test_invalid_base64(token):
    """Test con base64 inválido (debe fallar)"""
    print("\n" + "=" * 60)
    print("4. TEST: Base64 inválido (espera error 400)")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    body = {
        "profile_picture": "esto_no_es_base64_válido!!!"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/users/me/profile-picture",
        json=body,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 400:
        print(f"✅ Validación correcta - rechazó base64 inválido")
        print(f"   Error: {response.json().get('detail')}")
        return True
    else:
        print(f"❌ Debería haber rechazado el base64 inválido")
        return False


def main():
    print("=" * 60)
    print("TEST: Endpoint /me/profile-picture")
    print("=" * 60)
    
    # Login
    token = login()
    if not token:
        print("\n❌ No se pudo obtener token - verifica credenciales")
        print("   Edita el archivo y actualiza TEST_EMAIL y TEST_PASSWORD")
        return 1
    
    # Tests
    results = {
        "data_url": test_profile_picture_with_data_url(token),
        "base64_puro": test_profile_picture_with_base64(token),
        "validacion": test_invalid_base64(token)
    }
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    
    passed = sum([1 for v in results.values() if v])
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed} / {total} tests pasaron")
    
    if passed == total:
        print("\n🎉 TODOS LOS TESTS PASARON")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
