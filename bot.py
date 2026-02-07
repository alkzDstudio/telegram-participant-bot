import json
import os
from datetime import datetime
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Путь к файлу с участниками
DATA_FILE = "participants.json"

# Админ из .env
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Инициализация данных
def load_data():
    if not os.path.exists(DATA_FILE):
        data = {"events": {}, "admins": [ADMIN_ID]}
        save_data(data)
        return data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                data = {"events": {}, "admins": [ADMIN_ID]}
                save_data(data)
                return data
            data = json.loads(content)

        if ADMIN_ID not in data["admins"]:
            data["admins"].append(ADMIN_ID)
            save_data(data)

        return data
    except json.JSONDecodeError as e:
        print(f"Ошибка чтения JSON: {e}. Создаём новый файл.")
        data = {"events": {}, "admins": [ADMIN_ID]}
        save_data(data)
        return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Проверка: является ли пользователь админом?
def is_admin(user_id: int, data) -> bool:
    return user_id in data["admins"]

# Функция для создания главного меню (для всех)
def get_main_menu(user_id: int, data):
    keyboard = [
        [InlineKeyboardButton("📋 События", callback_data="events_menu")],
    ]
    if is_admin(user_id, data):
        keyboard.append([InlineKeyboardButton("🆕 Создать событие", callback_data="new_event_menu")])
        keyboard.append([InlineKeyboardButton("👥 Добавить админа", callback_data="add_admin_menu")])
    return InlineKeyboardMarkup(keyboard)

# Главная функция — при первом запуске
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    await update.message.reply_text(
        "👋 Привет! Нажми на кнопку ниже, чтобы начать.",
        reply_markup=get_main_menu(user_id, data)
    )

