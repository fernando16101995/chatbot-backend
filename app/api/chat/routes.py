from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.core.database import SessionLocal
from app.services.ollama_service import OllamaService
from app.services.depression_detector import DepressionDetectorService
from app.services.phq9_service import PHQ9Service
from app.services.conversational_phq9_service import ConversationalPHQ9Service
from app.api.chat.schemas import ChatRequest, ChatHistoryResponse, ChatMessageResponse
from app.models.chat_message import ChatMessage
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["Chat"])
ollama_service = OllamaService()
depression_detector = DepressionDetectorService()
phq9_service = PHQ9Service()
conversational_phq9 = ConversationalPHQ9Service()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint con streaming de respuestas de LLaMA.
    Mantiene contexto de conversación por usuario.
    Analiza automáticamente cada mensaje para detectar depresión.
    Integra preguntas PHQ-9 de forma natural cuando detecta contenido depresivo.
    """
    
    # Obtener user_id
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    
    # Guardar mensaje del usuario primero para obtener message_id
    user_message = ChatMessage(
        user_id=user.id,
        role="user",
        content=payload.message
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # Analizar mensaje en background (detección de depresión)
    background_tasks.add_task(
        analyze_message_background,
        payload.message,
        user.id,
        user_message.id,
        db
    )
    
    # Verificar si hay evaluación PHQ-9 activa
    active_assessment = conversational_phq9.get_active_assessment(db, user.id)
    phq9_question = None
    
    if active_assessment:
        # Si el usuario acaba de responder, guardar la respuesta
        if active_assessment.current_question <= 9:
            # Verificar si este mensaje es respuesta a la pregunta anterior
            last_messages = await ollama_service.get_chat_history(db, user_email, limit=2)
            if len(last_messages) >= 1:
                # Guardar respuesta del usuario
                await conversational_phq9.save_user_response(
                    db, 
                    active_assessment, 
                    payload.message
                )
                # Recargar assessment después de guardar
                db.refresh(active_assessment)
        
        # Determinar si incluir siguiente pregunta PHQ-9
        if conversational_phq9.should_ask_next_question(active_assessment, messages_threshold=3):
            phq9_question = conversational_phq9.get_next_question(active_assessment)
        else:
            # Incrementar contador de mensajes
            conversational_phq9.increment_message_counter(db, active_assessment)
    
    async def event_generator():
        async for chunk in ollama_service.chat_stream(
            payload.message, 
            db, 
            user_email,
            payload.use_context,
            phq9_question=phq9_question
        ):
            # Server-Sent Events format
            yield f"data: {chunk}\n\n"
        
        # Indicar fin del stream
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


async def analyze_message_background(message: str, user_id: int, message_id: int, db: Session):
    """
    Función auxiliar para analizar mensaje en background.
    Detecta depresión e inicia evaluación PHQ-9 conversacional si es necesario.
    """
    from app.core.database import SessionLocal
    db_bg = SessionLocal()
    try:
        # Detectar depresión
        result = await depression_detector.analyze_message(message, user_id, message_id, db_bg)
        
        # Si detectó depresión, verificar si iniciar evaluación PHQ-9
        if result.get('detected', False):
            should_start = conversational_phq9.should_start_assessment(
                db_bg, 
                user_id, 
                depression_detected=True
            )
            
            if should_start:
                conversational_phq9.start_assessment(db_bg, user_id)
                print(f"✅ Iniciada evaluación PHQ-9 conversacional para usuario {user_id}")
    finally:
        db_bg.close()


@router.get("/history", response_model=ChatHistoryResponse)
def get_chat_history(
    limit: int = 50,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de conversación del usuario.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"messages": [], "total": 0}
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == user.id
    ).order_by(ChatMessage.created_at.asc()).limit(limit).all()
    
    return {
        "messages": messages,
        "total": len(messages)
    }


@router.delete("/history")
def clear_chat_history(
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Borra todo el historial de conversación del usuario.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"message": "Usuario no encontrado"}
    
    deleted = db.query(ChatMessage).filter(
        ChatMessage.user_id == user.id
    ).delete()
    db.commit()
    
    return {"message": f"{deleted} mensajes eliminados"}


@router.post("/analyze-phq9")
async def analyze_phq9(
    narrative: str,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analiza un texto narrativo largo del usuario con el cuestionario PHQ-9.
    El usuario debe proporcionar una descripción de cómo se ha sentido.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    
    result = await phq9_service.analyze_narrative(narrative, user.id, db)
    return result
