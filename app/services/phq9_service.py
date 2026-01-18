"""
Servicio PHQ-9 usando LLaMA.
Analiza narrativas largas del usuario y predice síntomas PHQ-9.
"""

import httpx
import json
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models.assessment import PHQ9Assessment, MentalHealthSummary
from datetime import datetime

class PHQ9Service:
    # Las 9 preguntas oficiales del PHQ-9
    QUESTIONS = [
        {
            "number": 1,
            "text": "Poco interés o placer en hacer cosas",
            "key": "q1_interest"
        },
        {
            "number": 2,
            "text": "Sentirse deprimido, decaído o sin esperanzas",
            "key": "q2_depressed"
        },
        {
            "number": 3,
            "text": "Problemas para dormir o dormir demasiado",
            "key": "q3_sleep"
        },
        {
            "number": 4,
            "text": "Sentirse cansado o tener poca energía",
            "key": "q4_energy"
        },
        {
            "number": 5,
            "text": "Poco apetito o comer en exceso",
            "key": "q5_appetite"
        },
        {
            "number": 6,
            "text": "Sentirse mal consigo mismo, sentirse un fracaso o haber decepcionado a su familia",
            "key": "q6_failure"
        },
        {
            "number": 7,
            "text": "Problemas para concentrarse en cosas como leer o ver televisión",
            "key": "q7_concentration"
        },
        {
            "number": 8,
            "text": "Moverse o hablar tan lento que otras personas lo notaron, o estar tan inquieto que se movía mucho más de lo normal",
            "key": "q8_movement"
        },
        {
            "number": 9,
            "text": "Pensamientos de que estaría mejor muerto o de hacerse daño de alguna manera",
            "key": "q9_suicide"
        }
    ]
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.1:8b"
    
    async def analyze_narrative(self, text: str, user_id: int, db: Session) -> Dict:
        """
        Analiza un texto narrativo largo del usuario y detecta síntomas PHQ-9.
        """
        
        # Crear lista de síntomas para el prompt
        symptoms_list = "\n".join([f"{q['number']}. {q['text']}" for q in self.QUESTIONS])
        
        prompt = f"""Eres un experto en salud mental especializado en el cuestionario PHQ-9.

Analiza el siguiente texto del usuario y determina qué síntomas del PHQ-9 están presentes.

Texto del usuario:
"{text}"

Síntomas PHQ-9 a evaluar:
{symptoms_list}

Para CADA síntoma, indica:
- presente: true/false (¿el texto menciona o implica este síntoma?)
- confianza: 0-100 (qué tan seguro estás)

Responde SOLO con este formato JSON:
{{
    "sintomas": [
        {{"numero": 1, "presente": false, "confianza": 20}},
        {{"numero": 2, "presente": true, "confianza": 95}},
        ... (los 9 síntomas)
    ]
}}"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
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
                
                # Procesar resultados
                assessment_data = {
                    "user_id": user_id,
                    "narrative_text": text,
                }
                
                total_score = 0
                
                for symptom in analysis['sintomas']:
                    num = symptom['numero']
                    presente = symptom['presente']
                    confianza = symptom['confianza'] / 100.0
                    
                    q_key = self.QUESTIONS[num - 1]['key']
                    
                    # Guardar predicción (0 o 1)
                    assessment_data[q_key] = 1 if presente else 0
                    assessment_data[f"{q_key}_confidence"] = confianza
                    
                    if presente:
                        total_score += 1
                
                assessment_data['total_score'] = total_score
                assessment_data['severity'] = self._calculate_severity(total_score)
                
                # Guardar en BD
                assessment = PHQ9Assessment(**assessment_data)
                db.add(assessment)
                
                # Actualizar resumen del usuario
                self._update_user_summary(user_id, total_score, assessment_data['severity'], db)
                
                db.commit()
                
                return {
                    "assessment_id": assessment.id,
                    "total_score": total_score,
                    "severity": assessment_data['severity'],
                    "symptoms": analysis['sintomas']
                }
                
        except Exception as e:
            print(f"Error en análisis PHQ-9: {e}")
            return {
                "error": str(e),
                "total_score": 0,
                "severity": "unknown"
            }
    
    def _calculate_severity(self, score: int) -> str:
        """
        Calcula la severidad según el score PHQ-9.
        0-4: Minimal
        5-9: Mild
        10-14: Moderate
        15-19: Moderately severe
        20-27: Severe
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
    
    def _update_user_summary(self, user_id: int, score: int, severity: str, db: Session):
        """Actualiza el resumen con la última evaluación PHQ-9"""
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
    
    def get_user_assessments(self, user_id: int, db: Session, limit: int = 10) -> List[PHQ9Assessment]:
        """Obtiene el historial de evaluaciones PHQ-9 del usuario"""
        return db.query(PHQ9Assessment).filter(
            PHQ9Assessment.user_id == user_id
        ).order_by(PHQ9Assessment.created_at.desc()).limit(limit).all()
