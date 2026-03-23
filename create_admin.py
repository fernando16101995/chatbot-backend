"""
Script para crear un usuario administrador.
Uso: python create_admin.py admin@chatbot.com password123
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.core.security import hash_password

def create_admin(email: str, password: str):
    """Crea un usuario administrador"""
    
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Verificar si el usuario ya existe
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"❌ El usuario {email} ya existe")
            return
        
        # Crear nuevo admin
        admin_user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Admin creado exitosamente")
        print(f"   Email: {email}")
        print(f"   ID: {admin_user.id}")
        print(f"   Status: {'Activo' if admin_user.is_active else 'Inactivo'}")
        print(f"   Rol: {'Admin' if admin_user.is_admin else 'User'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python create_admin.py <email> <password>")
        print("Ejemplo: python create_admin.py admin@chatbot.com miPassword123")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    create_admin(email, password)
