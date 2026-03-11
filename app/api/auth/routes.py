from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.api.auth.schemas import UserRegister, UserResponse, LoginRequest, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=UserResponse)
def register(user: UserRegister, db: Session = Depends(get_db)):

    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )

    new_user = User(
        email=user.email,
        password_hash=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "Usuario registrado correctamente",
        "email": new_user.email
    }

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )

    # Solo enviar saludo de reingreso si el usuario ya ha conversado antes.
    has_user_history = db.query(ChatMessage.id).filter(
        ChatMessage.user_id == user.id,
        ChatMessage.role == "user"
    ).first() is not None

    from datetime import datetime

    welcome_messages = [
        """¡Hola de nuevo! 👋 Me alegra verte por aquí.

¿Cómo te ha ido desde la última vez? Estoy aquí para escucharte sin juzgarte y acompañarte en lo que necesites.

¿Hay algo en tu mente que te gustaría compartir hoy? 💙""",
        
        """¡Bienvenido de vuelta! 😊

Me alegra que estés aquí. Este es tu espacio seguro para hablar sobre lo que sientas.

¿Cómo ha estado tu día? ¿Algo que quieras platicar? 💙""",
        
        """¡Qué bueno verte de nuevo! 👋

Estoy aquí para ti. ¿Cómo te sientes hoy? No importa si es algo grande o pequeño, todo es válido aquí.

Cuéntame, ¿qué hay en tu mente? 💙"""
    ]

    if has_user_history:
        # Elegir mensaje aleatorio basado en la hora actual
        import random
        random.seed(datetime.now().hour)
        welcome_text = random.choice(welcome_messages)

        welcome_message = ChatMessage(
            user_id=user.id,
            role="assistant",
            content=welcome_text
        )
        db.add(welcome_message)
        db.commit()

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}
