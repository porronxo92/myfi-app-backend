"""
Script para crear usuario de prueba con datos completos
Ejecutar desde el directorio backend: python create_test_user.py
"""

import sys
import os

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, datetime, timedelta
from decimal import Decimal
import uuid
import random

from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Importar módulos de la aplicación
from app.database import SessionLocal, engine
from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.budget import Budget
from app.models.budget_item import BudgetItem
from app.models.investment import Investment, InvestmentStatus

# Configuración de hash de contraseña
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================
# DATOS DEL USUARIO DE TEST
# ============================================
TEST_USER = {
    "email": "test@appfinanzas.com",
    "username": "testuser",
    "password": "Test1234!",  # Contraseña a comunicar al usuario
    "full_name": "Usuario Test"
}

# Bancos y sus cuentas
BANKS = [
    {"name": "Cuenta BBVA", "bank_name": "BBVA", "type": "checking", "initial_balance": 10000},
    {"name": "Cuenta Santander", "bank_name": "Santander", "type": "savings", "initial_balance": 10000},
    {"name": "Cuenta ING", "bank_name": "ING Direct", "type": "checking", "initial_balance": 10000},
]

# Stocks a añadir
STOCKS = [
    {"symbol": "AMZN", "company_name": "Amazon.com Inc.", "shares": 5, "avg_price": 185.50},
    {"symbol": "AAPL", "company_name": "Apple Inc.", "shares": 20, "avg_price": 172.30},
    {"symbol": "AVGO", "company_name": "Broadcom Inc.", "shares": 3, "avg_price": 1350.00},
    {"symbol": "NVDA", "company_name": "NVIDIA Corporation", "shares": 10, "avg_price": 875.25},
    {"symbol": "META", "company_name": "Meta Platforms Inc.", "shares": 8, "avg_price": 485.00},
]

def create_test_user(db: Session) -> User:
    """Crear usuario de test"""
    # Verificar si ya existe
    existing = db.query(User).filter(User.email == TEST_USER["email"]).first()
    if existing:
        print(f"⚠️  Usuario ya existe: {TEST_USER['email']}")
        return existing
    
    user = User(
        id=uuid.uuid4(),
        email=TEST_USER["email"],
        username=TEST_USER["username"],
        password_hash=pwd_context.hash(TEST_USER["password"]),
        full_name=TEST_USER["full_name"],
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"✅ Usuario creado: {TEST_USER['email']}")
    return user


def create_default_categories(db: Session, user_id: uuid.UUID) -> dict:
    """Crear categorías por defecto y devolver diccionario con IDs"""
    
    # Verificar si ya tiene categorías
    existing = db.query(Category).filter(Category.user_id == user_id).count()
    if existing > 0:
        print(f"⚠️  Usuario ya tiene {existing} categorías")
        categories = db.query(Category).filter(Category.user_id == user_id).all()
        return {cat.name: {"id": cat.id, "type": cat.type} for cat in categories}
    
    default_categories = [
        # Gastos
        ("Alquiler / Hipoteca",   "expense", "#14B8A6"),
        ("Ocio y entretenimiento","expense", "#8B5CF6"),
        ("Restaurantes",          "expense", "#F97316"),
        ("Ropa y calzado",        "expense", "#EC4899"),
        ("Salud",                 "expense", "#10B981"),
        ("Seguros",               "expense", "#6B7280"),
        ("Suministros del hogar", "expense", "#F59E0B"),
        ("Supermercado",          "expense", "#84CC16"),
        ("Suscripciones",         "expense", "#6366F1"),
        ("Transporte",            "expense", "#06B6D4"),
        ("Viajes",                "expense", "#EF4444"),
        # Ingresos
        ("Intereses",             "income",  "#6EE7B7"),
        ("Salario",               "income",  "#059669"),
    ]
    
    cat_dict = {}
    for name, cat_type, color in default_categories:
        cat_id = uuid.uuid4()
        category = Category(
            id=cat_id,
            name=name,
            type=cat_type,
            color=color,
            user_id=user_id
        )
        db.add(category)
        cat_dict[name] = {"id": cat_id, "type": cat_type}
    
    db.commit()
    print(f"✅ Creadas {len(default_categories)} categorías")
    return cat_dict


def create_accounts(db: Session, user_id: uuid.UUID) -> list:
    """Crear 3 cuentas bancarias"""
    accounts = []
    
    for bank in BANKS:
        # Verificar si ya existe
        existing = db.query(Account).filter(
            Account.user_id == user_id,
            Account.name == bank["name"]
        ).first()
        
        if existing:
            print(f"⚠️  Cuenta ya existe: {bank['name']}")
            accounts.append(existing)
            continue
        
        account = Account(
            id=uuid.uuid4(),
            user_id=user_id,
            name=bank["name"],
            bank_name=bank["bank_name"],
            type=bank["type"],
            currency="EUR",
            balance=Decimal(str(bank["initial_balance"])),
            is_active=True
        )
        db.add(account)
        accounts.append(account)
        print(f"✅ Cuenta creada: {bank['name']} ({bank['bank_name']}) - {bank['initial_balance']}€")
    
    db.commit()
    return accounts


