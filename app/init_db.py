"""
Script para crear todas las tablas en la base de datos.
Ejecutar: python -m app.init_db
"""
from app.core.database import Base, engine
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.models.assessment import (
    PHQ9Assessment, 
    DepressionDetection, 
    MentalHealthSummary,
    PHQ9ConversationalAssessment
)

def init_db():
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tablas creadas exitosamente")
    print("\nTablas disponibles:")
    print("  - users")
    print("  - chat_messages")
    print("  - phq9_assessments")
    print("  - depression_detections")
    print("  - mental_health_summary")
    print("  - phq9_conversational_assessments")

if __name__ == "__main__":
    init_db()
