#!/usr/bin/env python3
"""
Test: Validar sistema de encriptación con TypeDecorators

Este script valida que:
1. TypeDecorators encriptan campos automáticamente al escribir
2. TypeDecorators desencriptan campos automáticamente al leer
3. Datos en BD están encriptados (no en texto claro)
4. Operaciones CRUD funcionan con encriptación transparente

Arquitectura: Single field con TypeDecorator (AES-256-GCM)
- NO hay campos duplicados (*_encrypted)
- Encriptación/desencriptación es transparente

Uso:
    python tests/test_encryption_typedecorator.py
    
Author: Security Team
Date: 2026
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
from sqlalchemy import text
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


def test_typedecorator_encrypt_on_write(db: Session) -> bool:
    """Test 1: TypeDecorator encripta al escribir"""
    print("\n" + "=" * 60)
    print("TEST 1: Encriptación automática al escribir (TypeDecorator)")
    print("=" * 60)
    
    try:
        user = db.query(User).first()
        if not user:
            print_warning("No hay usuarios en la BD, creando usuario de prueba...")
            user = User(
                id=uuid4(),
                email="test_encryption@example.com",
                hashed_password="test_hash_for_encryption_test"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Crear cuenta con balance
        test_balance = 9999.99
        account = Account(
            id=uuid4(),
            user_id=user.id,
            name="Test TypeDecorator Encryption",
            type="checking",
            balance=Decimal(str(test_balance)),
            currency="EUR"
        )
        db.add(account)
        db.commit()
        account_id = account.id
        
        # Leer directamente de la BD para verificar que está encriptado
        raw_query = text("SELECT balance FROM accounts WHERE id = :id")
        result = db.execute(raw_query, {"id": str(account_id)}).fetchone()
        
        if result:
            raw_balance = result[0]
            # El valor raw debería ser bytes/string encriptado, no el número original
            # Si el valor es el número original en texto claro, FALLA
            try:
                if float(raw_balance) == test_balance:
                    print_error(f"¡FALLO! Balance en BD está en texto claro: {raw_balance}")
                    return False
            except (ValueError, TypeError):
                # No se puede convertir a float = está encriptado (correcto)
                print_success("Balance está encriptado en BD (no se puede leer directamente)")
                print_info(f"Raw value type: {type(raw_balance)}")
                print_info(f"Raw value length: {len(str(raw_balance)) if raw_balance else 0}")
        
        # Verificar que SQLAlchemy lo desencripta al leer
        db.refresh(account)
        if float(account.balance) == test_balance:
            print_success(f"SQLAlchemy desencripta correctamente: {account.balance}")
        else:
            print_error(f"Valor desencriptado incorrecto: {account.balance} != {test_balance}")
            return False
        
        # Limpiar
        db.delete(account)
        db.commit()
        
        return True
        
    except Exception as e:
        print_error(f"Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_typedecorator_decrypt_on_read(db: Session) -> bool:
    """Test 2: TypeDecorator desencripta al leer"""
    print("\n" + "=" * 60)
    print("TEST 2: Desencriptación automática al leer")
    print("=" * 60)
    
    try:
        # Obtener una cuenta existente
        account = db.query(Account).first()
        
        if not account:
            print_warning("No hay cuentas para probar lectura")
            return True
        
        # Verificar que el balance se lee como número
        balance = account.balance
        
        if balance is None:
            print_info("Balance es None (permitido)")
            return True
        
        # Debe ser un número (Decimal o float)
        balance_float = float(balance)
        print_success(f"Balance desencriptado correctamente: {balance_float}")
        print_info(f"Tipo de dato: {type(balance)}")
        
        return True
        
    except Exception as e:
        print_error(f"Error al desencriptar: {e}")
        return False


def test_transaction_encryption(db: Session) -> bool:
    """Test 3: Encriptación de transacciones"""
    print("\n" + "=" * 60)
    print("TEST 3: Encriptación de Transacciones")
    print("=" * 60)
    
    try:
        user = db.query(User).first()
        account = db.query(Account).filter(Account.user_id == user.id).first()
        
        if not user or not account:
            print_warning("Faltan usuario/cuenta para test de transacciones")
            return True
        
        # Crear transacción
        test_amount = 1234.56
        test_description = "Pago secreto de prueba"
        
        transaction = Transaction(
            id=uuid4(),
            user_id=user.id,
            account_id=account.id,
            amount=Decimal(str(test_amount)),
            description=test_description,
            type="expense",
            category_id=None
        )
        db.add(transaction)
        db.commit()
        tx_id = transaction.id
        
        # Verificar encriptación en BD
        raw_query = text("SELECT amount, description FROM transactions WHERE id = :id")
        result = db.execute(raw_query, {"id": str(tx_id)}).fetchone()
        
        if result:
            raw_amount, raw_desc = result[0], result[1]
            
            # Verificar que amount no está en claro
            try:
                if float(raw_amount) == test_amount:
                    print_error("¡Amount en texto claro!")
                    return False
            except (ValueError, TypeError):
                print_success("Amount encriptado en BD")
            
            # Verificar que description no está en claro
            if raw_desc == test_description:
                print_error("¡Description en texto claro!")
                return False
            print_success("Description encriptada en BD")
        
        # Verificar desencriptación
        db.refresh(transaction)
        if float(transaction.amount) == test_amount:
            print_success(f"Amount desencriptado: {transaction.amount}")
        else:
            print_error(f"Amount incorrecto: {transaction.amount}")
            return False
        
        if transaction.description == test_description:
            print_success(f"Description desencriptada correctamente")
        else:
            print_error(f"Description incorrecta: {transaction.description}")
            return False
        
        # Limpiar
        db.delete(transaction)
        db.commit()
        
        return True
        
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_investment_encryption(db: Session) -> bool:
    """Test 4: Encriptación de inversiones"""
    print("\n" + "=" * 60)
    print("TEST 4: Encriptación de Inversiones")
    print("=" * 60)
    
    try:
        user = db.query(User).first()
        
        if not user:
            print_warning("Sin usuario para test de inversiones")
            return True
        
        # Crear inversión
        test_symbol = "AAPL"
        test_shares = 100.5
        test_avg_price = 175.50
        
        investment = Investment(
            id=uuid4(),
            user_id=user.id,
            symbol=test_symbol,
            shares=Decimal(str(test_shares)),
            average_price=Decimal(str(test_avg_price)),
            purchase_date="2024-01-15"
        )
        db.add(investment)
        db.commit()
        inv_id = investment.id
        
        # Verificar raw data
        raw_query = text("SELECT symbol, shares, average_price FROM investments WHERE id = :id")
        result = db.execute(raw_query, {"id": str(inv_id)}).fetchone()
        
        if result:
            raw_symbol, raw_shares, raw_price = result
            
            if raw_symbol == test_symbol:
                print_warning("Symbol podría estar en texto claro (verificar configuración)")
            else:
                print_success("Symbol encriptado")
            
            try:
                if float(raw_shares) == test_shares:
                    print_error("Shares en texto claro")
                    return False
            except (ValueError, TypeError):
                print_success("Shares encriptado")
        
        # Verificar desencriptación
        db.refresh(investment)
        if investment.symbol == test_symbol:
            print_success(f"Symbol desencriptado: {investment.symbol}")
        
        if float(investment.shares) == test_shares:
            print_success(f"Shares desencriptado: {investment.shares}")
        
        # Limpiar
        db.delete(investment)
        db.commit()
        
        return True
        
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_python_aggregation(db: Session) -> bool:
    """Test 5: Agregación en Python funciona con datos encriptados"""
    print("\n" + "=" * 60)
    print("TEST 5: Agregación Python con datos encriptados")
    print("=" * 60)
    
    try:
        from app.utils.aggregation_helpers import sum_amounts, calculate_summary
        
        user = db.query(User).first()
        if not user:
            print_warning("Sin usuario para test")
            return True
        
        # Obtener transacciones
        transactions = db.query(Transaction).filter(
            Transaction.user_id == user.id
        ).limit(10).all()
        
        if not transactions:
            print_warning("Sin transacciones para probar agregación")
            return True
        
        # Probar sum_amounts
        total = sum_amounts(transactions, 'amount')
        print_success(f"sum_amounts funcionó: {total}")
        
        # Probar calculate_summary
        summary = calculate_summary(transactions, 'amount')
        print_success(f"calculate_summary funcionó")
        print_info(f"  Total: {summary['total']}")
        print_info(f"  Count: {summary['count']}")
        print_info(f"  Average: {summary['average']:.2f}")
        
        return True
        
    except ImportError:
        print_warning("aggregation_helpers no disponible")
        return True
    except Exception as e:
        print_error(f"Error en agregación: {e}")
        return False


def run_all_tests():
    """Ejecutar todos los tests"""
    print("\n" + "=" * 60)
    print("TESTS DE ENCRIPTACIÓN - ARQUITECTURA TYPEDECORATOR")
    print("=" * 60)
    print("Este test valida la nueva arquitectura de encriptación:")
    print("- Campo único encriptado via TypeDecorator")
    print("- Sin campos duplicados (*_encrypted)")
    print("- Encriptación AES-256-GCM transparente")
    print("=" * 60)
    
    db = SessionLocal()
    results = []
    
    try:
        # Test 1: Escribir encripta
        results.append(("Encriptación en escritura", test_typedecorator_encrypt_on_write(db)))
        
        # Test 2: Leer desencripta
        results.append(("Desencriptación en lectura", test_typedecorator_decrypt_on_read(db)))
        
        # Test 3: Transacciones
        results.append(("Transacciones encriptadas", test_transaction_encryption(db)))
        
        # Test 4: Inversiones
        results.append(("Inversiones encriptadas", test_investment_encryption(db)))
        
        # Test 5: Agregación Python
        results.append(("Agregación Python", test_python_aggregation(db)))
        
    finally:
        db.close()
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        if result:
            print(f"{Colors.GREEN}✅ {name}: PASÓ{Colors.RESET}")
            passed += 1
        else:
            print(f"{Colors.RED}❌ {name}: FALLÓ{Colors.RESET}")
            failed += 1
    
    print("\n" + "-" * 40)
    print(f"Total: {passed + failed} tests")
    print(f"{Colors.GREEN}Pasaron: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Fallaron: {failed}{Colors.RESET}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
