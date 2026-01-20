# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal, engine
from .. import models, schemas
from ..bot.telegram_bot import notify_new_message  # ← асинхронная функция
import uuid

models.Base.metadata.create_all(bind=engine)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/chat/start")
def start_chat(db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())
    visitor = models.Visitor(session_id=session_id)
    db.add(visitor)
    db.commit()
    db.refresh(visitor)
    chat = models.ChatSession(visitor_id=visitor.id)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return {"session_id": session_id, "chat_id": chat.id}

# 👇 ЭТОТ РОУТ ДОЛЖЕН БЫТЬ АСИНХРОННЫМ
@router.post("/chat/{chat_id}/message")
async def send_message(chat_id: int, msg: schemas.MessageCreate, db: Session = Depends(get_db)):
    message = models.Message(
        chat_session_id=chat_id,
        sender="visitor",
        text=msg.text
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # 👇 ВЫЗЫВАЕМ АСИНХРОННО
    await notify_new_message(chat_id, msg.text or "Пустое сообщение")
    return {"status": "ok"}

@router.post("/chat/{chat_id}/reply")
def reply_to_chat(chat_id: int, msg: schemas.MessageCreate, db: Session = Depends(get_db)):
    message = models.Message(
        chat_session_id=chat_id,
        sender="operator",
        text=msg.text
    )
    db.add(message)
    db.commit()
    return {"status": "ok"}

@router.get("/chat/{chat_id}", response_model=schemas.ChatSessionOut)
def get_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(models.ChatSession).filter(models.ChatSession.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = db.query(models.Message).filter(models.Message.chat_session_id == chat_id).all()
    return {"id": chat.id, "messages": messages}