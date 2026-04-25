#!/usr/bin/env python3
"""
Script de migración: De campos plaintext a TypeDecorators encriptados

Este script migra datos que están actualmente en texto claro
a la nueva arquitectura de encriptación con TypeDecorators.

PREREQUISITOS:
1. Ejecutar migrations/002_add_encrypted_columns.sql PRIMERO
   (Crea las columnas *_encrypted)
2. ENCRYPTION_MASTER_KEY configurada en .env
3. Backup de la base de datos

PROCESO:
1. Este script lee datos plaintext
2. Los escribe en modelos (TypeDecorators encriptan automáticamente)  
3. Los guarda en columnas *_encrypted
4. Después ejecutar migrations/004_encryption_only_fields.sql
   (Elimina plaintext y renombra encrypted → original)

Uso:
    # Ver qué haría sin ejecutar
    python scripts/migrate_to_encrypted_fields.py --dry-run
    
    # Ejecutar migración
    python scripts/migrate_to_encrypted_fields.py
    
    # Con límite de registros
    python scripts/migrate_to_encrypted_fields.py --limit 100

Author: Security Team  
Date: 2026-02-14
"""

import sys
import os
import argparse
from pathlib import Path
from decimal import Decimal

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Cargar .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Variables cargadas desde: {env_path}")
else:
    print(f"⚠️  Archivo .env no encontrado: {env_path}")

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.config import settings


