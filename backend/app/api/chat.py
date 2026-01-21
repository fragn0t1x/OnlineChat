# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session
from ..database import SessionLocal, engine
from .. import models, schemas
from ..bot.telegram_bot import notify_new_message
import uuid
import os

models.Base.metadata.create_all(bind=engine)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Убедитесь, что папка uploads существует
os.makedirs("/app/uploads", exist_ok=True)

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

@router.post("/chat/{chat_id}/message")
async def send_message(
    chat_id: int,
    text: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    file_url = None
    if file:
        # Генерируем уникальное имя файла
        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = f"/app/uploads/{filename}"
        # Сохраняем файл
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        file_url = f"/uploads/{filename}"

    # Сохраняем сообщение в БД
    message = models.Message(
        chat_session_id=chat_id,
        sender="visitor",
        text=text,
        file_url=file_url
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Отправляем уведомление в Telegram
    preview = text or (f"📎 Файл: {file.filename}" if file else "Пустое сообщение")
    await notify_new_message(chat_id, preview, file_url)
    return {"status": "ok"}

@router.post("/chat/{chat_id}/reply")
async def reply_to_chat(
    chat_id: int,
    text: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    file_url = None
    if file:
        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = f"/app/uploads/{filename}"
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        file_url = f"/uploads/{filename}"

    message = models.Message(
        chat_session_id=chat_id,
        sender="operator",
        text=text,
        file_url=file_url
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