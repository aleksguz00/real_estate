# bot.py

import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from db import init_db
from handlers_user import router as user_router
from handlers_admin import router as admin_router
from handlers_channel import start_parser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def check_single_instance():
    """Проверяет что бот не запущен в другом процессе."""
    import subprocess
    result = subprocess.run(
        ['pgrep', '-f', 'bot.py'],
        capture_output=True, text=True
    )
    pids = [p for p in result.stdout.strip().split('\n') if p and p != str(os.getpid())]
    if pids:
        print(f"❌ Бот уже запущен (PID: {', '.join(pids)}). Остановите его сначала.")
        sys.exit(1)


async def main():
    check_single_instance()
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Роутеры
    dp.include_router(user_router)
    dp.include_router(admin_router)

    # БД
    await init_db()

    # Запускаем парсер каналов
    parser = await start_parser(bot=bot)

    # Загружаем только новые посты которых нет в БД
    asyncio.create_task(parser.fetch_new_posts())

    logger.info("✅ Бот запущен")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await parser.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
