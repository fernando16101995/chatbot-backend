import httpx
from typing import AsyncGenerator, List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.chat_message import ChatMessage
from app.models.user import User

class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama3.2:1b"
        self.max_response_chars = 500
    
    async def get_chat_history(self, db: Session, user_email: str, limit: int = 10) -> List[Dict[str, str]]:
        """Obtiene el historial de conversación del usuario para contexto"""
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return []
        
        messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user.id
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
        
        # Invertir para tener orden cronológico
        messages = list(reversed(messages))
        
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def save_message(self, db: Session, user_email: str, role: str, content: str):
        """Guarda un mensaje en el historial"""
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return
        
        message = ChatMessage(
            user_id=user.id,
            role=role,
            content=content
        )
        db.add(message)
        db.commit()
    
    async def chat_stream(
        self, 
        user_message: str, 
        db: Session, 
        user_email: str,
        use_context: bool = True,
        phq9_question: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Genera respuestas en streaming usando LLaMA con contexto de conversación.
        Si se proporciona phq9_question, la integra naturalmente en la conversación.
        """
        # Obtener historial
        history = await self.get_chat_history(db, user_email) if use_context else []
        
        # Construir mensajes para el modelo
        messages = history + [{"role": "user", "content": user_message}]
        
        # Guardar mensaje del usuario
        self.save_message(db, user_email, "user", user_message)
        
        # Prompt base para mantener el tono del asistente y evitar cortes de conversación.
        base_system_prompt = f"""Eres Seren, un asistente terapéutico cálido, empático y conversacional.

    Reglas obligatorias:
    - Responde SIEMPRE en español.
    - Mantén la respuesta principal breve: máximo {self.max_response_chars} caracteres.
    - Si el usuario sube el tono o usa lenguaje intenso, NO cierres la conversación ni digas que no puedes continuar.
    - En esos casos, valida la emoción y redirige con calma para seguir conversando.
    - Mantén un tono humano, respetuoso y cercano.
    """

        # Si hay pregunta PHQ-9, instruir a LLaMA para que genere SOLO comentario cálido
        if phq9_question:
            system_prompt = base_system_prompt + """

    Ahora mismo hay una evaluación PHQ-9 activa.

IMPORTANTE: Responde con UN COMENTARIO BREVE (1 oración máximo) que sea:
- Validador y empático con lo que el usuario acaba de decir
- Un poco arriesgado o provocador de forma amable
- Que conecte emocionalmente con el usuario

Ejemplos:
"Entiendo, puede ser frustrante por lo que estás pasando."
"Eso suena agotador... pero el hecho de que sigas aquí dice mucho de tu fortaleza."
"Vaya, eso debe ser difícil. A veces nuestro cuerpo nos habla de maneras que ignoramos."

NO hagas ninguna pregunta. SOLO el comentario empático."""

            messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            messages = [{"role": "system", "content": base_system_prompt}] + messages
        
        # Hacer request a Ollama con streaming
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        
        assistant_response = ""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            import json
                            chunk = json.loads(line)
                            
                            if "message" in chunk and "content" in chunk["message"]:
                                content = chunk["message"]["content"]
                                remaining_chars = self.max_response_chars - len(assistant_response)
                                if remaining_chars > 0:
                                    trimmed_content = content[:remaining_chars]
                                    assistant_response += trimmed_content
                                    if trimmed_content:
                                        yield trimmed_content
                            
                            # Ollama envía done: true cuando termina
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        
        # Si hay pregunta PHQ-9, agregarla después del comentario de LLaMA
        if phq9_question:
            phq9_text = f" {phq9_question}"
            print(f"✅ Agregando pregunta PHQ-9 exacta: {phq9_question}")
            assistant_response += phq9_text
            yield phq9_text
        
        # Guardar respuesta completa del asistente
        if assistant_response:
            self.save_message(db, user_email, "assistant", assistant_response)
