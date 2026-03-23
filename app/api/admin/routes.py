from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.core.dependencies import get_current_admin, get_db
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.models.assessment import (
    PHQ9Assessment,
    DepressionDetection,
    MentalHealthSummary,
    PHQ9ConversationalAssessment
)

router = APIRouter(prefix="/admin", tags=["Dashboard Admin"])


@router.get("/dashboard/metrics")
def get_dashboard_metrics(
    admin_email: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Obtiene todas las métricas generales del dashboard.
    Solo accesible para administradores.
    """
    
    # Estadísticas de usuarios
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    admins_count = db.query(func.count(User.id)).filter(User.is_admin == True).scalar() or 0
    
    # Usuarios creados en los últimos 7 días
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = db.query(func.count(User.id)).filter(
        User.created_at >= week_ago
    ).scalar() or 0
    
    # Estadísticas de mensajes
    total_messages = db.query(func.count(ChatMessage.id)).scalar() or 0
    messages_week = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.created_at >= week_ago
    ).scalar() or 0
    
    # Estadísticas de evaluaciones PHQ-9
    total_phq9_assessments = db.query(func.count(PHQ9Assessment.id)).scalar() or 0
    assessments_week = db.query(func.count(PHQ9Assessment.id)).filter(
        PHQ9Assessment.created_at >= week_ago
    ).scalar() or 0
    
    # Severidad de evaluaciones PHQ-9
    severity_distribution = db.query(
        PHQ9Assessment.severity,
        func.count(PHQ9Assessment.id)
    ).group_by(PHQ9Assessment.severity).all()
    
    severity_counts = {
        "minimal": 0,
        "mild": 0,
        "moderate": 0,
        "moderately_severe": 0,
        "severe": 0
    }
    for severity, count in severity_distribution:
        if severity in severity_counts:
            severity_counts[severity] = count
    
    # Detecciones de depresión
    total_detections = db.query(func.count(DepressionDetection.id)).scalar() or 0
    positive_detections = db.query(func.count(DepressionDetection.id)).filter(
        DepressionDetection.is_depressive == True
    ).scalar() or 0
    detections_week = db.query(func.count(DepressionDetection.id)).filter(
        DepressionDetection.detected_at >= week_ago
    ).scalar() or 0
    
    # Evaluaciones conversacionales PHQ-9
    total_conversational = db.query(func.count(PHQ9ConversationalAssessment.id)).scalar() or 0
    completed_conversational = db.query(func.count(PHQ9ConversationalAssessment.id)).filter(
        PHQ9ConversationalAssessment.is_active == False
    ).scalar() or 0
    
    # Usuarios que requieren atención
    users_requiring_attention = db.query(func.count(MentalHealthSummary.user_id)).filter(
        MentalHealthSummary.requires_attention == True
    ).scalar() or 0
    
    # Score promedio PHQ-9
    avg_phq9_score = db.query(func.avg(PHQ9Assessment.total_score)).scalar() or 0
    max_phq9_score = db.query(func.max(PHQ9Assessment.total_score)).scalar() or 0
    
    return {
        "timestamp": datetime.utcnow(),
        "admin_email": admin_email,
        "users": {
            "total": total_users,
            "active": active_users,
            "admins": admins_count,
            "new_this_week": new_users_week,
            "requiring_attention": users_requiring_attention
        },
        "messages": {
            "total": total_messages,
            "this_week": messages_week,
            "avg_per_user": round(total_messages / total_users, 2) if total_users > 0 else 0
        },
        "phq9_assessments": {
            "total": total_phq9_assessments,
            "this_week": assessments_week,
            "avg_score": round(avg_phq9_score, 2),
            "max_score": max_phq9_score,
            "by_severity": severity_counts
        },
        "depression_detections": {
            "total": total_detections,
            "positive": positive_detections,
            "this_week": detections_week,
            "positive_rate": f"{(positive_detections / total_detections * 100) if total_detections > 0 else 0:.1f}%"
        },
        "conversational_assessments": {
            "total": total_conversational,
            "completed": completed_conversational,
            "in_progress": total_conversational - completed_conversational
        }
    }


@router.get("/dashboard/users")
def get_users_list(
    admin_email: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Obtiene lista de todos los usuarios con información resumida.
    """
    users = db.query(User).offset(offset).limit(limit).all()
    
    users_data = []
    for user in users:
        # Obtener resumen de salud
        summary = db.query(MentalHealthSummary).filter(
            MentalHealthSummary.user_id == user.id
        ).first()
        
        # Contar mensajes
        message_count = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.user_id == user.id
        ).scalar() or 0
        
        # Última evaluación
        last_assessment = db.query(PHQ9Assessment).filter(
            PHQ9Assessment.user_id == user.id
        ).order_by(PHQ9Assessment.created_at.desc()).first()
        
        users_data.append({
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "messages_count": message_count,
            "risk_level": summary.overall_risk_level if summary else "unknown",
            "requires_attention": summary.requires_attention if summary else False,
            "last_assessment": last_assessment.created_at if last_assessment else None
        })
    
    total = db.query(func.count(User.id)).scalar()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "users": users_data
    }


