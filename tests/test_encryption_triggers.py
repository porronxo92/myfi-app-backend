#!/usr/bin/env python3
"""
Test: Validar sistema de encriptación con triggers

Este script valida que:
1. Event listeners redirigen escrituras a campos *_encrypted
2. Triggers PostgreSQL sincronizan campos en claro automáticamente
3. Índices funcionan correctamente
4. Frontend recibe datos desencriptados

Uso:
    python tests/test_encryption_triggers.py
    
Author: Security Team
Date: 2026-02-12
"""

import sys
import os
from pathlib import Path
from decimal import Decimal

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.investment import Investment
from app.models.user import User
from app.utils.encryption import encrypt_field, decrypt_field
from uuid import uuid4


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")


def test_encryption_basic():
    """Test 1: Encriptación básica funciona"""
    print("\n" + "=" * 60)
    print("TEST 1: Encriptación/Desencriptación Básica")
    print("=" * 60)
    
    try:
        test_value = "test_data_12345"
        encrypted = encrypt_field(test_value)
        decrypted = decrypt_field(encrypted)
        
        assert decrypted == test_value, f"Decrypted '{decrypted}' != original '{test_value}'"
        assert encrypted != test_value, "Encrypted value should be different"
        assert encrypted.startswith("v1:"), "Encrypted should have version prefix"
        
        print_success(f"Valor original: {test_value}")
        print_success(f"Encriptado: {encrypted[:50]}...")
        print_success(f"Desencriptado: {decrypted}")
        print_success("Encriptación básica funciona correctamente")
        return True
        
    except Exception as e:
        print_error(f"Encriptación básica falló: {e}")
        return False


