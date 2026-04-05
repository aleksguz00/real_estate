import asyncpg
from asyncpg import Pool
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

pool: Pool | None = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


async def get_user_id(telegram_id):
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )


async def save_user(telegram_id):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id)
            VALUES ($1)
            ON CONFLICT (telegram_id) DO NOTHING
        """, telegram_id)


async def save_filter(user_id, data):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_filters
            (user_id, deal_type, district, area_from, area_to, floor_from, floor_to, days_depth)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)    
        """, *data)