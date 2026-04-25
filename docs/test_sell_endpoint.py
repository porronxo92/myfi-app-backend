"""
Script de Prueba: Endpoint de Venta de Posiciones
==================================================
Prueba el nuevo endpoint POST /api/investments/{id}/sell

Requiere:
- Backend corriendo en http://localhost:8000
- Usuario autenticado con token JWT
- Al menos una posición activa

Uso:
    python test_sell_endpoint.py
"""

import requests
import json
from datetime import date

# ============================================
# CONFIGURACIÓN
# ============================================
BASE_URL = "http://localhost:8000"
EMAIL = "test@example.com"  # Cambiar por tu usuario
PASSWORD = "password123"     # Cambiar por tu contraseña

# ============================================
# 1. LOGIN - Obtener Token
# ============================================
def login():
    print("🔐 Iniciando sesión...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data["accessToken"]
        print(f"✅ Login exitoso. Token: {token[:20]}...")
        return token
    else:
        print(f"❌ Error en login: {response.status_code}")
        print(response.text)
        return None


# ============================================
# 2. OBTENER POSICIONES ACTIVAS
# ============================================
def get_positions(token):
    print("\n📊 Obteniendo posiciones activas...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/api/investments", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        positions = data["positions"]
        print(f"✅ Encontradas {len(positions)} posiciones activas")
        
        for i, pos in enumerate(positions):
            print(f"\n  [{i}] {pos['companyName']} ({pos['symbol']})")
            print(f"      ID: {pos['id']}")
            print(f"      Acciones: {pos['shares']}")
            print(f"      Precio Compra: ${pos['averagePrice']}")
            print(f"      Precio Actual: ${pos['currentPrice']}")
            print(f"      Valor: ${pos['totalValue']}")
        
        return positions
    else:
        print(f"❌ Error obteniendo posiciones: {response.status_code}")
        return []


# ============================================
# 3. VENDER POSICIÓN
# ============================================
def sell_position(token, position_id, sale_price, notes=""):
    print(f"\n💰 Vendiendo posición {position_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "salePrice": sale_price,
        "saleDate": str(date.today()),
        "notes": notes
    }
    
    print(f"   Datos de venta: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/api/investments/{position_id}/sell",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Posición vendida exitosamente")
        print(f"\n   Resultado:")
        print(f"   - Status: {data.get('status')}")
        print(f"   - Precio Venta: ${data.get('salePrice')}")
        print(f"   - Fecha Venta: {data.get('saleDate')}")
        print(f"   - Notas: {data.get('notes')}")
        
        # Calcular ganancia/pérdida
        purchase_price = data.get('averagePrice')
        shares = data.get('shares')
        profit = (sale_price - purchase_price) * shares
        profit_percent = ((sale_price - purchase_price) / purchase_price) * 100
        
        print(f"\n   💵 Ganancia/Pérdida:")
        print(f"   - Total: ${profit:.2f}")
        print(f"   - Porcentaje: {profit_percent:+.2f}%")
        
        return data
    else:
        print(f"❌ Error vendiendo posición: {response.status_code}")
        print(response.text)
        return None


# ============================================
# 4. VERIFICAR QUE YA NO APARECE EN ACTIVAS
# ============================================
def verify_sold(token, position_id):
    print(f"\n🔍 Verificando que posición {position_id} ya no está en activas...")
    positions = get_positions(token)
    
    active_ids = [p["id"] for p in positions]
    
    if position_id not in active_ids:
        print("✅ Confirmado: La posición ya no aparece en lista de activas")
        print("   (Status cambiado a 'sold', se mantiene en BD para historial)")
    else:
        print("❌ ERROR: La posición aún aparece en activas")


# ============================================
# MAIN - Flujo Completo
# ============================================
def main():
    print("=" * 60)
    print("  TEST: Endpoint de Venta de Posiciones")
    print("=" * 60)
    
    # 1. Login
    token = login()
    if not token:
        return
    
    # 2. Obtener posiciones
    positions = get_positions(token)
    if not positions:
        print("\n⚠️  No hay posiciones activas para vender")
        return
    
    # 3. Seleccionar posición a vender
    print("\n" + "=" * 60)
    position_index = int(input(f"Selecciona posición a vender (0-{len(positions)-1}): "))
    
    if position_index < 0 or position_index >= len(positions):
        print("❌ Índice inválido")
        return
    
    position = positions[position_index]
    
    # 4. Solicitar precio de venta
    current_price = position["currentPrice"]
    print(f"\nPrecio actual de mercado: ${current_price}")
    sale_price = float(input("Precio de venta: "))
    
    notes = input("Notas (opcional): ")
    
    # 5. Confirmar
    print("\n" + "=" * 60)
    print("RESUMEN DE VENTA:")
    print(f"  Acción: {position['companyName']} ({position['symbol']})")
    print(f"  Acciones: {position['shares']}")
    print(f"  Precio Compra: ${position['averagePrice']}")
    print(f"  Precio Venta: ${sale_price}")
    
    profit = (sale_price - position['averagePrice']) * position['shares']
    profit_percent = ((sale_price - position['averagePrice']) / position['averagePrice']) * 100
    
    print(f"\n  Ganancia/Pérdida Estimada:")
    print(f"  - ${profit:.2f} ({profit_percent:+.2f}%)")
    print("=" * 60)
    
    confirm = input("\n¿Confirmar venta? (s/n): ")
    if confirm.lower() != 's':
        print("❌ Venta cancelada")
        return
    
    # 6. Ejecutar venta
    result = sell_position(token, position["id"], sale_price, notes)
    
    if result:
        # 7. Verificar que ya no está en activas
        verify_sold(token, position["id"])
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operación cancelada por usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
