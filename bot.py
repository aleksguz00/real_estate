import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import init_db
from handlers_user import router as user_router


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    await init_db()

    dp.include_router(user_router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())