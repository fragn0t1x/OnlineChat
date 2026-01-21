from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from ..database import SessionLocal, engine
from .. import models, schemas
from ..bot.telegram_bot import notify_new_message
import json
from datetime import datetime
import redis
import os

# Redis
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


@router.get("/chat/start")
def start_chat(db: Session = Depends(get_db)):
    from uuid import uuid4
    session_id = str(uuid4())
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
        db: Session = Depends(get_db)
):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    message = models.Message(
        chat_session_id=chat_id,
        sender="visitor",
        text=text.strip()
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Очищаем статус "печатает" для оператора
    redis_client.delete(f"typing_operator:{chat_id}")

    await notify_new_message(chat_id, text.strip())
    return {"status": "ok"}


@router.post("/chat/{chat_id}/reply")
async def reply_to_chat(
        chat_id: int,
        text: str = Form(None),
        db: Session = Depends(get_db)
):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    message = models.Message(
        chat_session_id=chat_id,
        sender="operator",
        text=text.strip()
    )
    db.add(message)
    db.commit()

    # Очищаем статус "печатает" для посетителя
    redis_client.delete(f"typing_visitor:{chat_id}")
    return {"status": "ok"}


@router.get("/chat/{chat_id}", response_model=schemas.ChatSessionOut)
def get_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(models.ChatSession).filter(models.ChatSession.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = db.query(models.Message).filter(models.Message.chat_session_id == chat_id).all()
    return {"id": chat.id, "messages": messages}


# === ТИПИНГ ===
@router.post("/chat/{chat_id}/typing")
async def set_typing(chat_id: int, role: str = "visitor", is_typing: bool = True):
    key = f"typing_{'operator' if role == 'visitor' else 'visitor'}:{chat_id}"
    if is_typing:
        redis_client.setex(key, 3, "1")
    else:
        redis_client.delete(key)
    return {"status": "ok"}


@router.get("/chat/{chat_id}/typing")
async def get_typing(chat_id: int, role: str = "visitor"):
    key = f"typing_{role}:{chat_id}"
    is_typing = redis_client.exists(key)
    return {"is_typing": bool(is_typing)}


# === ОНЛАЙН ===
@router.post("/chat/{chat_id}/heartbeat")
async def heartbeat(chat_id: int, role: str = "visitor"):
    key = f"online:{chat_id}"
    status = {
        "role": role,
        "last_seen": datetime.utcnow().isoformat()
    }
    redis_client.setex(key, 35, json.dumps(status))
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