def create_transactions(db: Session, account: Account, categories: dict, num_transactions: int = 45):
    """Crear transacciones para una cuenta"""
    
    # Verificar si ya tiene transacciones
    existing_count = db.query(Transaction).filter(Transaction.account_id == account.id).count()
    if existing_count >= num_transactions:
        print(f"⚠️  La cuenta {account.name} ya tiene {existing_count} transacciones")
        return
    
    expense_categories = [k for k, v in categories.items() if v["type"] == "expense"]
    income_categories = [k for k, v in categories.items() if v["type"] == "income"]
    
    # Descripciones por categoría
    descriptions = {
        "Alquiler / Hipoteca": ["Pago mensual hipoteca", "Cuota hipoteca", "Pago alquiler"],
        "Ocio y entretenimiento": ["Netflix", "Spotify", "Cine", "Concierto", "Teatro", "Videojuegos"],
        "Restaurantes": ["Cena con amigos", "Comida trabajo", "Café", "Desayuno", "Tapas", "Sushi"],
        "Ropa y calzado": ["Zapatillas deportivas", "Camiseta", "Pantalones", "Chaqueta", "Zapatos"],
        "Salud": ["Farmacia", "Dentista", "Médico", "Gimnasio mensual", "Vitaminas"],
        "Seguros": ["Seguro coche", "Seguro hogar", "Seguro vida"],
        "Suministros del hogar": ["Luz", "Gas", "Agua", "Internet", "Teléfono móvil"],
        "Supermercado": ["Compra semanal", "Mercadona", "Carrefour", "Lidl", "Dia"],
        "Suscripciones": ["Amazon Prime", "HBO Max", "Gym", "iCloud", "Microsoft 365"],
        "Transporte": ["Gasolina", "Parking", "Metro/Bus", "Uber", "Peaje autopista"],
        "Viajes": ["Hotel Barcelona", "Vuelo Madrid", "Tren AVE", "Airbnb"],
        "Salario": ["Nómina mensual", "Pago extra", "Bonus trimestral"],
        "Intereses": ["Intereses cuenta ahorro", "Dividendos", "Rendimientos"],
    }
    
    # Rangos de importes por categoría
    amounts = {
        "Alquiler / Hipoteca": (600, 1200),
        "Ocio y entretenimiento": (10, 80),
        "Restaurantes": (15, 60),
        "Ropa y calzado": (20, 150),
        "Salud": (10, 100),
        "Seguros": (30, 200),
        "Suministros del hogar": (40, 120),
        "Supermercado": (30, 120),
        "Suscripciones": (5, 30),
        "Transporte": (20, 80),
        "Viajes": (100, 500),
        "Salario": (2000, 3500),
        "Intereses": (5, 50),
    }
    
    # Generar transacciones para los últimos 3 meses (marzo, abril 2026)
    start_date = date(2026, 3, 1)
    end_date = date(2026, 4, 25)
    
    transactions_created = 0
    balance_change = Decimal("0")
    
    for _ in range(num_transactions):
        # Determinar si es ingreso (20%) o gasto (80%)
        is_income = random.random() < 0.2
        
        if is_income:
            cat_name = random.choice(income_categories)
            trans_type = "income"
        else:
            cat_name = random.choice(expense_categories)
            trans_type = "expense"
        
        cat_id = categories[cat_name]["id"]
        
        # Generar fecha aleatoria en el rango
        days_range = (end_date - start_date).days
        random_date = start_date + timedelta(days=random.randint(0, days_range))
        
        # Generar importe
        min_amt, max_amt = amounts.get(cat_name, (10, 100))
        amount = Decimal(str(round(random.uniform(min_amt, max_amt), 2)))
        
        # Descripción
        desc_list = descriptions.get(cat_name, [cat_name])
        description = random.choice(desc_list)
        
        transaction = Transaction(
            id=uuid.uuid4(),
            account_id=account.id,
            date=random_date,
            category_id=cat_id,
            type=trans_type,
            amount=amount,
            description=description
        )
        db.add(transaction)
        transactions_created += 1
        
        # Actualizar balance tracker
        if trans_type == "income":
            balance_change += amount
        else:
            balance_change -= amount
    
    db.commit()
    
    # Actualizar balance de la cuenta
    new_balance = Decimal("10000") + balance_change
    account.balance = new_balance
    db.commit()
    
    print(f"✅ {transactions_created} transacciones creadas para {account.name} (Balance: {new_balance:.2f}€)")


