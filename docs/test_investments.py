#!/usr/bin/env python3
"""
Script de prueba para el módulo de inversiones
Ejecutar desde el directorio backend/
"""
import requests
import json
from typing import Optional

# Configuración
BASE_URL = "http://localhost:8000/api"
TEST_USER = {
    "email": "test@example.com",  # Cambiar por usuario real
    "password": "test123"          # Cambiar por contraseña real
}

class InvestmentTester:
    def __init__(self):
        self.token: Optional[str] = None
        self.headers = {}
    
    def login(self):
        """Autenticarse y obtener token JWT"""
        print("\n1️⃣  Autenticando usuario...")
        response = requests.post(
            f"{BASE_URL}/users/login",
            json=TEST_USER
        )
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            print(f"✅ Login exitoso. Token: {self.token[:20]}...")
            return True
        else:
            print(f"❌ Error en login: {response.status_code}")
            print(response.text)
            return False
    
    def search_stocks(self, query: str):
        """Buscar acciones por símbolo o nombre"""
        print(f"\n2️⃣  Buscando acciones: '{query}'...")
        response = requests.get(
            f"{BASE_URL}/investments/search",
            params={"q": query},
            headers=self.headers
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Encontradas {len(results)} acciones:")
            for stock in results[:5]:  # Mostrar solo 5
                print(f"   - {stock['symbol']}: {stock['name']} ({stock['region']})")
            return results
        else:
            print(f"❌ Error en búsqueda: {response.status_code}")
            print(response.text)
            return []
    
    def create_investment(self, symbol: str, company_name: str, shares: float, 
                         avg_price: float, purchase_date: str, notes: str = ""):
        """Crear nueva inversión"""
        print(f"\n3️⃣  Creando inversión en {symbol}...")
        data = {
            "symbol": symbol,
            "company_name": company_name,
            "shares": shares,
            "average_price": avg_price,
            "purchase_date": purchase_date,
            "notes": notes
        }
        
        response = requests.post(
            f"{BASE_URL}/investments",
            json=data,
            headers=self.headers
        )
        
        if response.status_code == 201:
            investment = response.json()
            print(f"✅ Inversión creada con ID: {investment['id']}")
            print(f"   {investment['shares']} acciones de {investment['symbol']}")
            print(f"   Precio promedio: ${investment['average_price']}")
            return investment
        else:
            print(f"❌ Error al crear inversión: {response.status_code}")
            print(response.text)
            return None
    
    def get_investments_with_summary(self):
        """Obtener todas las inversiones con resumen e insights"""
        print("\n4️⃣  Obteniendo portfolio completo...")
        response = requests.get(
            f"{BASE_URL}/investments",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            positions = data.get("positions", [])
            summary = data.get("summary", {})
            insights = data.get("insights", [])
            
            print(f"\n✅ Portfolio cargado:")
            print(f"\n📊 RESUMEN DEL PORTFOLIO:")
            print(f"   Valor Total: ${summary.get('total_value', 0):,.2f}")
            print(f"   Invertido: ${summary.get('total_invested', 0):,.2f}")
            print(f"   Ganancia/Pérdida: ${summary.get('total_gain_loss', 0):,.2f} ({summary.get('total_gain_loss_percent', 0):+.2f}%)")
            print(f"   Cambio del día: ${summary.get('day_change', 0):,.2f} ({summary.get('day_change_percent', 0):+.2f}%)")
            print(f"   Posiciones: {summary.get('positions_count', 0)}")
            
            print(f"\n💼 POSICIONES ({len(positions)}):")
            for pos in positions:
                print(f"\n   {pos['symbol']} - {pos['company_name']}")
                print(f"      Acciones: {pos['shares']}")
                print(f"      Precio compra: ${pos['average_price']:.2f}")
                print(f"      Precio actual: ${pos.get('current_price', 0):.2f}")
                print(f"      Valor total: ${pos.get('total_value', 0):,.2f}")
                print(f"      Ganancia/Pérdida: ${pos.get('total_gain_loss', 0):,.2f} ({pos.get('total_gain_loss_percent', 0):+.2f}%)")
            
            if insights:
                print(f"\n💡 INSIGHTS ({len(insights)}):")
                for insight in insights:
                    icon_map = {
                        "success": "✅",
                        "warning": "⚠️",
                        "danger": "🚨",
                        "info": "ℹ️"
                    }
                    icon = icon_map.get(insight['type'], "•")
                    print(f"   {icon} {insight['title']}")
                    print(f"      {insight['message']}")
            
            return data
        else:
            print(f"❌ Error al obtener portfolio: {response.status_code}")
            print(response.text)
            return None
    
    def update_investment(self, investment_id: str, shares: Optional[float] = None,
                         notes: Optional[str] = None):
        """Actualizar una inversión existente"""
        print(f"\n5️⃣  Actualizando inversión {investment_id}...")
        data = {}
        if shares is not None:
            data["shares"] = shares
        if notes is not None:
            data["notes"] = notes
        
        response = requests.patch(
            f"{BASE_URL}/investments/{investment_id}",
            json=data,
            headers=self.headers
        )
        
        if response.status_code == 200:
            investment = response.json()
            print(f"✅ Inversión actualizada:")
            print(f"   {investment['symbol']}: {investment['shares']} acciones")
            return investment
        else:
            print(f"❌ Error al actualizar: {response.status_code}")
            print(response.text)
            return None
    
    def delete_investment(self, investment_id: str):
        """Eliminar una inversión"""
        print(f"\n6️⃣  Eliminando inversión {investment_id}...")
        response = requests.delete(
            f"{BASE_URL}/investments/{investment_id}",
            headers=self.headers
        )
        
        if response.status_code == 204:
            print("✅ Inversión eliminada exitosamente")
            return True
        else:
            print(f"❌ Error al eliminar: {response.status_code}")
            print(response.text)
            return False


def main():
    """Ejecutar suite de pruebas completa"""
    print("=" * 60)
    print("🧪 SUITE DE PRUEBAS - MÓDULO DE INVERSIONES")
    print("=" * 60)
    
    tester = InvestmentTester()
    
    # 1. Login
    if not tester.login():
        print("\n❌ No se pudo autenticar. Verifica las credenciales.")
        return
    
    # 2. Buscar acciones
    results = tester.search_stocks("apple")
    
    # 3. Crear inversión de prueba
    if results:
        stock = results[0]
        investment = tester.create_investment(
            symbol=stock["symbol"],
            company_name=stock["name"],
            shares=10.0,
            avg_price=170.50,
            purchase_date="2024-12-30",
            notes="Inversión de prueba desde script"
        )
        
        created_id = investment["id"] if investment else None
    else:
        created_id = None
        print("\n⚠️  No se encontraron resultados para crear inversión")
    
    # 4. Obtener portfolio completo
    portfolio = tester.get_investments_with_summary()
    
    # 5. Actualizar inversión (si se creó)
    if created_id:
        tester.update_investment(
            investment_id=created_id,
            shares=15.0,
            notes="Actualizada desde script de prueba"
        )
        
        # Volver a obtener portfolio para ver cambios
        print("\n📊 Portfolio después de actualización:")
        tester.get_investments_with_summary()
        
        # 6. Eliminar inversión de prueba
        input("\n⏸️  Presiona ENTER para eliminar la inversión de prueba...")
        tester.delete_investment(created_id)
        
        # Portfolio final
        print("\n📊 Portfolio final:")
        tester.get_investments_with_summary()
    
    print("\n" + "=" * 60)
    print("✅ Suite de pruebas completada")
    print("=" * 60)


if __name__ == "__main__":
    main()