def check_encryption_configured():
    """Verifica que la encriptación está configurada"""
    print("\n🔍 Verificando configuración de encriptación...")
    
    if not settings.ENCRYPTION_MASTER_KEY:
        print("\n❌ ERROR: ENCRYPTION_MASTER_KEY no configurada en .env")
        print("   Genera una clave con:")
        print("   python -c \"import os, base64; print(base64.b64encode(os.urandom(32)).decode())\"")
        return False
    
    try:
        from app.utils.encryption import encrypt_field, decrypt_field
        
        test_value = "test_123"
        encrypted = encrypt_field(test_value)
        decrypted = decrypt_field(encrypted)
        
        if decrypted != test_value:
            print("❌ ERROR: Encriptación/desencriptación no funciona")
            return False
        
        print("✅ Encriptación configurada correctamente\n")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_encrypted_columns_exist(db: Session):
    """Verifica que las columnas *_encrypted existan"""
    print("🔍 Verificando que columnas encriptadas existen...")
    
    checks = [
        ("accounts", "balance_encrypted"),
        ("accounts", "account_number_encrypted"),
        ("transactions", "amount_encrypted"),
        ("transactions", "description_encrypted"),
        ("investments", "symbol_encrypted"),
        ("investments", "shares_encrypted"),
    ]
    
    for table, column in checks:
        query = text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table AND column_name = :column
        """)
        result = db.execute(query, {"table": table, "column": column}).fetchone()
        
        if not result:
            print(f"❌ ERROR: Columna {table}.{column} no existe")
            print(f"   Ejecuta primero: migrations/002_add_encrypted_columns.sql")
            return False
    
    print("✅ Todas las columnas encriptadas existen\n")
    return True


def migrate_accounts(db: Session, dry_run: bool = False, limit: int = None):
    """Migra cuentas de plaintext a encrypted"""
    print("\n📦 Migrando cuentas...")
    
    # Usar SQL raw para leer sin TypeDecorators
    query = text("""
        SELECT id, balance, account_number, notes
        FROM accounts
        WHERE balance_encrypted IS NULL
        ORDER BY created_at
    """)
    
    if limit:
        query = text(str(query) + f" LIMIT {limit}")
    
    results = db.execute(query).fetchall()
    print(f"   Cuentas a migrar: {len(results)}")
    
    if len(results) == 0:
        print("   ✅ No hay cuentas pendientes de migración")
        return 0, 0, 0
    
    processed = 0
    migrated = 0
    errors = 0
    
    from app.utils.encryption import encrypt_field
    
    for row in results:
        processed += 1
        account_id, balance, account_number, notes = row
        
        try:
            if dry_run:
                print(f"   [DRY-RUN] Cuenta {account_id}: balance={balance}")
            else:
                # Encriptar y actualizar directamente
                updates = {}
                
                if balance is not None:
                    updates['balance_encrypted'] = encrypt_field(str(balance))
                
                if account_number:
                    updates['account_number_encrypted'] = encrypt_field(account_number)
                
                if notes:
                    updates['notes_encrypted'] = encrypt_field(notes)
                
                if updates:
                    # Construir UPDATE statement
                    set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                    update_query = text(f"""
                        UPDATE accounts 
                        SET {set_clause}
                        WHERE id = :id
                    """)
                    
                    db.execute(update_query, {**updates, 'id': account_id})
                    migrated += 1
                    
                    if migrated % 100 == 0:
                        db.commit()
                        print(f"   Progreso: {migrated} cuentas migradas...")
                        
        except Exception as e:
            errors += 1
            print(f"   ❌ Error en cuenta {account_id}: {e}")
    
    if not dry_run and migrated > 0:
        db.commit()
    
    return processed, migrated, errors


def migrate_transactions(db: Session, dry_run: bool = False, limit: int = None):
    """Migra transacciones de plaintext a encrypted"""
    print("\n📦 Migrando transacciones...")
    
    query = text("""
        SELECT id, amount, description
        FROM transactions
        WHERE amount_encrypted IS NULL
        ORDER BY created_at
    """)
    
    if limit:
        query = text(str(query) + f" LIMIT {limit}")
    
    results = db.execute(query).fetchall()
    print(f"   Transacciones a migrar: {len(results)}")
    
    if len(results) == 0:
        print("   ✅ No hay transacciones pendientes")
        return 0, 0, 0
    
    processed = 0
    migrated = 0
    errors = 0
    
    from app.utils.encryption import encrypt_field
    
    for row in results:
        processed += 1
        tx_id, amount, description = row
        
        try:
            if dry_run:
                print(f"   [DRY-RUN] TX {tx_id}: amount={amount}")
            else:
                updates = {}
                
                if amount is not None:
                    updates['amount_encrypted'] = encrypt_field(str(amount))
                
                if description:
                    updates['description_encrypted'] = encrypt_field(description)
                
                if updates:
                    set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                    update_query = text(f"""
                        UPDATE transactions 
                        SET {set_clause}
                        WHERE id = :id
                    """)
                    
                    db.execute(update_query, {**updates, 'id': tx_id})
                    migrated += 1
                    
                    if migrated % 100 == 0:
                        db.commit()
                        print(f"   Progreso: {migrated} transacciones migradas...")
                        
        except Exception as e:
            errors += 1
            print(f"   ❌ Error en TX {tx_id}: {e}")
    
    if not dry_run and migrated > 0:
        db.commit()
    
    return processed, migrated, errors


def migrate_investments(db: Session, dry_run: bool = False, limit: int = None):
    """Migra inversiones de plaintext a encrypted"""
    print("\n📦 Migrando inversiones...")
    
    query = text("""
        SELECT id, symbol, company_name, shares, average_price
        FROM investments
        WHERE symbol_encrypted IS NULL
        ORDER BY purchase_date
    """)
    
    if limit:
        query = text(str(query) + f" LIMIT {limit}")
    
    results = db.execute(query).fetchall()
    print(f"   Inversiones a migrar: {len(results)}")
    
    if len(results) == 0:
        print("   ✅ No hay inversiones pendientes")
        return 0, 0, 0
    
    processed = 0
    migrated = 0
    errors = 0
    
    from app.utils.encryption import encrypt_field
    
    for row in results:
        processed += 1
        inv_id, symbol, company_name, shares, avg_price = row
        
        try:
            if dry_run:
                print(f"   [DRY-RUN] Investment {inv_id}: {symbol}")
            else:
                updates = {}
                
                if symbol:
                    updates['symbol_encrypted'] = encrypt_field(symbol)
                
                if company_name:
                    updates['company_name_encrypted'] = encrypt_field(company_name)
                
                if shares is not None:
                    updates['shares_encrypted'] = encrypt_field(str(shares))
                
                if avg_price is not None:
                    updates['average_price_encrypted'] = encrypt_field(str(avg_price))
                
                if updates:
                    set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                    update_query = text(f"""
                        UPDATE investments 
                        SET {set_clause}
                        WHERE id = :id
                    """)
                    
                    db.execute(update_query, {**updates, 'id': inv_id})
                    migrated += 1
                    
                    if migrated % 50 == 0:
                        db.commit()
                        print(f"   Progreso: {migrated} inversiones migradas...")
                        
        except Exception as e:
            errors += 1
            print(f"   ❌ Error en investment {inv_id}: {e}")
    
    if not dry_run and migrated > 0:
        db.commit()
    
    return processed, migrated, errors


def migrate_users(db: Session, dry_run: bool = False, limit: int = None):
    """Migra usuarios (full_name, profile_picture)"""
    print("\n📦 Migrando usuarios...")
    
    query = text("""
        SELECT id, full_name, profile_picture
        FROM users
        WHERE full_name_encrypted IS NULL AND full_name IS NOT NULL
    """)
    
    if limit:
        query = text(str(query) + f" LIMIT {limit}")
    
    results = db.execute(query).fetchall()
    print(f"   Usuarios a migrar: {len(results)}")
    
    if len(results) == 0:
        print("   ✅ No hay usuarios pendientes")
        return 0, 0, 0
    
    processed = 0
    migrated = 0
    errors = 0
    
    from app.utils.encryption import encrypt_field
    
    for row in results:
        processed += 1
        user_id, full_name, profile_picture = row
        
        try:
            if dry_run:
                print(f"   [DRY-RUN] User {user_id}: {full_name}")
            else:
                updates = {}
                
                if full_name:
                    updates['full_name_encrypted'] = encrypt_field(full_name)
                
                if profile_picture:
                    updates['profile_picture_encrypted'] = encrypt_field(profile_picture)
                
                if updates:
                    set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                    update_query = text(f"""
                        UPDATE users 
                        SET {set_clause}
                        WHERE id = :id
                    """)
                    
                    db.execute(update_query, {**updates, 'id': user_id})
                    migrated += 1
                        
        except Exception as e:
            errors += 1
            print(f"   ❌ Error en usuario {user_id}: {e}")
    
    if not dry_run and migrated > 0:
        db.commit()
    
    return processed, migrated, errors


def main():
    parser = argparse.ArgumentParser(
        description='Migrar datos plaintext a campos encriptados'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Simular sin aplicar cambios'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Límite de registros por tabla'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔐 MIGRACIÓN: PLAINTEXT → CAMPOS ENCRIPTADOS")
    print("=" * 70)
    print(f"Modo: {'DRY-RUN (simulación)' if args.dry_run else 'PRODUCCIÓN'}")
    if args.limit:
        print(f"Límite: {args.limit} registros/tabla")
    print("=" * 70)
    
    # Verificaciones
    if not check_encryption_configured():
        sys.exit(1)
    
    db = SessionLocal()
    
    try:
        if not check_encrypted_columns_exist(db):
            print("\n💡 Solución: Ejecuta primero:")
            print("   psql -U usuario -d appfinanzas -f migrations/002_add_encrypted_columns.sql")
            sys.exit(1)
        
        # Confirmar
        if not args.dry_run:
            print("\n⚠️  ADVERTENCIA: Esto modificará la base de datos.")
            print("   Asegúrate de tener un BACKUP.")
            response = input("\n¿Continuar? [y/N]: ")
            if response.lower() != 'y':
                print("❌ Cancelado")
                sys.exit(0)
        
        # Ejecutar migraciones
        users_p, users_m, users_e = migrate_users(db, args.dry_run, args.limit)
        accounts_p, accounts_m, accounts_e = migrate_accounts(db, args.dry_run, args.limit)
        trans_p, trans_m, trans_e = migrate_transactions(db, args.dry_run, args.limit)
        inv_p, inv_m, inv_e = migrate_investments(db, args.dry_run, args.limit)
        
        # Resumen
        print("\n" + "=" * 70)
        print("📊 RESUMEN")
        print("=" * 70)
        
        tables = [
            ("Usuarios", users_p, users_m, users_e),
            ("Cuentas", accounts_p, accounts_m, accounts_e),
            ("Transacciones", trans_p, trans_m, trans_e),
            ("Inversiones", inv_p, inv_m, inv_e),
        ]
        
        for name, processed, migrated, errors in tables:
            print(f"\n{name}:")
            print(f"   Procesados: {processed}")
            print(f"   Migrados:   {migrated}")
            print(f"   Errores:    {errors}")
        
        total_migrated = users_m + accounts_m + trans_m + inv_m
        total_errors = users_e + accounts_e + trans_e + inv_e
        
        if args.dry_run:
            print(f"\n✅ Dry-run completado. {total_migrated} registros serían migrados.")
            print("\n💡 Siguiente paso:")
            print("   python scripts/migrate_to_encrypted_fields.py  (sin --dry-run)")
        else:
            if total_errors > 0:
                print(f"\n⚠️  Completado con {total_errors} errores")
            else:
                print(f"\n✅ ¡Migración exitosa! {total_migrated} registros migrados")
                print("\n💡 Siguiente paso:")
                print("   psql -U usuario -d appfinanzas -f migrations/004_encryption_only_fields.sql")
        
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
