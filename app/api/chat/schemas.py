from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    use_context: bool = True  # Si usar historial de conversación

class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageResponse]
    total: int
