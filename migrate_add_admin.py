"""
Script para agregar la columna is_admin a la tabla users.
Ejecutar solo una vez.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import engine
from sqlalchemy import text

def migrate():
    """Agrega la columna is_admin a la tabla users"""
    
    try:
        with engine.connect() as connection:
            # Verificar si la columna ya existe
            result = connection.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_admin'")
            )
            
            if result.fetchone():
                print("✅ La columna is_admin ya existe")
                return
            
            # Agregar la columna
            connection.execute(
                text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")
            )
            connection.commit()
            print("✅ Columna is_admin agregada exitosamente")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
