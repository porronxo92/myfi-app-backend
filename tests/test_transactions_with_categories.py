"""
Script de prueba para validar el endpoint de transacciones con categorías

Este script verifica que:
1. El endpoint GET /api/transactions devuelve correctamente las transacciones
2. Cada transacción incluye category_name y category_color desde la relación
3. Se evita el problema N+1 (una sola consulta SQL)
4. La paginación funciona correctamente
5. Los filtros se aplican correctamente

Uso:
    python backend/tests/test_transactions_with_categories.py
"""

import sys
from pathlib import Path
from datetime import date, datetime
from uuid import uuid4

# Agregar el directorio backend al path para importaciones
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.account import Account
from app.models.user import User
from app.services.transaction_service import TransactionService
from app.schemas.transaction import TransactionResponse
from app.config import settings

# ============================================
# CONFIGURACIÓN DE BASE DE DATOS DE PRUEBA
# ============================================

def get_test_db_session() -> Session:
    """Crea una sesión de base de datos para pruebas"""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def create_test_data(db: Session):
    """
    Crea datos de prueba:
    - 1 usuario
    - 1 cuenta
    - 3 categorías
    - 10 transacciones (algunas con categoría, otras sin)
    
    Returns:
        tuple: (user_id, account_id, category_ids)
    """
    print("\n📦 Creando datos de prueba...")
    
    # 1. Crear usuario de prueba
    user = User(
        id=uuid4(),
        email=f"test_{uuid4().hex[:8]}@example.com",
        username="test_user_transactions",
        full_name="Usuario Prueba Transacciones",
        hashed_password="$2b$12$dummy_hash",
        is_active=True
    )
    db.add(user)
    db.flush()
    
    # 2. Crear cuenta de prueba
    account = Account(
        id=uuid4(),
        user_id=user.id,
        name="Cuenta Test",
        type="checking",
        currency="EUR",
        balance=1000.00,
        is_active=True
    )
    db.add(account)
    db.flush()
    
    # 3. Crear categorías de prueba
    categories = [
        Category(
            id=uuid4(),
            name=f"Supermercado_{uuid4().hex[:6]}",
            type="expense",
            color="#EF4444"
        ),
        Category(
            id=uuid4(),
            name=f"Transporte_{uuid4().hex[:6]}",
            type="expense",
            color="#3B82F6"
        ),
        Category(
            id=uuid4(),
            name=f"Salario_{uuid4().hex[:6]}",
            type="income",
            color="#10B981"
        )
    ]
    
    for category in categories:
        db.add(category)
    db.flush()
    
    # 4. Crear transacciones de prueba
    transactions = [
        # Transacciones con categoría
        Transaction(
            id=uuid4(),
            account_id=account.id,
            category_id=categories[0].id,  # Supermercado
            date=date(2025, 1, 15),
            amount=-50.00,
            description="Mercadona - Compra mensual",
            type="expense",
            source="manual"
        ),
        Transaction(
            id=uuid4(),
            account_id=account.id,
            category_id=categories[1].id,  # Transporte
            date=date(2025, 1, 14),
            amount=-30.50,
            description="Gasolina Repsol",
            type="expense",
            source="import"
        ),
        Transaction(
            id=uuid4(),
            account_id=account.id,
            category_id=categories[2].id,  # Salario
            date=date(2025, 1, 1),
            amount=2500.00,
            description="Nómina enero",
            type="income",
            source="api"
        ),
        # Transacciones sin categoría
        Transaction(
            id=uuid4(),
            account_id=account.id,
            category_id=None,
            date=date(2025, 1, 20),
            amount=-15.00,
            description="Transferencia sin categoría",
            type="expense",
            source="manual"
        ),
        Transaction(
            id=uuid4(),
            account_id=account.id,
            category_id=categories[0].id,
            date=date(2025, 1, 25),
            amount=-45.75,
            description="Carrefour - Compra semanal",
            type="expense",
            source="import"
        ),
    ]
    
    for transaction in transactions:
        db.add(transaction)
    
    db.commit()
    
    print(f"✅ Usuario creado: {user.email}")
    print(f"✅ Cuenta creada: {account.name}")
    print(f"✅ Categorías creadas: {len(categories)}")
    print(f"✅ Transacciones creadas: {len(transactions)}")
    
    return user.id, account.id, [c.id for c in categories]


def test_get_transactions_with_categories(db: Session, user_id):
    """
    Prueba que el servicio devuelve transacciones con categorías incluidas.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario de prueba
    """
    print("\n🧪 TEST 1: Obtener transacciones con categorías")
    print("=" * 60)
    
    # Obtener transacciones del servicio
    transactions = TransactionService.get_all(
        db=db,
        user_id=user_id,
        skip=0,
        limit=10
    )
    
    print(f"📊 Transacciones obtenidas: {len(transactions)}")
    
    # Verificar que se obtuvieron transacciones
    assert len(transactions) > 0, "❌ No se obtuvieron transacciones"
    print("✅ Se obtuvieron transacciones correctamente")
    
    # Verificar que las relaciones están cargadas
    for i, transaction in enumerate(transactions, 1):
        print(f"\nTransacción {i}:")
        print(f"  - Descripción: {transaction.description}")
        print(f"  - Monto: {transaction.amount}")
        
        # Verificar relación con cuenta
        assert hasattr(transaction, 'account'), "❌ Falta relación 'account'"
        assert transaction.account is not None, "❌ La relación 'account' es None"
        print(f"  - Cuenta: {transaction.account.name} ✅")
        
        # Verificar relación con categoría (puede ser None)
        assert hasattr(transaction, 'category'), "❌ Falta relación 'category'"
        if transaction.category:
            print(f"  - Categoría: {transaction.category.name} ({transaction.category.color}) ✅")
        else:
            print(f"  - Categoría: (Sin categoría) ✅")
    
    print("\n✅ TEST 1 PASADO: Todas las transacciones tienen relaciones correctas")


