"""
Servicio de detección de lenguaje depresivo usando LLaMA.
Analiza mensajes del usuario en español para detectar patrones depresivos.
"""

import httpx
import json
from typing import Dict
from sqlalchemy.orm import Session
from app.models.assessment import DepressionDetection, MentalHealthSummary
from app.models.user import User

class DepressionDetectorService:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.1:8b"
    
    async def analyze_message(self, text: str, user_id: int, message_id: int, db: Session) -> Dict:
        """
        Analiza un mensaje para detectar lenguaje depresivo.
        Usa LLaMA con prompt engineering específico.
        """
        
        prompt = f"""Eres un experto en salud mental. Analiza el siguiente mensaje y determina si contiene lenguaje depresivo.

Mensaje: "{text}"

Indica:
1. ¿Tiene lenguaje depresivo? (sí/no)
2. Nivel de confianza (0-100)
3. Nivel de riesgo (bajo/medio/alto/severo)
4. Palabras clave detectadas (máximo 5)

Responde SOLO con este formato JSON:
{{
    "es_depresivo": true/false,
    "confianza": 85,
    "riesgo": "alto",
    "palabras_clave": ["palabra1", "palabra2"]
}}"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                
                # Guardar detección en BD
                detection = DepressionDetection(
                    user_id=user_id,
                    message_id=message_id,
                    is_depressive=analysis['es_depresivo'],
                    confidence_score=analysis['confianza'] / 100.0,
                    risk_level=analysis['riesgo'],
                    detected_keywords=analysis.get('palabras_clave', [])
                )
                
                db.add(detection)
                
                # Actualizar resumen si es positivo
                if analysis['es_depresivo']:
                    self._update_user_summary(user_id, analysis['riesgo'], db)
                
                db.commit()
                
                return {
                    "detected": analysis['es_depresivo'],
                    "confidence": analysis['confianza'] / 100.0,
                    "risk_level": analysis['riesgo'],
                    "keywords": analysis.get('palabras_clave', [])
                }
                
        except Exception as e:
            print(f"Error en detección: {e}")
            return {
                "detected": False,
                "confidence": 0.0,
                "risk_level": "low",
                "keywords": [],
                "error": str(e)
            }
    
    def _update_user_summary(self, user_id: int, risk_level: str, db: Session):
        """Actualiza el resumen de salud mental del usuario"""
        from datetime import datetime
        
        summary = db.query(MentalHealthSummary).filter(
            MentalHealthSummary.user_id == user_id
        ).first()
        
        if not summary:
            summary = MentalHealthSummary(user_id=user_id)
            db.add(summary)
        
        summary.depression_detection_count += 1
        summary.last_detection_date = datetime.utcnow()
        
        if risk_level in ['alto', 'severo', 'high', 'severe']:
            summary.high_risk_detections += 1
            summary.requires_attention = True
        
        # Actualizar riesgo general
        if summary.high_risk_detections >= 3:
            summary.overall_risk_level = "critical"
        elif risk_level == "severo":
            summary.overall_risk_level = "severe"
        elif risk_level == "alto":
            summary.overall_risk_level = "moderate"
        
        db.commit()
