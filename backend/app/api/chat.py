from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from ..database import SessionLocal, engine
from .. import models, schemas
from ..bot.telegram_bot import notify_new_message
import uuid
import os
import json
from datetime import datetime, timedelta
import redis

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

models.Base.metadata.create_all(bind=engine)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = f"/app/uploads/{filename}"
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        file_url = f"/uploads/{filename}"

    message = models.Message(
        chat_session_id=chat_id,
        sender="visitor",
        text=text,
        file_url=file_url
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Clear typing status
    redis_client.delete(f"typing:{chat_id}")

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

    # Clear typing status
    redis_client.delete(f"typing:{chat_id}")
    return {"status": "ok"}


@router.get("/chat/{chat_id}", response_model=schemas.ChatSessionOut)
def get_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(models.ChatSession).filter(models.ChatSession.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = db.query(models.Message).filter(models.Message.chat_session_id == chat_id).all()
    return {"id": chat.id, "messages": messages}


# === НОВЫЕ ЭНДПОИНТЫ ===

@router.post("/chat/{chat_id}/typing")
async def set_typing(chat_id: int, is_typing: bool = True):
    if is_typing:
        redis_client.setex(f"typing:{chat_id}", 3, "1")  # expires in 3 seconds
    else:
        redis_client.delete(f"typing:{chat_id}")
    return {"status": "ok"}


@router.get("/chat/{chat_id}/typing")
async def get_typing(chat_id: int):
    is_typing = redis_client.exists(f"typing:{chat_id}")
    return {"is_typing": bool(is_typing)}


@router.post("/chat/{chat_id}/heartbeat")
async def heartbeat(chat_id: int, role: str = "visitor"):
    key = f"online:{chat_id}"
    status = {
        "role": role,
        "last_seen": datetime.utcnow().isoformat()
    }
    redis_client.setex(key, 35, json.dumps(status))  # expires in 35 seconds
    return {"status": "ok"}


@router.get("/chat/{chat_id}/online")
async def get_online_status(chat_id: int):
    key = f"online:{chat_id}"
    data = redis_client.get(key)
    if not data:
        return {"visitor_online": False, "operator_online": False}

    status = json.loads(data)
    is_online = (datetime.utcnow() - datetime.fromisoformat(status["last_seen"])).total_seconds() < 30
    return {
        "visitor_online": is_online and status["role"] == "visitor",
        "operator_online": is_online and status["role"] == "operator"
    }