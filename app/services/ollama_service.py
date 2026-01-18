import httpx
from typing import AsyncGenerator, List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.chat_message import ChatMessage
from app.models.user import User

class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama3.1:8b"
    
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
        
        # Si hay pregunta PHQ-9, agregar instrucción al sistema
        if phq9_question:
            system_prompt = f"""Eres un asistente empático y conversacional. 
Responde al usuario de manera natural y después, de forma suave y empática, 
haz esta pregunta: "{phq9_question}"

Integra la pregunta de forma natural en la conversación, mostrando genuino interés."""
            
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Guardar mensaje del usuario
        self.save_message(db, user_email, "user", user_message)
        
        # Hacer request a Ollama con streaming
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        
        assistant_response = ""
        
        async with httpx.AsyncClient(timeout=120.0) as client:
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
                                assistant_response += content
                                yield content
                            
                            # Ollama envía done: true cuando termina
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        
        # Guardar respuesta completa del asistente
        if assistant_response:
            self.save_message(db, user_email, "assistant", assistant_response)
