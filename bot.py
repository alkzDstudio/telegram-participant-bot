# bot.py

import asyncio
import logging
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.ext import Application, MessageHandler, filters
from database import init_db, save_state, load_state

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

STATE: Dict[int, Dict] = {}

STATUS_ACTIVE = "active"
STATUS_UNSURE = "unsure"
STATUS_NOT_GOING = "not_going"

STATUS_MAP = {
    "active": "✅ Участвуют",
    "unsure": "❔ Не уверены",
    "not_going": "🚫 Не пойдут"
}

def get_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    state = STATE.get(chat_id, {})
    user_id = state.get("user_id")
    status = state.get("status", "active")

    buttons = [
        [InlineKeyboardButton("✅ Участвую", callback_data="action:active")],
        [InlineKeyboardButton("❔ Не уверен", callback_data="action:unsure")],
        [InlineKeyboardButton("🚫 Не пойду", callback_data="action:not_going")],
    ]
    return InlineKeyboardMarkup(buttons)

async def initialize():
    # Set up resources
    pass
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user

    participants = await load_state(chat_id)
    STATE[chat_id] = {
        "date": "Четверг-22-01-2026",
        "participants": participants,
        "user_id": user.id,
        "user_name": user.full_name,
    }

    await update.message.reply_text("Выберите, как вы будете участвовать:")
    await update.message.reply_text(
        text=get_status_text(chat_id),
        reply_markup=get_keyboard(chat_id),
        parse_mode="MarkdownV2"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_id = query.from_user.id
    data = query.data

    if not data.startswith("action:"):
        return

    action = data.split(":")[1]

    state = STATE.get(chat_id, {})
    participants = state.get("participants", {})

    participants[user_id] = {
        "name": query.from_user.full_name,
        "status": action,
        "timestamp": asyncio.get_event_loop().time()
    }

    STATE[chat_id]["participants"] = participants

    await save_state(chat_id, participants)

    await query.edit_message_text(
        text=get_status_text(chat_id),
        reply_markup=get_keyboard(chat_id),
        parse_mode="MarkdownV2"
    )

def get_status_text(chat_id: int) -> str:
    state = STATE.get(chat_id, {})
    date = state.get("date", "Не указано")
    participants = state.get("participants", {})

    active: List[str] = []
    unsure: List[str] = []
    not_going: List[str] = []

    for user_id, info in participants.items():
        name = info["name"]
        status = info["status"]
        if status == "active":
            active.append(name)
        elif status == "unsure":
            unsure.append(name)
        elif status == "not_going":
            not_going.append(name)

    active = sorted(active)
    unsure = sorted(unsure)
    not_going = sorted(not_going)

    lines = [
        f"#{date}-Кто-готов?",
        "################",
        "Участвуют:",
    ]
    for i, name in enumerate(active, 1):
        lines.append(f"✅ {i}. {name}")

    if unsure:
        lines.append("")
        lines.append("Не уверены:")
        for i, name in enumerate(unsure, 1):
            lines.append(f"❔ {i}. {name}")

    if not_going:
        lines.append("")
        lines.append("Не пойдут:")
        for i, name in enumerate(not_going, 1):
            lines.append(f"🚫 {i}. {name}")

    lines.append("################")
    lines.append(f"Итого:")
    lines.append(f"✅ Участвуют: {len(active)}")
    lines.append(f"❔ Не уверены: {len(unsure)}")
    lines.append(f"🚫 Не участвуют: {len(not_going)}")

    return "\n".join(lines)

async def run_bot() -> None:
    from dotenv import load_dotenv
    import os

    load_dotenv()

    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("BOT_TOKEN not found in .env file")

    await init_db()

    # Создаём приложение через ApplicationBuilder
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    await app.initialize()
    await app.start()
    await app.run_polling(stop_signals=None)

    print("Бот запущен...")
    
async def main():
    await initialize()
    await run_bot()
    
if __name__ == "__main__":
    asyncio.run(main())
