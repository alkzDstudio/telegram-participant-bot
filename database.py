import aiosqlite
import asyncio

DB_PATH = "participants.db"

async def init_db():
    """Инициализирует базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                chat_id INTEGER,
                user_id INTEGER,
                status TEXT,
                name TEXT,
                date TEXT,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        await db.commit()
    print("База данных инициализирована.")

async def save_state(chat_id: int, participants: dict):
    """Сохраняет состояние в БД"""
    async with aiosqlite.connect(DB_PATH) as db:
        for user_id, info in participants.items():
            await db.execute("""
                INSERT OR REPLACE INTO participants (chat_id, user_id, status, name, date)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, user_id, info["status"], info["name"], "Четверг-22-01-2026"))
        await db.commit()

async def load_state(chat_id: int) -> dict:
    """Загружает состояние из БД"""
    participants = {}
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, status, name FROM participants WHERE chat_id = ?", (chat_id,)) as cursor:
            async for row in cursor:
                user_id, status, name = row
                participants[user_id] = {"status": status, "name": name}
    return participants
