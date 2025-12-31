from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth.routes import router as auth_router
from app.api.chat.routes import router as chat_router  

app = FastAPI(
    title="Chatbot IA Backend",
    version="1.0.0"
)

# 🔓 CORS (para que Android pueda conectarse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego lo restringimos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)

@app.get("/")
def root():
    return {
        "status": "200",
        "message": "Backend Chatbot IA activo 🚀"
    }
