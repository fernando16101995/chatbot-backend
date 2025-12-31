from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/")
def chat(message: str, user: str = Depends(get_current_user)):
    return {
        "reply": f"Hola {user}, dijiste: {message}"
    }
