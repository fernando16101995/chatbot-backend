"""
Servicio de evaluación PHQ-9 conversacional.
Integra las preguntas del PHQ-9 de forma natural durante el chat.
"""

import httpx
import json
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models.assessment import PHQ9ConversationalAssessment, MentalHealthSummary
from app.models.user import User
from datetime import datetime


class ConversationalPHQ9Service:
    """
    Gestiona evaluaciones PHQ-9 conversacionales que se insertan
    naturalmente durante el chat cuando se detecta contenido depresivo.
    """
    
    # Las 9 preguntas del PHQ-9 en formato conversacional
    QUESTIONS = [
        {
            "number": 1,
            "question": "Me gustaría saber, ¿has tenido poco interés o placer en hacer cosas últimamente?",
            "symptom": "Poco interés o placer en hacer cosas"
        },
        {
            "number": 2,
            "question": "¿Te has sentido decaído, deprimido o sin esperanzas en las últimas semanas?",
            "symptom": "Sentirse deprimido, decaído o sin esperanzas"
        },
        {
            "number": 3,
            "question": "¿Has tenido problemas para dormir, o tal vez has dormido demasiado?",
            "symptom": "Problemas para dormir o dormir demasiado"
        },
        {
            "number": 4,
            "question": "¿Te has sentido cansado o con poca energía?",
            "symptom": "Sentirse cansado o tener poca energía"
        },
        {
            "number": 5,
            "question": "¿Has notado cambios en tu apetito, ya sea comer menos o comer en exceso?",
            "symptom": "Poco apetito o comer en exceso"
        },
        {
            "number": 6,
            "question": "¿Te has sentido mal contigo mismo, como si fueras un fracaso o hubieras decepcionado a tu familia?",
            "symptom": "Sentirse mal consigo mismo o sentirse un fracaso"
        },
        {
            "number": 7,
            "question": "¿Has tenido problemas para concentrarte en cosas como leer, ver televisión o trabajar?",
            "symptom": "Problemas para concentrarse"
        },
        {
            "number": 8,
            "question": "¿Has notado que te mueves o hablas más lento de lo normal, o por el contrario, estás más inquieto de lo habitual?",
            "symptom": "Moverse o hablar lento, o estar muy inquieto"
        },
        {
            "number": 9,
            "question": "¿Has tenido pensamientos de que estarías mejor muerto o de hacerte daño de alguna manera?",
            "symptom": "Pensamientos de muerte o autolesión"
        }
    ]
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.1:8b"
    
    def should_start_assessment(
        self, 
        db: Session, 
        user_id: int, 
        depression_detected: bool
    ) -> bool:
        """
        Determina si se debe iniciar una evaluación PHQ-9 conversacional.
        
        Inicia si:
        - Se detectó lenguaje depresivo
        - No hay evaluación activa en progreso
        """
        if not depression_detected:
            return False
        
        # Verificar si ya hay una evaluación activa
        active = db.query(PHQ9ConversationalAssessment).filter(
            PHQ9ConversationalAssessment.user_id == user_id,
            PHQ9ConversationalAssessment.is_active == True
        ).first()
        
        return active is None
    
    def start_assessment(self, db: Session, user_id: int) -> PHQ9ConversationalAssessment:
        """Inicia una nueva evaluación conversacional."""
        assessment = PHQ9ConversationalAssessment(
            user_id=user_id,
            is_active=True,
            current_question=1,
            messages_since_last_question=0
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment
    
    def get_active_assessment(
        self, 
        db: Session, 
        user_id: int
    ) -> Optional[PHQ9ConversationalAssessment]:
        """Obtiene la evaluación activa del usuario."""
        return db.query(PHQ9ConversationalAssessment).filter(
            PHQ9ConversationalAssessment.user_id == user_id,
            PHQ9ConversationalAssessment.is_active == True
        ).first()
    
    def should_ask_next_question(
        self, 
        assessment: PHQ9ConversationalAssessment,
        messages_threshold: int = 3
    ) -> bool:
        """
        Determina si es momento de hacer la siguiente pregunta PHQ-9.
        
        Args:
            assessment: Evaluación actual
            messages_threshold: Número de mensajes entre preguntas (default: 3)
        """
        if not assessment or not assessment.is_active:
            return False
        
        # Si ya completó las 9 preguntas
        if assessment.current_question > 9:
            return False
        
        # Si es la primera pregunta, hacerla inmediatamente
        if assessment.current_question == 1 and assessment.messages_since_last_question == 0:
            return True
        
        # Si han pasado suficientes mensajes, hacer siguiente pregunta
        return assessment.messages_since_last_question >= messages_threshold
    
    def get_next_question(
        self, 
        assessment: PHQ9ConversationalAssessment
    ) -> Optional[str]:
        """Obtiene la siguiente pregunta PHQ-9 a realizar."""
        if assessment.current_question > 9:
            return None
        
        question_data = self.QUESTIONS[assessment.current_question - 1]
        return question_data["question"]
    
    def increment_message_counter(
        self, 
        db: Session, 
        assessment: PHQ9ConversationalAssessment
    ):
        """Incrementa el contador de mensajes desde la última pregunta."""
        assessment.messages_since_last_question += 1
        db.commit()
    
    async def save_user_response(
        self,
        db: Session,
        assessment: PHQ9ConversationalAssessment,
        user_response: str
    ):
        """
        Guarda la respuesta del usuario a la pregunta PHQ-9 actual
        e infiere el score usando IA.
        """
        question_num = assessment.current_question
        
        # Guardar respuesta textual
        setattr(assessment, f"q{question_num}_response", user_response)
        
        # Inferir score (0-3) usando LLaMA
        score = await self._infer_score(user_response, question_num)
        setattr(assessment, f"q{question_num}_score", score)
        
        # Avanzar a siguiente pregunta
        assessment.current_question += 1
        assessment.messages_since_last_question = 0
        
        # Si completó todas las preguntas, finalizar evaluación
        if assessment.current_question > 9:
            await self._finalize_assessment(db, assessment)
        
        db.commit()
    
    async def _infer_score(self, user_response: str, question_num: int) -> int:
        """
        Infiere el score PHQ-9 (0-3) de la respuesta del usuario usando IA.
        
        Escala PHQ-9:
        0 = Ningún día
        1 = Varios días
        2 = Más de la mitad de los días
        3 = Casi todos los días
        """
        question_data = self.QUESTIONS[question_num - 1]
        
        prompt = f"""Eres un experto en evaluación PHQ-9. Analiza la respuesta del usuario y asigna un score de 0 a 3.

Pregunta: {question_data['symptom']}
Respuesta del usuario: "{user_response}"

Escala:
0 = No presenta el síntoma o ningún día
1 = Lo presenta varios días
2 = Más de la mitad de los días
3 = Casi todos los días

Responde SOLO con un JSON:
{{
    "score": 0-3,
    "razonamiento": "breve explicación"
}}"""

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    }
                )
                
                result = response.json()
                analysis = json.loads(result['response'])
                score = analysis.get('score', 0)
                
                # Validar rango
                return max(0, min(3, score))
                
        except Exception as e:
            print(f"Error infiriendo score: {e}")
            # Score conservador en caso de error
            return 1
    
    async def _finalize_assessment(
        self, 
        db: Session, 
        assessment: PHQ9ConversationalAssessment
    ):
        """Finaliza la evaluación, calcula score total y actualiza resumen."""
        # Calcular score total (0-27)
        total = sum([
            assessment.q1_score,
            assessment.q2_score,
            assessment.q3_score,
            assessment.q4_score,
            assessment.q5_score,
            assessment.q6_score,
            assessment.q7_score,
            assessment.q8_score,
            assessment.q9_score
        ])
        
        assessment.total_score = total
        assessment.severity = self._calculate_severity(total)
        assessment.is_active = False
        assessment.completed_at = datetime.utcnow()
        
        # Actualizar resumen del usuario
        self._update_user_summary(db, assessment.user_id, total, assessment.severity)
        
        db.commit()
    
    def _calculate_severity(self, score: int) -> str:
        """
        Calcula severidad según score PHQ-9 estándar (0-27).
        """
        if score <= 4:
            return "minimal"
        elif score <= 9:
            return "mild"
        elif score <= 14:
            return "moderate"
        elif score <= 19:
            return "moderately_severe"
        else:
            return "severe"
    
    def _update_user_summary(
        self, 
        db: Session, 
        user_id: int, 
        score: int, 
        severity: str
    ):
        """Actualiza el resumen de salud mental del usuario."""
        summary = db.query(MentalHealthSummary).filter(
            MentalHealthSummary.user_id == user_id
        ).first()
        
        if not summary:
            summary = MentalHealthSummary(user_id=user_id)
            db.add(summary)
        
        summary.latest_phq9_score = score
        summary.latest_phq9_severity = severity
        summary.latest_phq9_date = datetime.utcnow()
        summary.total_phq9_assessments += 1
        
        # Actualizar riesgo general
        if severity in ["severe", "moderately_severe"]:
            summary.overall_risk_level = "severe"
            summary.requires_attention = True
        elif severity == "moderate":
            summary.overall_risk_level = "moderate"
        
        db.commit()