# Функция для получения текста сообщения
async def get_message_text(event_key: str, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    event = data["events"][event_key]
    date_str = event["date"]

    message = f"################\n{date_str}-Кто-готов?\n################\nУчаствуют:\n"

    participants = event["participants"]
    joined = [p for p, status in participants.items() if status == "join"]
    maybe = [p for p, status in participants.items() if status == "maybe"]
    left = [p for p, status in participants.items() if status == "leave"]

    for i, user_id in enumerate(joined, 1):
        try:
            user = await context.bot.get_chat(user_id)
            name = user.first_name
            if user.last_name:
                name += f" {user.last_name}"
            message += f"✅ {i}. {html.escape(name)}\n"
        except Exception as e:
            message += f"✅ {i}. Пользователь (ID: {user_id})\n"

    if maybe:
        message += "\nНе уверены:\n"
        for i, user_id in enumerate(maybe, 1):
            try:
                user = await context.bot.get_chat(user_id)
                name = user.first_name
                if user.last_name:
                    name += f" {user.last_name}"
                message += f"❔ {i}. {html.escape(name)}\n"
            except Exception as e:
                message += f"❔ {i}. Пользователь (ID: {user_id})\n"

    if left:
        message += "\nНе пойдут:\n"
        for i, user_id in enumerate(left, 1):
            try:
                user = await context.bot.get_chat(user_id)
                name = user.first_name
                if user.last_name:
                    name += f" {user.last_name}"
                message += f"🚫 {i}. {html.escape(name)}\n"
            except Exception as e:
                message += f"🚫 {i}. Пользователь (ID: {user_id})\n"

    message += f"{'_' * 20}\nИтого:\n✅ Участвуют: {len(joined)}\n❔ Не уверены: {len(maybe)}\n🚫 Не участвуют: {len(left)}\n################"
    return message

# Обработка нажатий кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = load_data()

    if query.data == "events_menu":
        events = data["events"]
        if not events:
            await query.edit_message_text("❌ Нет созданных событий.")
            return

        message = "📋 Список событий:\n"
        keyboard = []

        for key, event in events.items():
            date_str = event["date"]
            row = [InlineKeyboardButton(f"🔹 {date_str}", callback_data=f"refresh_{key}")]
            if is_admin(user_id, data):
                row.append(InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{key}"))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "new_event_menu":
        if not is_admin(user_id, data):
            await query.edit_message_text("❌ У вас нет прав на создание события.")
            return
        await query.edit_message_text(
            "Введите дату события в формате:\n\nДень-ДД-ММ-ГГГГ\n\nПример: Воскресенье-08-02-2026",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]])
        )
        context.user_data["waiting_for_date"] = True

    elif query.data == "add_admin_menu":
        if not is_admin(user_id, data):
            await query.edit_message_text("❌ У вас нет прав на добавление админов.")
            return
        await query.edit_message_text(
            "Отправь user_id нового админа.\n\nПример: 123456789",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]])
        )
        context.user_data["waiting_for_admin_id"] = True

    elif query.data == "back_to_main":
        await query.edit_message_text("👋 Выберите действие:", reply_markup=get_main_menu(user_id, data))

    elif query.data.startswith("join_"):
        event_key = query.data.split("_", 1)[1]
        event = data["events"][event_key]
        user_id = query.from_user.id
        participants = event["participants"]

        if user_id in participants:
            old_status = participants[user_id]
            if old_status == "join":
                del participants[user_id]
            elif old_status == "maybe":
                del participants[user_id]
            elif old_status == "leave":
                del participants[user_id]
            else:
                participants[user_id] = "join"
        else:
            participants[user_id] = "join"

        save_data(data)

        try:
            await update.callback_query.edit_message_text(
                text=await get_message_text(event_key, context),
                reply_markup=get_keyboard(event_key),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            if "Message is not modified" in str(e):
                await update.callback_query.answer("✅ Статус уже обновлён.")
            else:
                print(f"Не удалось обновить сообщение: {e}")
                await update.message.reply_text(
                    await get_message_text(event_key, context),
                    reply_markup=get_keyboard(event_key),
                    parse_mode=ParseMode.HTML
                )

    elif query.data.startswith("maybe_"):
        event_key = query.data.split("_", 1)[1]
        event = data["events"][event_key]
        user_id = query.from_user.id
        participants = event["participants"]

        if user_id in participants:
            old_status = participants[user_id]
            if old_status == "join":
                del participants[user_id]
            elif old_status == "maybe":
                del participants[user_id]
            elif old_status == "leave":
                del participants[user_id]
            else:
                participants[user_id] = "maybe"
        else:
            participants[user_id] = "maybe"

        save_data(data)

        try:
            await update.callback_query.edit_message_text(
                text=await get_message_text(event_key, context),
                reply_markup=get_keyboard(event_key),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            if "Message is not modified" in str(e):
                await update.callback_query.answer("✅ Статус уже обновлён.")
            else:
                print(f"Не удалось обновить сообщение: {e}")
                await update.message.reply_text(
                    await get_message_text(event_key, context),
                    reply_markup=get_keyboard(event_key),
                    parse_mode=ParseMode.HTML
                )

    elif query.data.startswith("leave_"):
        event_key = query.data.split("_", 1)[1]
        event = data["events"][event_key]
        user_id = query.from_user.id
        participants = event["participants"]

        if user_id in participants:
            old_status = participants[user_id]
            if old_status == "join":
                del participants[user_id]
            elif old_status == "maybe":
                del participants[user_id]
            elif old_status == "leave":
                del participants[user_id]
            else:
                participants[user_id] = "leave"
        else:
            participants[user_id] = "leave"

        save_data(data)

        try:
            await update.callback_query.edit_message_text(
                text=await get_message_text(event_key, context),
                reply_markup=get_keyboard(event_key),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            if "Message is not modified" in str(e):
                await update.callback_query.answer("✅ Статус уже обновлён.")
            else:
                print(f"Не удалось обновить сообщение: {e}")
                await update.message.reply_text(
                    await get_message_text(event_key, context),
                    reply_markup=get_keyboard(event_key),
                    parse_mode=ParseMode.HTML
                )

    elif query.data.startswith("refresh_"):
        event_key = query.data.split("_", 1)[1]
        await send_event_message(update, event_key, context)

    elif query.data.startswith("delete_"):
        event_key = query.data.split("_", 1)[1]
        event = data["events"][event_key]
        date_str = event["date"]

        if not is_admin(user_id, data):
            await query.edit_message_text("❌ У вас нет прав на удаление события.")
            return

        del data["events"][event_key]
        save_data(data)

        await query.edit_message_text(
            f"✅ Событие '{date_str}' удалено.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]])
        )

# Обработка текста (ввод даты или user_id)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()

    if "waiting_for_date" in context.user_data:
        date_str = update.message.text.strip()
        if not date_str:
            await update.message.reply_text("❌ Неверный формат. Попробуй снова.")
            return
        event_key = date_str.replace(" ", "-").lower()
        if event_key in data["events"]:
            await update.message.reply_text(f"❌ Событие уже существует: {date_str}")
            return
        data["events"][event_key] = {
            "date": date_str,
            "participants": {},
            "created_at": datetime.now().isoformat()
        }
        save_data(data)
        await update.message.reply_text(
            f"✅ Событие создано: {date_str}\nТеперь участники могут подтвердить своё участие.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]])
        )
        context.user_data.pop("waiting_for_date", None)

    elif "waiting_for_admin_id" in context.user_data:
        try:
            new_admin_id = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text("❌ Неверный формат. Отправь число.")
            return
        if new_admin_id in data["admins"]:
            await update.message.reply_text("❗ Этот пользователь уже админ.")
            return
        data["admins"].append(new_admin_id)
        save_data(data)
        await update.message.reply_text(
            f"✅ Пользователь {new_admin_id} теперь админ.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]])
        )
        context.user_data.pop("waiting_for_admin_id", None)

# Отправка сообщения с кнопками (обновляет существующее)
async def send_event_message(update: Update, event_key: str, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.callback_query.edit_message_text(
            text=await get_message_text(event_key, context),
            reply_markup=get_keyboard(event_key),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        if "Message is not modified" in str(e):
            await update.callback_query.answer("✅ Статус уже обновлён.")
        else:
            print(f"Не удалось обновить сообщение: {e}")
            await update.message.reply_text(
                await get_message_text(event_key, context),
                reply_markup=get_keyboard(event_key),
                parse_mode=ParseMode.HTML
            )

def get_keyboard(event_key):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Участвую", callback_data=f"join_{event_key}"),
         InlineKeyboardButton("❔ Не уверен", callback_data=f"maybe_{event_key}")],
        [InlineKeyboardButton("🚫 Не пойду", callback_data=f"leave_{event_key}"),
         InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{event_key}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ])

# Запуск бота
def main():
    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
