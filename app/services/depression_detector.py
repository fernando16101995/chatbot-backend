"""
Servicio de detección de lenguaje depresivo usando LLaMA.
Analiza mensajes del usuario en español para detectar patrones depresivos.
"""

import asyncio
import httpx
import json
import logging
import re
from typing import Dict
from sqlalchemy.orm import Session
from app.models.assessment import DepressionDetection, MentalHealthSummary
from app.models.user import User

logger = logging.getLogger(__name__)

# Reintentos con backoff exponencial para errores de parsing JSON
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # segundos

class DepressionDetectorService:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.1:8b"
    
    def _validate_keywords(self, keywords: list, text: str) -> tuple[list, int]:
        """
        Filtra las palabras clave que no aparecen en el texto original.
        Retorna (keywords_validadas, cantidad_alucinadas).
        """
        text_lower = text.lower()
        validated = [kw for kw in keywords if kw.lower() in text_lower]
        hallucinated = len(keywords) - len(validated)
        if hallucinated > 0:
            logger.warning(
                "Keyword hallucination detected: %d/%d keywords not found in original text "
                "(hallucinated: %s)",
                hallucinated,
                len(keywords),
                [kw for kw in keywords if kw.lower() not in text_lower],
            )
        return validated, hallucinated

    async def _call_llama(self, client: httpx.AsyncClient, prompt: str) -> Dict:
        """
        Llama a LLaMA y parsea el JSON de la respuesta.
        Lanza ValueError si el JSON está malformado.
        """
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
        raw = result['response']
        # Extraer JSON aunque LLaMA agregue texto extra alrededor
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError(f"No se encontró JSON en la respuesta de LLaMA: {raw[:200]}")
        return json.loads(match.group())

    async def analyze_message(self, text: str, user_id: int, message_id: int, db: Session) -> Dict:
        """
        Analiza un mensaje para detectar lenguaje depresivo.
        Usa LLaMA con prompt engineering específico.
        Reintenta hasta _MAX_RETRIES veces con backoff exponencial ante JSON malformado.
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

        last_error: Exception = None
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(_MAX_RETRIES):
                try:
                    analysis = await self._call_llama(client, prompt)

                    # Validar palabras clave contra el texto original
                    raw_keywords = analysis.get('palabras_clave', [])
                    validated_keywords, _ = self._validate_keywords(raw_keywords, text)

                    # Guardar detección en BD
                    detection = DepressionDetection(
                        user_id=user_id,
                        message_id=message_id,
                        is_depressive=analysis['es_depresivo'],
                        confidence_score=analysis['confianza'] / 100.0,
                        risk_level=analysis['riesgo'],
                        detected_keywords=validated_keywords
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
                        "keywords": validated_keywords
                    }

                except (ValueError, json.JSONDecodeError, KeyError) as e:
                    last_error = e
                    logger.warning(
                        "JSON parsing error in depression detector (user=%d, msg=%d, attempt=%d/%d): %s",
                        user_id, message_id, attempt + 1, _MAX_RETRIES, e,
                    )
                    if attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))

        logger.error(
            "❌ All %d retries exhausted in depression detector (user=%d, msg=%d): %s",
            _MAX_RETRIES, user_id, message_id, last_error,
        )
        return {
            "detected": False,
            "confidence": 0.0,
            "risk_level": "low",
            "keywords": [],
            "error": str(last_error)
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