def create_budgets(db: Session, user_id: uuid.UUID, categories: dict):
    """Crear presupuestos para abril, mayo y junio 2026"""
    
    months = [
        (4, 2026, "Presupuesto Abril 2026"),
        (5, 2026, "Presupuesto Mayo 2026"),
        (6, 2026, "Presupuesto Junio 2026"),
    ]
    
    expense_categories = [(k, v["id"]) for k, v in categories.items() if v["type"] == "expense"]
    
    # Asignaciones por categoría
    allocations = {
        "Alquiler / Hipoteca": Decimal("800"),
        "Ocio y entretenimiento": Decimal("150"),
        "Restaurantes": Decimal("200"),
        "Ropa y calzado": Decimal("100"),
        "Salud": Decimal("80"),
        "Seguros": Decimal("100"),
        "Suministros del hogar": Decimal("200"),
        "Supermercado": Decimal("400"),
        "Suscripciones": Decimal("50"),
        "Transporte": Decimal("150"),
        "Viajes": Decimal("200"),
    }
    
    for month, year, name in months:
        # Verificar si ya existe
        existing = db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.year == year
        ).first()
        
        if existing:
            print(f"⚠️  Presupuesto ya existe: {name}")
            continue
        
        total_budget = sum(allocations.values())
        
        budget = Budget(
            id=uuid.uuid4(),
            user_id=user_id,
            month=month,
            year=year,
            total_budget=total_budget,
            name=name
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
        
        # Crear partidas
        for cat_name, cat_id in expense_categories:
            amount = allocations.get(cat_name, Decimal("50"))
            
            item = BudgetItem(
                id=uuid.uuid4(),
                budget_id=budget.id,
                category_id=cat_id,
                allocated_amount=amount
            )
            db.add(item)
        
        db.commit()
        print(f"✅ Presupuesto creado: {name} ({total_budget}€)")


def create_investments(db: Session, user_id: uuid.UUID):
    """Crear inversiones en acciones"""
    
    for stock in STOCKS:
        # Verificar si ya existe
        existing = db.query(Investment).filter(
            Investment.user_id == user_id,
            Investment.symbol == stock["symbol"],
            Investment.status == InvestmentStatus.ACTIVE
        ).first()
        
        if existing:
            print(f"⚠️  Inversión ya existe: {stock['symbol']}")
            continue
        
        # Fecha de compra aleatoria en los últimos 6 meses
        purchase_date = date(2026, random.randint(1, 4), random.randint(1, 28))
        
        investment = Investment(
            id=uuid.uuid4(),
            user_id=user_id,
            symbol=stock["symbol"],
            company_name=stock["company_name"],
            shares=Decimal(str(stock["shares"])),
            average_price=Decimal(str(stock["avg_price"])),
            purchase_date=purchase_date,
            status=InvestmentStatus.ACTIVE
        )
        db.add(investment)
        
        total_value = stock["shares"] * stock["avg_price"]
        print(f"✅ Inversión creada: {stock['shares']} x {stock['symbol']} @ ${stock['avg_price']} = ${total_value:,.2f}")
    
    db.commit()


def main():
    """Ejecutar creación de datos de prueba"""
    print("\n" + "="*60)
    print("🚀 CREACIÓN DE USUARIO DE PRUEBA")
    print("="*60 + "\n")
    
    db = SessionLocal()
    
    try:
        # 1. Crear usuario
        print("\n📌 Paso 1: Creando usuario...")
        user = create_test_user(db)
        
        # 2. Crear categorías
        print("\n📌 Paso 2: Creando categorías...")
        categories = create_default_categories(db, user.id)
        
        # 3. Crear cuentas bancarias
        print("\n📌 Paso 3: Creando cuentas bancarias...")
        accounts = create_accounts(db, user.id)
        
        # 4. Crear transacciones
        print("\n📌 Paso 4: Creando transacciones...")
        for account in accounts:
            create_transactions(db, account, categories, num_transactions=45)
        
        # 5. Crear presupuestos
        print("\n📌 Paso 5: Creando presupuestos...")
        create_budgets(db, user.id, categories)
        
        # 6. Crear inversiones
        print("\n📌 Paso 6: Creando inversiones...")
        create_investments(db, user.id)
        
        print("\n" + "="*60)
        print("✅ DATOS DE PRUEBA CREADOS CORRECTAMENTE")
        print("="*60)
        print(f"\n🔐 CREDENCIALES DE ACCESO:")
        print(f"   Email:    {TEST_USER['email']}")
        print(f"   Password: {TEST_USER['password']}")
        print(f"   Username: {TEST_USER['username']}")
        print("\n" + "="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
