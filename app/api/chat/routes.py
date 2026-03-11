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
from app.models.assessment import DepressionDetection
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
        # Si está esperando respuesta, guardar la respuesta del usuario
        if active_assessment.waiting_for_response:
            await conversational_phq9.save_user_response(
                db, 
                active_assessment, 
                payload.message
            )
            # Recargar assessment después de guardar
            db.refresh(active_assessment)
        
        # Determinar si incluir siguiente pregunta PHQ-9
        # Threshold=1 permite 1 mensaje de conversación entre preguntas
        if conversational_phq9.should_ask_next_question(active_assessment, messages_threshold=1):
            phq9_question = conversational_phq9.get_next_question(db, active_assessment)
            if phq9_question:
                print(f"📋 Enviando pregunta PHQ-9: {phq9_question}")
        else:
            # Solo incrementar contador si NO está esperando respuesta
            if not active_assessment.waiting_for_response:
                conversational_phq9.increment_message_counter(db, active_assessment)
    
    async def event_generator():
        try:
            # Enviar mensaje inicial inmediatamente para evitar timeout
            yield "data: \n\n"
            
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
        except Exception as e:
            print(f"❌ Error en streaming: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: Error: {str(e)}\n\n"
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
    Si no tiene mensajes, crea un mensaje de bienvenida automático.
    """
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"messages": [], "total": 0}
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == user.id
    ).order_by(ChatMessage.created_at.asc()).limit(limit).all()
    
    # Si no tiene mensajes, crear mensaje de bienvenida
    if len(messages) == 0:
        welcome_message = ChatMessage(
            user_id=user.id,
            role="assistant",
            content=f"""¡Hola! 👋 Es un gusto conocerte.

Soy Seren, tu compañero de confianza en este espacio seguro. Estoy aquí para escucharte sin juzgarte, entenderte y acompañarte en lo que necesites.

A veces es difícil encontrar alguien con quien hablar abiertamente. ¿Sabes qué? No tienes que guardar todo para ti. Este es tu espacio.

¿Cómo te sientes hoy? ¿Hay algo en tu mente que te gustaría compartir? Puede ser cualquier cosa: lo que te preocupa, lo que te emociona, o simplemente cómo ha sido tu día.

Estoy aquí para ti. 💙"""
        )
        db.add(welcome_message)
        db.commit()
        db.refresh(welcome_message)
        messages = [welcome_message]
    
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

    try:
        # Primero eliminar detecciones que referencian mensajes del usuario.
        user_message_ids = db.query(ChatMessage.id).filter(
            ChatMessage.user_id == user.id
        ).subquery()

        db.query(DepressionDetection).filter(
            DepressionDetection.message_id.in_(user_message_ids)
        ).delete(synchronize_session=False)

        deleted = db.query(ChatMessage).filter(
            ChatMessage.user_id == user.id
        ).delete(synchronize_session=False)

        db.commit()
    except Exception:
        db.rollback()
        raise
    
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
