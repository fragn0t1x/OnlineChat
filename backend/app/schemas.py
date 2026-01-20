from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MessageCreate(BaseModel):
    text: Optional[str] = None

class MessageOut(BaseModel):
    id: int
    sender: str
    text: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionOut(BaseModel):
    id: int
    messages: List[MessageOut]

    class Config:
        from_attributes = True