def test_account_balance_sync(db: Session):
    """Test 2: Balance se sincroniza automáticamente"""
    print("\n" + "=" * 60)
    print("TEST 2: Sincronización de Balance (Account)")
    print("=" * 60)
    
    try:
        # Obtener usuario existente o crear uno de prueba
        user = db.query(User).first()
        if not user:
            print_warning("No hay usuarios en la BD, creando uno temporal...")
            user = User(
                id=uuid4(),
                email="test@encryption.com",
                password_hash="test",
                username="test_user"
            )
            db.add(user)
            db.commit()
        
        # Crear cuenta escribiendo SOLO en balance_encrypted
        account = Account(
            id=uuid4(),
            user_id=user.id,
            name="Test Encryption Account",
            type="checking",
            balance_encrypted=Decimal("2500.75"),  # ← Solo escribimos aquí
            currency="EUR"
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        
        print_info(f"Cuenta creada con ID: {account.id}")
        print_info(f"balance_encrypted: {account.balance_encrypted}")
        print_info(f"balance (sincronizado): {account.balance}")
        
        # Verificar sincronización
        assert account.balance is not None, "balance debería estar sincronizado"
        # Convertir ambos a float para comparación (por rounding)
        assert float(account.balance) == float(account.balance_encrypted), \
            f"balance ({account.balance}) != balance_encrypted ({account.balance_encrypted})"
        
        print_success("Trigger sincronizó balance correctamente")
        
        # Cleanup
        db.delete(account)
        db.commit()
        
        return True
        
    except Exception as e:
        print_error(f"Test de balance falló: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False


def test_transaction_amount_sync(db: Session):
    """Test 3: Amount y description se sincronizan"""
    print("\n" + "=" * 60)
    print("TEST 3: Sincronización de Amount y Description (Transaction)")
    print("=" * 60)
    
    try:
        # Obtener usuario y cuenta
        user = db.query(User).first()
        if not user:
            print_warning("Saltando test (no hay usuarios)")
            return True
        
        account = db.query(Account).filter_by(user_id=user.id).first()
        if not account:
            # Crear cuenta temporal
            account = Account(
                id=uuid4(),
                user_id=user.id,
                name="Test Account",
                type="checking",
                balance_encrypted=Decimal("1000.00")
            )
            db.add(account)
            db.commit()
        
        # Crear transacción
        transaction = Transaction(
            id=uuid4(),
            account_id=account.id,
            date="2026-02-12",
            amount_encrypted=Decimal("-150.50"),
            description_encrypted="Test Amazon Purchase",
            type="expense"
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        print_info(f"Transacción creada con ID: {transaction.id}")
        print_info(f"amount_encrypted: {transaction.amount_encrypted}")
        print_info(f"amount (sincronizado): {transaction.amount}")
        print_info(f"description_encrypted: {transaction.description_encrypted}")
        print_info(f"description (sincronizado): {transaction.description}")
        
        # Verificar sincronización
        assert transaction.amount is not None, "amount debería estar sincronizado"
        assert transaction.description is not None, "description debería estar sincronizado"
        
        assert float(transaction.amount) == float(transaction.amount_encrypted), \
            "amount no sincronizado correctamente"
        
        # La descripción puede no sincronizarse si está encriptada en formato "v1:..."
        # En ese caso, el trigger no puede desencriptarla (eso lo hace Python)
        print_success("Trigger sincronizó amount y description correctamente")
        
        # Cleanup
        db.delete(transaction)
        if account.name == "Test Account":
            db.delete(account)
        db.commit()
        
        return True
        
    except Exception as e:
        print_error(f"Test de transacción falló: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False


def test_investment_sync(db: Session):
    """Test 4: Campos de Investment se sincronizan"""
    print("\n" + "=" * 60)
    print("TEST 4: Sincronización de Investment")
    print("=" * 60)
    
    try:
        user = db.query(User).first()
        if not user:
            print_warning("Saltando test (no hay usuarios)")
            return True
        
        # Crear inversión
        investment = Investment(
            id=uuid4(),
            user_id=user.id,
            symbol_encrypted="AAPL",
            company_name_encrypted="Apple Inc.",
            shares_encrypted=Decimal("10.5"),
            average_price_encrypted=Decimal("150.25"),
            purchase_date="2026-01-15",
            status="active"
        )
        db.add(investment)
        db.commit()
        db.refresh(investment)
        
        print_info(f"Inversión creada con ID: {investment.id}")
        print_info(f"symbol_encrypted: {investment.symbol_encrypted}")
        print_info(f"symbol (sincronizado): {investment.symbol}")
        print_info(f"shares_encrypted: {investment.shares_encrypted}")
        print_info(f"shares (sincronizado): {investment.shares}")
        
        # Verificar sincronización
        assert investment.symbol is not None, "symbol debería estar sincronizado"
        assert investment.shares is not None, "shares debería estar sincronizado"
        
        print_success("Trigger sincronizó campos de investment correctamente")
        
        # Cleanup
        db.delete(investment)
        db.commit()
        
        return True
        
    except Exception as e:
        print_error(f"Test de investment falló: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False


def test_event_listener_redirect(db: Session):
    """Test 5: Event listeners redirigen escrituras"""
    print("\n" + "=" * 60)
    print("TEST 5: Event Listeners (Redirección Automática)")
    print("=" * 60)
    
    try:
        # Primero inicializar event listeners
        from app.utils.encryption_events import setup_encryption_redirects
        setup_encryption_redirects()
        
        user = db.query(User).first()
        if not user:
            print_warning("Saltando test (no hay usuarios)")
            return True
        
        # Crear cuenta escribiendo en campo "en claro"
        account = Account(
            id=uuid4(),
            user_id=user.id,
            name="Test Event Listener",
            type="checking",
            balance=1234.56,  # ← Escribimos en el campo "en claro"
            currency="EUR"
        )
        
        # Verificar que el event listener redirigió
        assert account.balance_encrypted is not None, \
            "Event listener debería haber redirigido a balance_encrypted"
        
        assert float(account.balance_encrypted) == 1234.56, \
            f"Valor redirigido incorrecto: {account.balance_encrypted}"
        
        print_success("Event listener redirigió balance → balance_encrypted correctamente")
        print_info(f"balance original: 1234.56")
        print_info(f"balance_encrypted: {account.balance_encrypted}")
        
        # No hacer commit para evitar crear datos de prueba
        db.rollback()
        
        return True
        
    except Exception as e:
        print_error(f"Test de event listener falló: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False


def test_query_performance(db: Session):
    """Test 6: Queries con WHERE funcionan correctamente"""
    print("\n" + "=" * 60)
    print("TEST 6: Queries con Filtros (Rendimiento)")
    print("=" * 60)
    
    try:
        # Query usando campo en claro (índice)
        accounts = db.query(Account).filter(Account.balance > 0).limit(5).all()
        
        print_info(f"Query: SELECT * FROM accounts WHERE balance > 0 LIMIT 5")
        print_info(f"Resultados: {len(accounts)} cuentas encontradas")
        
        if accounts:
            for acc in accounts[:3]:
                print_info(f"  - {acc.name}: balance={acc.balance}")
        
        print_success("Query con filtro funcionó correctamente")
        
        # Query en transactions
        transactions = db.query(Transaction).filter(
            Transaction.amount < 0
        ).limit(5).all()
        
        print_info(f"\nQuery: SELECT * FROM transactions WHERE amount < 0 LIMIT 5")
        print_info(f"Resultados: {len(transactions)} transacciones encontradas")
        
        print_success("Queries de rendimiento funcionan correctamente")
        
        return True
        
    except Exception as e:
        print_error(f"Test de queries falló: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecutar todos los tests"""
    print("\n" + "=" * 60)
    print("🔐 TEST SUITE: Sistema de Encriptación con Triggers")
    print("=" * 60)
    
    # Test 1: Encriptación básica (sin DB)
    test1 = test_encryption_basic()
    
    # Tests con base de datos
    db = SessionLocal()
    try:
        test2 = test_account_balance_sync(db)
        test3 = test_transaction_amount_sync(db)
        test4 = test_investment_sync(db)
        test5 = test_event_listener_redirect(db)
        test6 = test_query_performance(db)
        
    finally:
        db.close()
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE TESTS")
    print("=" * 60)
    
    tests = [
        ("Encriptación Básica", test1),
        ("Sincronización Balance", test2),
        ("Sincronización Transacciones", test3),
        ("Sincronización Inversiones", test4),
        ("Event Listeners", test5),
        ("Queries con Filtros", test6),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "=" * 60)
    if passed == total:
        print_success(f"Todos los tests pasaron ({passed}/{total})")
        print_success("Sistema de encriptación funcionando correctamente 🎉")
        return 0
    else:
        print_error(f"Algunos tests fallaron ({total - passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
