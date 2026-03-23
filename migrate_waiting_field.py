"""
Script para agregar el campo waiting_for_response a la tabla phq9_conversational_assessments
"""
from sqlalchemy import text
from app.core.database import engine

def migrate():
    with engine.connect() as conn:
        # Agregar columna waiting_for_response si no existe
        try:
            conn.execute(text("""
                ALTER TABLE phq9_conversational_assessments 
                ADD COLUMN waiting_for_response BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("✅ Campo 'waiting_for_response' agregado correctamente")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("⚠️  El campo 'waiting_for_response' ya existe")
            else:
                print(f"❌ Error: {e}")
                raise

if __name__ == "__main__":
    migrate()
