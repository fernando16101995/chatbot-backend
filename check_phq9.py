from app.core.database import SessionLocal
from app.models.assessment import PHQ9ConversationalAssessment, DepressionDetection
from app.models.user import User

db = SessionLocal()

# Buscar usuario
user = db.query(User).filter(User.email == 'jf.chavez20@info.uas.edu.mx').first()
print(f"Usuario encontrado: {user.email if user else 'No encontrado'}")
print(f"User ID: {user.id if user else 'N/A'}")

if user:
    # Ver evaluaciones PHQ-9
    assessments = db.query(PHQ9ConversationalAssessment).filter(
        PHQ9ConversationalAssessment.user_id == user.id
    ).all()
    
    print(f"\n📊 Total evaluaciones PHQ-9: {len(assessments)}")
    for a in assessments:
        print(f"  - ID: {a.id}, Activa: {a.is_active}, Pregunta actual: {a.current_question}, Iniciada: {a.started_at}")
    
    # Ver detecciones depresivas
    detections = db.query(DepressionDetection).filter(
        DepressionDetection.user_id == user.id,
        DepressionDetection.is_depressive == True
    ).count()
    
    print(f"\n🔍 Total detecciones depresivas: {detections}")

db.close()
