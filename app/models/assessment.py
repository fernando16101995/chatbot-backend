from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, JSON
from app.core.database import Base
from datetime import datetime

class PHQ9Assessment(Base):
    """
    Tabla para almacenar evaluaciones PHQ-9.
    Cada registro representa una evaluación completa (las 9 preguntas).
    """
    __tablename__ = "phq9_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Texto narrativo analizado
    narrative_text = Column(Text, nullable=False)
    
    # Predicciones del modelo (0 o 1 para cada pregunta)
    q1_interest = Column(Integer, default=0)  # Little interest or pleasure
    q2_depressed = Column(Integer, default=0)  # Feeling down, depressed, hopeless
    q3_sleep = Column(Integer, default=0)  # Sleep problems
    q4_energy = Column(Integer, default=0)  # Feeling tired
    q5_appetite = Column(Integer, default=0)  # Poor appetite or overeating
    q6_failure = Column(Integer, default=0)  # Feeling bad about yourself
    q7_concentration = Column(Integer, default=0)  # Trouble concentrating
    q8_movement = Column(Integer, default=0)  # Moving/speaking slowly or restless
    q9_suicide = Column(Integer, default=0)  # Thoughts of death/suicide
    
    # Probabilidades del modelo (0.0-1.0)
    q1_confidence = Column(Float, default=0.0)
    q2_confidence = Column(Float, default=0.0)
    q3_confidence = Column(Float, default=0.0)
    q4_confidence = Column(Float, default=0.0)
    q5_confidence = Column(Float, default=0.0)
    q6_confidence = Column(Float, default=0.0)
    q7_confidence = Column(Float, default=0.0)
    q8_confidence = Column(Float, default=0.0)
    q9_confidence = Column(Float, default=0.0)
    
    # Score total (0-9, suma de las respuestas)
    total_score = Column(Integer, default=0)
    
    # Severidad basada en score
    severity = Column(String, default="minimal")  # minimal, mild, moderate, severe
    
    created_at = Column(DateTime, default=datetime.utcnow)


class DepressionDetection(Base):
    """
    Tabla para almacenar detecciones de lenguaje depresivo
    en mensajes individuales del usuario.
    """
    __tablename__ = "depression_detections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False)
    
    # Predicción del modelo
    is_depressive = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)  # 0.0-1.0
    
    # Clasificación de riesgo
    risk_level = Column(String, default="low")  # low, medium, high, severe
    
    # Palabras clave detectadas (opcional)
    detected_keywords = Column(JSON, nullable=True)
    
    detected_at = Column(DateTime, default=datetime.utcnow)


class MentalHealthSummary(Base):
    """
    Tabla de resumen del estado de salud mental por usuario.
    Se actualiza con cada nueva evaluación o detección.
    """
    __tablename__ = "mental_health_summary"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # PHQ-9
    latest_phq9_score = Column(Integer, nullable=True)
    latest_phq9_severity = Column(String, nullable=True)
    latest_phq9_date = Column(DateTime, nullable=True)
    total_phq9_assessments = Column(Integer, default=0)
    
    # Detecciones de depresión
    depression_detection_count = Column(Integer, default=0)
    last_detection_date = Column(DateTime, nullable=True)
    high_risk_detections = Column(Integer, default=0)  # Cuántas veces se detectó riesgo alto
    
    # Riesgo general
    overall_risk_level = Column(String, default="minimal")  # minimal, mild, moderate, severe, critical
    
    # Banderas de alerta
    requires_attention = Column(Boolean, default=False)
    last_alert_sent = Column(DateTime, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PHQ9ConversationalAssessment(Base):
    """
    Tabla para trackear evaluaciones PHQ-9 conversacionales.
    Registra el progreso de las 9 preguntas insertadas naturalmente en el chat.
    """
    __tablename__ = "phq9_conversational_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Estado de la evaluación
    is_active = Column(Boolean, default=True)  # Si está en progreso
    current_question = Column(Integer, default=1)  # Pregunta actual (1-9)
    messages_since_last_question = Column(Integer, default=0)  # Contador de mensajes
    
    # Respuestas del usuario (texto libre)
    q1_response = Column(Text, nullable=True)
    q2_response = Column(Text, nullable=True)
    q3_response = Column(Text, nullable=True)
    q4_response = Column(Text, nullable=True)
    q5_response = Column(Text, nullable=True)
    q6_response = Column(Text, nullable=True)
    q7_response = Column(Text, nullable=True)
    q8_response = Column(Text, nullable=True)
    q9_response = Column(Text, nullable=True)
    
    # Scores inferidos (0-3 por pregunta según estándar PHQ-9)
    q1_score = Column(Integer, default=0)
    q2_score = Column(Integer, default=0)
    q3_score = Column(Integer, default=0)
    q4_score = Column(Integer, default=0)
    q5_score = Column(Integer, default=0)
    q6_score = Column(Integer, default=0)
    q7_score = Column(Integer, default=0)
    q8_score = Column(Integer, default=0)
    q9_score = Column(Integer, default=0)
    
    # Resultado final
    total_score = Column(Integer, default=0)  # 0-27
    severity = Column(String, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
