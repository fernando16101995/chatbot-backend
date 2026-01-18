from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.dependencies import get_current_user
from app.core.database import SessionLocal
from app.models.user import User
from app.models.assessment import (
    PHQ9Assessment, 
    DepressionDetection, 
    MentalHealthSummary,
    PHQ9ConversationalAssessment
)
from app.api.assessment.schemas import PHQ9ResultSchema, DepressionDetectionSchema, MentalHealthSummarySchema

router = APIRouter(prefix="/assessment", tags=["Mental Health Assessment"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/summary", response_model=MentalHealthSummarySchema)
def get_mental_health_summary(
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el resumen general de salud mental del usuario.
    Incluye últimas evaluaciones PHQ-9, detecciones y nivel de riesgo.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    
    summary = db.query(MentalHealthSummary).filter(
        MentalHealthSummary.user_id == user.id
    ).first()
    
    if not summary:
        # Crear resumen vacío si no existe
        summary = MentalHealthSummary(
            user_id=user.id,
            total_phq9_assessments=0,
            depression_detection_count=0,
            high_risk_detections=0,
            overall_risk_level="minimal",
            requires_attention=False
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)
    
    return summary


@router.get("/phq9/history", response_model=List[PHQ9ResultSchema])
def get_phq9_history(
    limit: int = 10,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de evaluaciones PHQ-9 del usuario.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    assessments = db.query(PHQ9Assessment).filter(
        PHQ9Assessment.user_id == user.id
    ).order_by(PHQ9Assessment.created_at.desc()).limit(limit).all()
    
    return assessments


@router.get("/phq9/latest", response_model=PHQ9ResultSchema)
def get_latest_phq9(
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene la última evaluación PHQ-9 del usuario.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    
    assessment = db.query(PHQ9Assessment).filter(
        PHQ9Assessment.user_id == user.id
    ).order_by(PHQ9Assessment.created_at.desc()).first()
    
    if not assessment:
        return {"error": "No hay evaluaciones PHQ-9"}
    
    return assessment


@router.get("/detections", response_model=List[DepressionDetectionSchema])
def get_depression_detections(
    limit: int = 20,
    only_positive: bool = False,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de detecciones de lenguaje depresivo.
    Si only_positive=true, solo muestra las detecciones positivas.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    query = db.query(DepressionDetection).filter(
        DepressionDetection.user_id == user.id
    )
    
    if only_positive:
        query = query.filter(DepressionDetection.is_depressive == True)
    
    detections = query.order_by(
        DepressionDetection.detected_at.desc()
    ).limit(limit).all()
    
    return detections


@router.get("/risk-alert")
def check_risk_alert(
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifica si el usuario requiere atención basado en sus evaluaciones.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    
    summary = db.query(MentalHealthSummary).filter(
        MentalHealthSummary.user_id == user.id
    ).first()
    
    if not summary:
        return {
            "requires_attention": False,
            "risk_level": "unknown",
            "message": "No hay datos suficientes"
        }
    
    return {
        "requires_attention": summary.requires_attention,
        "risk_level": summary.overall_risk_level,
        "phq9_score": summary.latest_phq9_score,
        "high_risk_detections": summary.high_risk_detections,
        "message": get_risk_message(summary)
    }


def get_risk_message(summary: MentalHealthSummary) -> str:
    """Genera mensaje según el nivel de riesgo"""
    if summary.overall_risk_level == "critical":
        return "Se han detectado múltiples señales de riesgo alto. Se recomienda buscar ayuda profesional inmediatamente."
    elif summary.overall_risk_level == "severe":
        return "Se han detectado síntomas severos. Es importante hablar con un profesional de salud mental."
    elif summary.overall_risk_level == "moderate":
        return "Se han detectado síntomas moderados. Considera buscar apoyo profesional."
    else:
        return "No se han detectado señales de riesgo significativas."


@router.get("/phq9/conversational/status")
def get_conversational_phq9_status(
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el estado de la evaluación PHQ-9 conversacional en progreso.
    Indica en qué pregunta va y cuántas ha completado.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    
    assessment = db.query(PHQ9ConversationalAssessment).filter(
        PHQ9ConversationalAssessment.user_id == user.id,
        PHQ9ConversationalAssessment.is_active == True
    ).first()
    
    if not assessment:
        return {
            "has_active_assessment": False,
            "message": "No hay evaluación en progreso"
        }
    
    completed_questions = assessment.current_question - 1
    total_questions = 9
    progress_percentage = (completed_questions / total_questions) * 100
    
    return {
        "has_active_assessment": True,
        "current_question": assessment.current_question,
        "completed_questions": completed_questions,
        "total_questions": total_questions,
        "progress_percentage": round(progress_percentage, 1),
        "messages_since_last_question": assessment.messages_since_last_question,
        "started_at": assessment.started_at
    }


@router.get("/phq9/conversational/history")
def get_conversational_phq9_history(
    limit: int = 10,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de evaluaciones PHQ-9 conversacionales completadas.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    assessments = db.query(PHQ9ConversationalAssessment).filter(
        PHQ9ConversationalAssessment.user_id == user.id,
        PHQ9ConversationalAssessment.is_active == False
    ).order_by(PHQ9ConversationalAssessment.completed_at.desc()).limit(limit).all()
    
    return [
        {
            "id": a.id,
            "total_score": a.total_score,
            "severity": a.severity,
            "started_at": a.started_at,
            "completed_at": a.completed_at,
            "responses": {
                f"q{i}": {
                    "response": getattr(a, f"q{i}_response"),
                    "score": getattr(a, f"q{i}_score")
                }
                for i in range(1, 10)
            }
        }
        for a in assessments
    ]


@router.delete("/phq9/conversational/cancel")
def cancel_conversational_phq9(
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancela la evaluación PHQ-9 conversacional en progreso.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    
    assessment = db.query(PHQ9ConversationalAssessment).filter(
        PHQ9ConversationalAssessment.user_id == user.id,
        PHQ9ConversationalAssessment.is_active == True
    ).first()
    
    if not assessment:
        return {"message": "No hay evaluación activa para cancelar"}
    
    assessment.is_active = False
    db.commit()
    
    return {"message": "Evaluación PHQ-9 cancelada exitosamente"}
