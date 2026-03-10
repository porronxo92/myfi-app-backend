#!/usr/bin/env python3
"""
Script de migración: Encriptar datos sensibles existentes

Este script migra los datos existentes en las tablas users, accounts, 
transactions e investments a sus respectivos campos encriptados.

IMPORTANTE:
1. Ejecutar primero: migrations/002_add_encrypted_columns.sql
2. Asegurarse de que ENCRYPTION_MASTER_KEY está configurada en .env
3. Hacer backup de la base de datos antes de ejecutar

Uso:
    python scripts/migrate_encrypt_data.py
    
    # Modo dry-run (solo muestra lo que haría)
    python scripts/migrate_encrypt_data.py --dry-run
    
    # Con límite de registros
    python scripts/migrate_encrypt_data.py --limit 100

Author: Security Team
Date: 2026-02-11 (Updated)
"""

import sys
import os
import argparse
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================
# CARGAR VARIABLES DE ENTORNO DESDE .env
# ============================================
from dotenv import load_dotenv

# Cargar .env explícitamente
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Variables de entorno cargadas desde: {env_path}")
else:
    print(f"⚠️  Archivo .env no encontrado en: {env_path}")
    print("   El script intentará usar variables de entorno del sistema")

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.investment import Investment
from app.config import settings


def check_encryption_configured():
    """Verifica que la encriptación está configurada correctamente"""
    print("\n🔍 Verificando configuración de encriptación...")
    
    # Debug: mostrar valor de la variable (parcialmente)
    env_key = os.getenv("ENCRYPTION_MASTER_KEY")
    settings_key = settings.ENCRYPTION_MASTER_KEY
    
    print(f"   ENCRYPTION_MASTER_KEY desde os.getenv(): {'✅ Configurada' if env_key else '❌ No encontrada'}")
    print(f"   ENCRYPTION_MASTER_KEY desde settings:   {'✅ Configurada' if settings_key else '❌ No encontrada'}")
    
    if settings_key:
        print(f"   Longitud de la clave: {len(settings_key)} caracteres")
    
    if not settings.ENCRYPTION_MASTER_KEY:
        print("\n❌ ERROR: ENCRYPTION_MASTER_KEY no está configurada en .env")
        print("   Por favor, genera una clave con:")
        print("   python -c \"import os, base64; print(base64.b64encode(os.urandom(32)).decode())\"")
        print("\n   Y agrégala a tu archivo .env:")
        print("   ENCRYPTION_MASTER_KEY=<clave_generada>")
        return False
    
    # Verificar que las funciones de encriptación funcionan
    try:
        from app.utils.encryption import encrypt_field, decrypt_field
        
        test_value = "test_encryption_data"
        encrypted = encrypt_field(test_value)
        decrypted = decrypt_field(encrypted)
        
        if decrypted != test_value:
            print("❌ ERROR: La encriptación/desencriptación no funciona correctamente")
            return False
        
        print("✅ Encriptación configurada y funcionando correctamente\n")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Fallo al verificar encriptación: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_users(db: Session, dry_run: bool = False, limit: int = None):
    """
    Migra los datos sensibles de usuarios a campos encriptados
    
    Args:
        db: Sesión de base de datos
        dry_run: Si True, solo muestra lo que haría sin ejecutar
        limit: Número máximo de registros a procesar
    
    Returns:
        tuple: (procesados, migrados, errores)
    """
    print("\n📦 Migrando usuarios...")
    
    query = db.query(User).filter(
        (User.full_name.isnot(None)) | 
        (User.profile_picture.isnot(None))
    )
    
    if limit:
        query = query.limit(limit)
    
    users = query.all()
    print(f"   Usuarios a procesar: {len(users)}")
    
    processed = 0
    migrated = 0
    errors = 0
    
    for user in users:
        processed += 1
        try:
            needs_migration = False
            
            # Verificar full_name
            if user.full_name and not user.full_name_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Usuario {user.id}: migraría full_name")
                else:
                    user.full_name_encrypted = user.full_name
                    user.full_name = None
                needs_migration = True
            
            # Verificar profile_picture
            if user.profile_picture and not user.profile_picture_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Usuario {user.id}: migraría profile_picture")
                else:
                    user.profile_picture_encrypted = user.profile_picture
                    user.profile_picture = None
                needs_migration = True
            
            if needs_migration:
                migrated += 1
                
                if not dry_run:
                    # Commit cada 100 registros
                    if migrated % 100 == 0:
                        db.commit()
                        print(f"   Progreso: {migrated} usuarios migrados...")
                        
        except Exception as e:
            errors += 1
            print(f"   ❌ Error migrando usuario {user.id}: {e}")
    
    if not dry_run and migrated > 0:
        db.commit()
    
    return processed, migrated, errors


