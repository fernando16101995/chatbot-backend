from app.core.database import SessionLocal
from app.models.assessment import PHQ9ConversationalAssessment
from app.models.user import User

db = SessionLocal()

# Buscar usuario
user = db.query(User).filter(User.email == 'jf.chavez20@info.uas.edu.mx').first()

if user:
    print(f"Usuario encontrado: {user.email} (ID: {user.id})")
    
    # Eliminar evaluaciones activas (están corruptas)
    assessments = db.query(PHQ9ConversationalAssessment).filter(
        PHQ9ConversationalAssessment.user_id == user.id
    ).all()
    
    for assessment in assessments:
        print(f"\n🗑️  Eliminando evaluación ID {assessment.id}")
        print(f"   - Estado: {'Activa' if assessment.is_active else 'Inactiva'}")
        print(f"   - Pregunta actual: {assessment.current_question}")
        print(f"   - Respuestas guardadas: {sum([1 for i in range(1,10) if getattr(assessment, f'q{i}_response')])}")
        
        db.delete(assessment)
    
    db.commit()
    print("\n✅ Todas las evaluaciones eliminadas correctamente")
    print("🔄 El sistema iniciará una nueva evaluación cuando detecte lenguaje depresivo")
else:
    print("Usuario no encontrado")

db.close()