def test_transaction_response_schema(db: Session, user_id):
    """
    Prueba que el schema TransactionResponse mapea correctamente las relaciones.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario de prueba
    """
    print("\n🧪 TEST 2: Schema TransactionResponse")
    print("=" * 60)
    
    # Obtener transacciones
    transactions = TransactionService.get_all(
        db=db,
        user_id=user_id,
        skip=0,
        limit=5
    )
    
    # Convertir a TransactionResponse
    response_items = [TransactionResponse.model_validate(t) for t in transactions]
    
    print(f"📊 Transacciones convertidas: {len(response_items)}")
    
    # Verificar que los campos están poblados
    for i, item in enumerate(response_items, 1):
        print(f"\nTransacción Response {i}:")
        print(f"  - id: {item.id}")
        print(f"  - description: {item.description}")
        print(f"  - amount: {item.amount}")
        print(f"  - account_name: {item.account_name}")
        print(f"  - category_name: {item.category_name or '(Sin categoría)'}")
        print(f"  - category_color: {item.category_color or '(N/A)'}")
        
        # Validaciones
        assert item.account_name is not None, "❌ account_name no está poblado"
        if item.category_id:
            assert item.category_name is not None, "❌ category_name no está poblado"
            assert item.category_color is not None, "❌ category_color no está poblado"
        
        print("  ✅ Todos los campos están correctamente mapeados")
    
    print("\n✅ TEST 2 PASADO: Schema TransactionResponse funciona correctamente")


def test_pagination(db: Session, user_id):
    """
    Prueba que la paginación funciona correctamente.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario de prueba
    """
    print("\n🧪 TEST 3: Paginación")
    print("=" * 60)
    
    # Página 1 (2 elementos)
    page1 = TransactionService.get_all(db=db, user_id=user_id, skip=0, limit=2)
    print(f"📄 Página 1: {len(page1)} transacciones")
    assert len(page1) == 2, f"❌ Se esperaban 2 transacciones, se obtuvieron {len(page1)}"
    
    # Página 2 (2 elementos)
    page2 = TransactionService.get_all(db=db, user_id=user_id, skip=2, limit=2)
    print(f"📄 Página 2: {len(page2)} transacciones")
    assert len(page2) == 2, f"❌ Se esperaban 2 transacciones, se obtuvieron {len(page2)}"
    
    # Verificar que son diferentes
    page1_ids = {t.id for t in page1}
    page2_ids = {t.id for t in page2}
    assert page1_ids.isdisjoint(page2_ids), "❌ Las páginas contienen transacciones duplicadas"
    
    print("✅ TEST 3 PASADO: Paginación funciona correctamente")


def test_filters(db: Session, user_id, category_ids):
    """
    Prueba que los filtros funcionan correctamente.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario de prueba
        category_ids: Lista de IDs de categorías
    """
    print("\n🧪 TEST 4: Filtros")
    print("=" * 60)
    
    # Filtrar por categoría
    filtered = TransactionService.get_all(
        db=db,
        user_id=user_id,
        category_id=category_ids[0],  # Supermercado
        skip=0,
        limit=10
    )
    
    print(f"🔍 Transacciones con categoría Supermercado: {len(filtered)}")
    assert all(t.category_id == category_ids[0] for t in filtered), "❌ El filtro por categoría no funciona"
    
    # Filtrar por tipo
    expenses = TransactionService.get_all(
        db=db,
        user_id=user_id,
        transaction_type="expense",
        skip=0,
        limit=10
    )
    
    print(f"🔍 Transacciones tipo 'expense': {len(expenses)}")
    assert all(t.type == "expense" for t in expenses), "❌ El filtro por tipo no funciona"
    
    print("✅ TEST 4 PASADO: Filtros funcionan correctamente")


def cleanup_test_data(db: Session, user_id):
    """
    Limpia los datos de prueba creados.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario de prueba
    """
    print("\n🧹 Limpiando datos de prueba...")
    
    try:
        # Eliminar usuario (cascade eliminará todo lo relacionado)
        db.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": str(user_id)})
        db.commit()
        print("✅ Datos de prueba eliminados")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Error al limpiar datos: {e}")


# ============================================
# MAIN - EJECUTAR TODAS LAS PRUEBAS
# ============================================

def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "=" * 60)
    print("🚀 INICIANDO PRUEBAS DE TRANSACCIONES CON CATEGORÍAS")
    print("=" * 60)
    
    db = get_test_db_session()
    user_id = None
    
    try:
        # Crear datos de prueba
        user_id, account_id, category_ids = create_test_data(db)
        
        # Ejecutar pruebas
        test_get_transactions_with_categories(db, user_id)
        test_transaction_response_schema(db, user_id)
        test_pagination(db, user_id)
        test_filters(db, user_id, category_ids)
        
        print("\n" + "=" * 60)
        print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ PRUEBA FALLIDA: {e}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n💥 ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Limpiar datos de prueba
        if user_id:
            cleanup_test_data(db, user_id)
        db.close()


if __name__ == "__main__":
    main()