def migrate_accounts(db: Session, dry_run: bool = False, limit: int = None):
    """
    Migra los datos sensibles de cuentas a campos encriptados
    
    Args:
        db: Sesión de base de datos
        dry_run: Si True, solo muestra lo que haría sin ejecutar
        limit: Número máximo de registros a procesar
    
    Returns:
        tuple: (procesados, migrados, errores)
    """
    print("\n📦 Migrando cuentas...")
    
    query = db.query(Account).filter(
        (Account.account_number.isnot(None)) | 
        (Account.notes.isnot(None))
    )
    
    if limit:
        query = query.limit(limit)
    
    accounts = query.all()
    print(f"   Cuentas a procesar: {len(accounts)}")
    
    processed = 0
    migrated = 0
    errors = 0
    
    for account in accounts:
        processed += 1
        try:
            needs_migration = False
            
            # Verificar account_number
            if account.account_number and not account.account_number_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Cuenta {account.id}: migraría account_number")
                else:
                    account.account_number_encrypted = account.account_number
                    account.account_number = None
                needs_migration = True
            
            # Verificar notes
            if account.notes and not account.notes_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Cuenta {account.id}: migraría notes")
                else:
                    account.notes_encrypted = account.notes
                    account.notes = None
                needs_migration = True
            
            # Verificar balance
            if account.balance is not None and not account.balance_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Cuenta {account.id}: migraría balance")
                else:
                    account.balance_encrypted = str(account.balance)
                    # NO borramos balance original porque se usa en cálculos
                needs_migration = True
            
            if needs_migration:
                migrated += 1
                
                if not dry_run:
                    if migrated % 100 == 0:
                        db.commit()
                        print(f"   Progreso: {migrated} cuentas migradas...")
                        
        except Exception as e:
            errors += 1
            print(f"   ❌ Error migrando cuenta {account.id}: {e}")
    
    if not dry_run and migrated > 0:
        db.commit()
    
    return processed, migrated, errors


def migrate_transactions(db: Session, dry_run: bool = False, limit: int = None):
    """
    Migra los datos sensibles de transacciones a campos encriptados
    
    Args:
        db: Sesión de base de datos
        dry_run: Si True, solo muestra lo que haría sin ejecutar
        limit: Número máximo de registros a procesar
    
    Returns:
        tuple: (procesados, migrados, errores)
    """
    print("\n📦 Migrando transacciones...")
    
    query = db.query(Transaction).filter(
        (Transaction.amount.isnot(None)) | 
        (Transaction.description.isnot(None))
    )
    
    if limit:
        query = query.limit(limit)
    
    transactions = query.all()
    print(f"   Transacciones a procesar: {len(transactions)}")
    
    processed = 0
    migrated = 0
    errors = 0
    
    for transaction in transactions:
        processed += 1
        try:
            needs_migration = False
            
            # Verificar amount
            if transaction.amount is not None and not transaction.amount_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Transacción {transaction.id}: migraría amount")
                else:
                    transaction.amount_encrypted = str(transaction.amount)
                    # NO borramos amount original porque se usa en cálculos
                needs_migration = True
            
            # Verificar description
            if transaction.description and not transaction.description_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Transacción {transaction.id}: migraría description")
                else:
                    transaction.description_encrypted = transaction.description
                    # NO borramos description porque puede usarse en búsquedas
                needs_migration = True
            
            if needs_migration:
                migrated += 1
                
                if not dry_run:
                    if migrated % 100 == 0:
                        db.commit()
                        print(f"   Progreso: {migrated} transacciones migradas...")
                        
        except Exception as e:
            errors += 1
            print(f"   ❌ Error migrando transacción {transaction.id}: {e}")
    
    if not dry_run and migrated > 0:
        db.commit()
    
    return processed, migrated, errors


