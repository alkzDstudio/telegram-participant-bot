# bot.py

import asyncio
import logging
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import init_db, save_state, load_state

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные
STATE: Dict[int, Dict] = {}

# Статусы
STATUS_ACTIVE = "active"
STATUS_UNSURE = "unsure"
STATUS_NOT_GOING = "not_going"

# Статусы как строки (для кнопок)
STATUS_MAP = {
    "active": "✅ Участвуют",
    "unsure": "❔ Не уверены",
    "not_going": "🚫 Не пойдут"
}

# Список кнопок
def get_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с кнопками"""
    state = STATE.get(chat_id, {})
    user_id = state.get("user_id")
    status = state.get("status", "active")

    buttons = [
        [InlineKeyboardButton("✅ Участвую", callback_data="action:active")],
        [InlineKeyboardButton("❔ Не уверен", callback_data="action:unsure")],
        [InlineKeyboardButton("🚫 Не пойду", callback_data="action:not_going")],
    ]
    return InlineKeyboardMarkup(buttons)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user

    # Загружаем состояние из БД
    participants = await load_state(chat_id)
    STATE[chat_id] = {
        "date": "Четверг-22-01-2026",
        "participants": participants,
        "user_id": user.id,
        "user_name": user.full_name,
    }

    # Отправляем сообщение
    await update.message.reply_text(
        "Выберите, как вы будете участвовать:"
    )
    await update.message.reply_text(
        text=get_status_text(chat_id),
        reply_markup=get_keyboard(chat_id),
        parse_mode="MarkdownV2"
    )

# Обработка нажатий на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_id = query.from_user.id
    data = query.data

    if not data.startswith("action:"):
        return

    action = data.split(":")[1]

    # Получаем текущее состояние
    state = STATE.get(chat_id, {})
    participants = state.get("participants", {})

    # Обновляем статус пользователя
    participants[user_id] = {
        "name": query.from_user.full_name,
        "status": action,
        "timestamp": asyncio.get_event_loop().time()
    }

    STATE[chat_id]["participants"] = participants

    # Сохраняем в БД
    await save_state(chat_id, participants)

    # Обновляем сообщение
    await query.edit_message_text(
        text=get_status_text(chat_id),
        reply_markup=get_keyboard(chat_id),
        parse_mode="MarkdownV2"
    )

# Форматирует текст с участниками
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

# ✅ ОСНОВНАЯ ФУНКЦИЯ — ВСЕГДА ИСПОЛЬЗУЙ asyncio.run()
async def main() -> None:
    from dotenv import load_dotenv
    import os

    load_dotenv()

    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("BOT_TOKEN not found in .env file")

    # Инициализация БД
    await init_db()

    # Создаём приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота
    print("Бот запущен...")
    await application.run_polling()

# ✅ ЗАПУСК — ВСЕГДА ТАК!
if __name__ == "__main__":
    asyncio.run(main())
