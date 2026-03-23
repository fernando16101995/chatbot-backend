from app.core.database import SessionLocal
from app.models.assessment import PHQ9ConversationalAssessment
from app.models.user import User

db = SessionLocal()

# Buscar usuario
email = 'jf.chavez20@info.uas.edu.mx'
user = db.query(User).filter(User.email == email).first()

if user:
    print(f"👤 Usuario: {user.email} (ID: {user.id})\n")
    
    # Buscar todas las evaluaciones PHQ-9
    assessments = db.query(PHQ9ConversationalAssessment).filter(
        PHQ9ConversationalAssessment.user_id == user.id
    ).all()
    
    if assessments:
        print(f"📊 Evaluaciones encontradas: {len(assessments)}\n")
        
        for i, assessment in enumerate(assessments, 1):
            print(f"{'='*60}")
            print(f"Evaluación #{i} (ID: {assessment.id})")
            print(f"{'='*60}")
            print(f"Estado: {'✅ Activa' if assessment.is_active else '❌ Inactiva'}")
            print(f"Pregunta actual: {assessment.current_question}/9")
            print(f"Esperando respuesta: {'Sí' if assessment.waiting_for_response else 'No'}")
            print(f"Mensajes desde última pregunta: {assessment.messages_since_last_question}")
            print(f"Iniciada: {assessment.started_at}")
            if assessment.completed_at:
                print(f"Completada: {assessment.completed_at}")
            print(f"\n📝 Respuestas guardadas:")
            
            for q in range(1, 10):
                response = getattr(assessment, f"q{q}_response")
                score = getattr(assessment, f"q{q}_score")
                if response:
                    print(f"  Q{q}: {response[:80]}..." if len(response) > 80 else f"  Q{q}: {response}")
                    print(f"       Score: {score}")
                else:
                    print(f"  Q{q}: [Sin respuesta]")
            
            if assessment.total_score is not None and assessment.total_score > 0:
                print(f"\n🎯 Score Total: {assessment.total_score}/27")
                print(f"📈 Severidad: {assessment.severity}")
            
            print()
    else:
        print("❌ No se encontraron evaluaciones PHQ-9 para este usuario")
else:
    print(f"❌ Usuario {email} no encontrado")

db.close()