def migrate_investments(db: Session, dry_run: bool = False, limit: int = None):
    """
    Migra los datos sensibles de inversiones a campos encriptados
    
    Args:
        db: Sesión de base de datos
        dry_run: Si True, solo muestra lo que haría sin ejecutar
        limit: Número máximo de registros a procesar
    
    Returns:
        tuple: (procesados, migrados, errores)
    """
    print("\n📦 Migrando inversiones...")
    
    query = db.query(Investment)
    
    if limit:
        query = query.limit(limit)
    
    investments = query.all()
    print(f"   Inversiones a procesar: {len(investments)}")
    
    processed = 0
    migrated = 0
    errors = 0
    
    for investment in investments:
        processed += 1
        try:
            needs_migration = False
            
            # Verificar symbol
            if investment.symbol and not investment.symbol_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Inversión {investment.id}: migraría symbol")
                else:
                    investment.symbol_encrypted = investment.symbol
                    # NO borramos symbol porque se usa en búsquedas/cotizaciones
                needs_migration = True
            
            # Verificar company_name
            if investment.company_name and not investment.company_name_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Inversión {investment.id}: migraría company_name")
                else:
                    investment.company_name_encrypted = investment.company_name
                needs_migration = True
            
            # Verificar shares
            if investment.shares is not None and not investment.shares_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Inversión {investment.id}: migraría shares")
                else:
                    investment.shares_encrypted = str(investment.shares)
                needs_migration = True
            
            # Verificar average_price
            if investment.average_price is not None and not investment.average_price_encrypted:
                if dry_run:
                    print(f"   [DRY-RUN] Inversión {investment.id}: migraría average_price")
                else:
                    investment.average_price_encrypted = str(investment.average_price)
                needs_migration = True
            
            if needs_migration:
                migrated += 1
                
                if not dry_run:
                    if migrated % 100 == 0:
                        db.commit()
                        print(f"   Progreso: {migrated} inversiones migradas...")
                        
        except Exception as e:
            errors += 1
            print(f"   ❌ Error migrando inversión {investment.id}: {e}")
    
    if not dry_run and migrated > 0:
        db.commit()
    
    return processed, migrated, errors


def main():
    parser = argparse.ArgumentParser(
        description='Migrar datos existentes a campos encriptados'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Simular la migración sin aplicar cambios'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Número máximo de registros a procesar por tabla'
    )
    parser.add_argument(
        '--skip-check',
        action='store_true',
        help='Saltar verificación de encriptación (no recomendado)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔐 MIGRACIÓN DE DATOS A CAMPOS ENCRIPTADOS")
    print("=" * 60)
    print(f"Entorno: {settings.ENVIRONMENT}")
    print(f"Modo: {'DRY-RUN (simulación)' if args.dry_run else 'PRODUCCIÓN'}")
    if args.limit:
        print(f"Límite: {args.limit} registros por tabla")
    print("=" * 60)
    
    # Verificar encriptación
    if not args.skip_check:
        if not check_encryption_configured():
            sys.exit(1)
    
    # Confirmar si no es dry-run
    if not args.dry_run:
        print("\n⚠️  ADVERTENCIA: Este script modificará la base de datos.")
        print("   Asegúrate de tener un backup antes de continuar.")
        response = input("\n¿Continuar? [y/N]: ")
        if response.lower() != 'y':
            print("Migración cancelada.")
            sys.exit(0)
    
    # Ejecutar migración
    db = SessionLocal()
    try:
        # Migrar usuarios
        users_processed, users_migrated, users_errors = migrate_users(
            db, 
            dry_run=args.dry_run, 
            limit=args.limit
        )
        
        # Migrar cuentas
        accounts_processed, accounts_migrated, accounts_errors = migrate_accounts(
            db, 
            dry_run=args.dry_run, 
            limit=args.limit
        )
        
        # Migrar transacciones
        trans_processed, trans_migrated, trans_errors = migrate_transactions(
            db, 
            dry_run=args.dry_run, 
            limit=args.limit
        )
        
        # Migrar inversiones
        inv_processed, inv_migrated, inv_errors = migrate_investments(
            db, 
            dry_run=args.dry_run, 
            limit=args.limit
        )
        
        # Resumen
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE MIGRACIÓN")
        print("=" * 60)
        print(f"\nUsuarios:")
        print(f"   Procesados: {users_processed}")
        print(f"   Migrados:   {users_migrated}")
        print(f"   Errores:    {users_errors}")
        
        print(f"\nCuentas:")
        print(f"   Procesados: {accounts_processed}")
        print(f"   Migrados:   {accounts_migrated}")
        print(f"   Errores:    {accounts_errors}")
        
        print(f"\nTransacciones:")
        print(f"   Procesados: {trans_processed}")
        print(f"   Migrados:   {trans_migrated}")
        print(f"   Errores:    {trans_errors}")
        
        print(f"\nInversiones:")
        print(f"   Procesados: {inv_processed}")
        print(f"   Migrados:   {inv_migrated}")
        print(f"   Errores:    {inv_errors}")
        
        total_errors = users_errors + accounts_errors + trans_errors + inv_errors
        total_migrated = users_migrated + accounts_migrated + trans_migrated + inv_migrated
        
        if total_errors > 0:
            print(f"\n⚠️  Se encontraron {total_errors} errores durante la migración.")
        else:
            if args.dry_run:
                print(f"\n✅ Dry-run completado. {total_migrated} registros serían migrados.")
            else:
                print(f"\n✅ Migración completada exitosamente. {total_migrated} registros migrados.")
        
    except Exception as e:
        print(f"\n❌ Error fatal durante la migración: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
