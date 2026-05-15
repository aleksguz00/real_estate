# bot.py

import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent

from config import BOT_TOKEN
from db import init_db
from handlers_user import router as user_router
from handlers_admin import router as admin_router
from handlers_channel import start_parser
from reminder_scheduler import check_reminders

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

    @dp.error()
    async def errors_handler(event: ErrorEvent):
        import traceback
        exception = event.exception
        error_msg = f"❌ Ошибка в боте:\n\n{type(exception).__name__}: {str(exception)[:500]}"
        logger.error(f"Bot error: {exception}\n{traceback.format_exc()}")
        try:
            await bot.send_message(chat_id=7572451975, text=error_msg[:4000])
        except:
            pass
        return True

    # Роутеры
    dp.include_router(user_router)
    dp.include_router(admin_router)

    # БД
    await init_db()

    # Запускаем парсер каналов
    parser = await start_parser(bot=bot)

    # Загружаем только новые посты которых нет в БД
    asyncio.create_task(parser.fetch_new_posts())

    # Планировщик напоминаний о просмотрах
    asyncio.create_task(check_reminders(bot))

    logger.info("✅ Бот запущен")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logging.error(f"Polling error: {e}")
    finally:
        await parser.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
