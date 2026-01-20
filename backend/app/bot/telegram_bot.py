import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPERATOR_CHAT_IDS = list(map(int, os.getenv("OPERATOR_CHAT_IDS", "").split(",")))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "http://localhost:8000")

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message()
async def cmd_start(message: types.Message):
    await message.answer("✅ Бот поддержки запущен.")

async def start_telegram_bot():
    await dp.start_polling(bot)

async def notify_new_message(chat_id: int, text: str):
    # Ссылка на ваш операторский интерфейс
    web_app_url = f"{WEBHOOK_HOST}/operator?chat_id={chat_id}"

    # Создаём кнопку Web App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Открыть чат",
            web_app=WebAppInfo(url=web_app_url)
        )]
    ])

    for op_id in OPERATOR_CHAT_IDS:
        await bot.send_message(
            op_id,
            f"📩 Новое сообщение:\n\n{text}\n\nЧат ID: {chat_id}",
            reply_markup=keyboard
        )