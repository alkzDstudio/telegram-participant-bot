import asyncio
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

    # Сортируем и нумеруем
    active = sorted(active)
    unsure = sorted(unsure)
    not_going = sorted(not_going)

    # Форматируем текст
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

# Запуск бота
def main() -> None:
    from dotenv import load_dotenv
    import os

    load_dotenv()

    # Замени на свой токен!
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("BOT_TOKEN not found in .env file")

    # Инициализация БД
    asyncio.run(init_db())

    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запуск бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
