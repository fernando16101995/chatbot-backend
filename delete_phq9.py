from app.core.database import SessionLocal
from app.models.assessment import PHQ9ConversationalAssessment
from app.models.user import User

db = SessionLocal()

# Buscar usuario
user = db.query(User).filter(User.email == 'jf.chavez20@info.uas.edu.mx').first()

if user:
    print(f"Usuario encontrado: {user.email} (ID: {user.id})")
    
    # Eliminar evaluación actual (que está mal registrada)
    assessment = db.query(PHQ9ConversationalAssessment).filter(
        PHQ9ConversationalAssessment.user_id == user.id
    ).first()
    
    if assessment:
        print(f"\n🗑️  Eliminando evaluación ID {assessment.id}")
        print(f"   - Estado: {'Activa' if assessment.is_active else 'Inactiva'}")
        print(f"   - Pregunta actual: {assessment.current_question}")
        print(f"   - Iniciada: {assessment.started_at}")
        
        db.delete(assessment)
        db.commit()
        print("✅ Evaluación eliminada correctamente")
    else:
        print("No se encontró ninguna evaluación")
else:
    print("Usuario no encontrado")

db.close()
