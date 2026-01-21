# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
import os
from .api import chat
from .bot.telegram_bot import start_telegram_bot
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import ChatSession
from datetime import datetime, timedelta

CHAT_INACTIVE_DAYS = int(os.getenv("CHAT_INACTIVE_DAYS", "3"))

async def cleanup_inactive_chats():
    while True:
        await asyncio.sleep(3600)
        cutoff = datetime.utcnow() - timedelta(days=CHAT_INACTIVE_DAYS)
        with SessionLocal() as db:
            db.query(ChatSession).filter(
                ChatSession.updated_at < cutoff,
                ChatSession.is_active == True
            ).update({ChatSession.is_active: False})
            db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        tasks.append(asyncio.create_task(start_telegram_bot()))
    tasks.append(asyncio.create_task(cleanup_inactive_chats()))
    yield
    for t in tasks:
        t.cancel()

app = FastAPI(lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "").split(",")
if origins == [""]:
    origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # ← явно укажите ваш Tilda-сайт
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API
app.include_router(chat.router, prefix="/api")

# Отдаём operator.html по /operator
@app.get("/operator")
async def operator_page():
    return FileResponse("/frontend/operator.html")

@app.get("/support-widget.js")
async def widget_js():
    return FileResponse("/frontend/support-widget.js", media_type="application/javascript")

# Остальные статические файлы (виджет)
app.mount("/", StaticFiles(directory="/frontend", html=True), name="static")