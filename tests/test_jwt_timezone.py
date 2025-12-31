"""
Script de prueba para verificar que los tokens JWT se crean correctamente
con timezone UTC aware
"""
from datetime import datetime, timezone, timedelta
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.jwt import create_access_token, create_refresh_token
from app.config import settings

def test_token_creation():
    print("\n" + "="*60)
    print("PRUEBA DE CREACIÓN DE TOKENS JWT")
    print("="*60)
    
    # Mostrar zona horaria local
    local_now = datetime.now()
    utc_now = datetime.now(timezone.utc)
    
    print(f"\n📍 Zona horaria del sistema:")
    print(f"   Hora local:     {local_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Hora UTC:       {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Offset:         {local_now.astimezone().strftime('%z')}")
    
    # Crear tokens
    print(f"\n🔑 Creando tokens JWT...")
    print(f"   Access token expira en: {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES} minutos")
    print(f"   Refresh token expira en: {settings.REFRESH_TOKEN_EXPIRE_DAYS} días")
    
    user_data = {"sub": "123e4567-e89b-12d3-a456-426614174000"}
    
    # Crear access token
    print(f"\n🔐 Creando access token...")
    access_token = create_access_token(data=user_data)
    
    # Crear refresh token
    print(f"\n🔄 Creando refresh token...")
    refresh_token = create_refresh_token(data=user_data)
    
    # Verificar expiración
    from jose import jwt
    
    access_payload = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    refresh_payload = jwt.decode(refresh_token, settings.REFRESH_TOKEN_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    
    access_exp = datetime.fromtimestamp(access_payload['exp'], tz=timezone.utc)
    refresh_exp = datetime.fromtimestamp(refresh_payload['exp'], tz=timezone.utc)
    
    print(f"\n✅ TOKENS CREADOS CORRECTAMENTE")
    print(f"\n📊 Detalles:")
    print(f"   Access Token:")
    print(f"      - Expira:        {access_exp.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"      - Tiempo restante: {(access_exp - utc_now).total_seconds() / 60:.1f} minutos")
    print(f"      - ¿Válido?:      {'✅ SÍ' if access_exp > utc_now else '❌ NO (¡EXPIRADO!)'}")
    
    print(f"\n   Refresh Token:")
    print(f"      - Expira:        {refresh_exp.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"      - Tiempo restante: {(refresh_exp - utc_now).total_seconds() / 86400:.1f} días")
    print(f"      - ¿Válido?:      {'✅ SÍ' if refresh_exp > utc_now else '❌ NO (¡EXPIRADO!)'}")
    
    # Validar que no estén expirados
    if access_exp > utc_now and refresh_exp > utc_now:
        print(f"\n{'='*60}")
        print("✅ ¡PRUEBA EXITOSA! Los tokens se crean correctamente")
        print("="*60)
        return True
    else:
        print(f"\n{'='*60}")
        print("❌ ERROR: Los tokens nacen expirados")
        print("="*60)
        return False

if __name__ == "__main__":
    success = test_token_creation()
    sys.exit(0 if success else 1)
