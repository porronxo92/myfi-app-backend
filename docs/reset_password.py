"""
Script para resetear contraseña de usuarios
Uso: python reset_password.py
"""
from app.database import SessionLocal
from app.models.user import User
from app.services.user_service import UserService
import sys

def list_users(db):
    """Lista todos los usuarios del sistema"""
    users = db.query(User).all()
    print("\n" + "="*60)
    print("USUARIOS EN EL SISTEMA:")
    print("="*60)
    for i, user in enumerate(users, 1):
        status = "✓ Activo" if user.is_active else "✗ Inactivo"
        admin = " [ADMIN]" if user.is_admin else ""
        print(f"{i}. {user.email}{admin} - {status}")
    print("="*60)
    return users

def reset_password(db, email, new_password):
    """Resetea la contraseña de un usuario"""
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        print(f"❌ Usuario con email '{email}' no encontrado")
        return False
    
    # Hashear nueva contraseña
    hashed_password = UserService._hash_password(new_password)
    user.password_hash = hashed_password
    db.commit()
    
    print(f"\n✅ Contraseña actualizada correctamente")
    print(f"📧 Email: {email}")
    print(f"🔑 Nueva contraseña: {new_password}")
    print(f"\n🧪 Prueba con curl:")
    print(f"""
curl -X POST http://localhost:8000/api/users/login \\
  -H 'Content-Type: application/json' \\
  -d '{{
    "email": "{email}",
    "password": "{new_password}"
  }}'
""")
    return True

def main():
    db = SessionLocal()
    
    try:
        # Listar usuarios
        users = list_users(db)
        
        if not users:
            print("⚠️  No hay usuarios en la base de datos")
            return
        
        # Solicitar email
        print("\nIngresa el email del usuario (o presiona Enter para salir):")
        email = input("📧 Email: ").strip()
        
        if not email:
            print("Cancelado.")
            return
        
        # Solicitar nueva contraseña
        print("\nIngresa la nueva contraseña:")
        new_password = input("🔑 Nueva contraseña: ").strip()
        
        if not new_password:
            print("❌ La contraseña no puede estar vacía")
            return
        
        # Confirmar
        print(f"\n⚠️  ¿Resetear contraseña de '{email}'? (s/n):")
        confirm = input("Confirmar: ").strip().lower()
        
        if confirm in ['s', 'si', 'sí', 'y', 'yes']:
            reset_password(db, email, new_password)
        else:
            print("Cancelado.")
    
    except KeyboardInterrupt:
        print("\n\nCancelado por el usuario.")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