@router.get("/dashboard/user/{user_id}")
def get_user_detail(
    user_id: int,
    admin_email: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Obtiene información detallada de un usuario específico.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    
    # Resumen de salud
    summary = db.query(MentalHealthSummary).filter(
        MentalHealthSummary.user_id == user.id
    ).first()
    
    # Últimas evaluaciones PHQ-9
    assessments = db.query(PHQ9Assessment).filter(
        PHQ9Assessment.user_id == user.id
    ).order_by(PHQ9Assessment.created_at.desc()).limit(5).all()
    
    # Detecciones de depresión
    detections = db.query(DepressionDetection).filter(
        DepressionDetection.user_id == user.id
    ).order_by(DepressionDetection.detected_at.desc()).limit(10).all()
    
    # Estadísticas generales
    message_count = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.user_id == user.id
    ).scalar() or 0
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at
        },
        "health_summary": {
            "overall_risk_level": summary.overall_risk_level if summary else None,
            "requires_attention": summary.requires_attention if summary else False,
            "latest_phq9_score": summary.latest_phq9_score if summary else None,
            "total_assessments": summary.total_phq9_assessments if summary else 0,
            "depression_detections": summary.depression_detection_count if summary else 0
        },
        "statistics": {
            "total_messages": message_count,
            "total_assessments": len(assessments),
            "total_detections": len(detections)
        },
        "recent_assessments": [
            {
                "id": a.id,
                "score": a.total_score,
                "severity": a.severity,
                "created_at": a.created_at
            }
            for a in assessments
        ],
        "recent_detections": [
            {
                "id": d.id,
                "detected": d.is_depressive,
                "risk_level": d.risk_level,
                "confidence": d.confidence_score,
                "detected_at": d.detected_at
            }
            for d in detections
        ]
    }


@router.get("/dashboard/high-risk-users")
def get_high_risk_users(
    admin_email: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los usuarios con nivel de riesgo severo o crítico.
    """
    high_risk_users = db.query(MentalHealthSummary).filter(
        MentalHealthSummary.requires_attention == True
    ).all()
    
    users_data = []
    for summary in high_risk_users:
        user = db.query(User).filter(User.id == summary.user_id).first()
        if user:
            users_data.append({
                "user_id": user.id,
                "email": user.email,
                "risk_level": summary.overall_risk_level,
                "latest_score": summary.latest_phq9_score,
                "high_risk_detections": summary.high_risk_detections,
                "last_alert": summary.last_alert_sent,
                "updated_at": summary.updated_at
            })
    
    return {
        "total_high_risk": len(users_data),
        "users": users_data
    }
