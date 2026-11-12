import os
import sys
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bookstore_project.settings")

import django
django.setup()

from telegram_bot.handlers import start, catalog, orders

BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise ValueError("XATOLIK: .env faylida 'BOT_TOKEN' topilmadi.")

    # Bot FSM xotirasi uchun Redis DB=2 dan foydalanamiz
    redis_client = Redis.from_url(REDIS_URL, db=2)
    storage = RedisStorage(redis=redis_client)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)  # Storage ulandi

    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(orders.router)

    print("Bot va Redis FSM muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
