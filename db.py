import asyncpg
from asyncpg import Pool
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

pool: Pool | None = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def get_user_id(telegram_id: int) -> int | None:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )


async def save_user(telegram_id: int, username: str | None = None):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, username)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO UPDATE SET
                username = EXCLUDED.username
        """, telegram_id, username)


async def save_phone(telegram_id: int, phone: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE users SET phone = $1 WHERE telegram_id = $2
        """, phone, telegram_id)


# ---------------------------------------------------------------------------
# Admins
# ---------------------------------------------------------------------------

async def is_admin(telegram_id: int) -> bool:
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            "SELECT 1 FROM admins WHERE telegram_id = $1",
            telegram_id
        )
        return result is not None


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

async def save_property(data: dict) -> int:
    """Сохраняет объект. При повторном парсинге (редактирование поста) - обновляет."""
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            INSERT INTO properties
                (source_channel, message_id, deal_type, subtype, district,
                 area, floor, heating, features, text, media_group_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (source_channel, message_id) DO UPDATE SET
                deal_type    = EXCLUDED.deal_type,
                subtype      = EXCLUDED.subtype,
                district     = EXCLUDED.district,
                area         = EXCLUDED.area,
                floor        = EXCLUDED.floor,
                heating      = EXCLUDED.heating,
                features     = EXCLUDED.features,
                text         = EXCLUDED.text,
                is_active    = TRUE
            RETURNING id
        """,
            data["source_channel"],
            data["message_id"],
            data.get("deal_type"),
            data.get("subtype"),
            data.get("district"),
            data.get("area"),
            data.get("floor"),
            data.get("heating", []),
            data.get("features", []),
            data.get("text"),
            data.get("media_group_id"),
        )


async def deactivate_property(source_channel: int, message_id: int):
    """Помечает объект неактивным (пост содержит 'Сдано!', 'Продано!' и т.п.)."""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE properties SET is_active = FALSE
            WHERE source_channel = $1 AND message_id = $2
        """, source_channel, message_id)


async def get_properties(filters: dict, offset: int = 0, limit: int = 10) -> list:
    """Поиск объектов по фильтрам с пагинацией."""
    conditions = ["is_active = TRUE"]
    params = []
    i = 1

    if filters.get("deal_type"):
        conditions.append(f"deal_type = ${i}")
        params.append(filters["deal_type"])
        i += 1

    if filters.get("district"):
        conditions.append(f"district = ANY(${i})")
        params.append(filters["district"])
        i += 1

    if filters.get("area_from") is not None:
        conditions.append(f"area >= ${i}")
        params.append(filters["area_from"])
        i += 1

    if filters.get("area_to") is not None:
        conditions.append(f"area <= ${i}")
        params.append(filters["area_to"])
        i += 1

    if filters.get("floor_from") is not None:
        conditions.append(f"floor >= ${i}")
        params.append(filters["floor_from"])
        i += 1

    if filters.get("floor_to") is not None:
        conditions.append(f"floor <= ${i}")
        params.append(filters["floor_to"])
        i += 1

    if filters.get("days_depth") is not None:
        conditions.append(f"created_at >= NOW() - (${i} * INTERVAL '1 day')")
        params.append(filters["days_depth"])
        i += 1

    if filters.get("heating"):
        conditions.append(f"heating && ${i}")
        params.append(filters["heating"])
        i += 1

    if filters.get("features"):
        conditions.append(f"features && ${i}")
        params.append(filters["features"])
        i += 1

    where = " AND ".join(conditions)
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        return await conn.fetch(f"""
            SELECT * FROM properties
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${i} OFFSET ${i + 1}
        """, *params)


# ---------------------------------------------------------------------------
# Filters / Subscriptions
# ---------------------------------------------------------------------------

async def save_filter(user_id: int, data: dict, is_subscription: bool = False):
    """
    Сохраняет фильтр.
    is_subscription=False - разовый поиск.
    is_subscription=True  - автопоиск (подписка на уведомления).
    """
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_filters
                (user_id, deal_type, district, area_from, area_to,
                 floor_from, floor_to, days_depth, heating, features, is_subscription)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
            user_id,
            data.get("deal_type"),
            data.get("district", []),
            data.get("area_from"),
            data.get("area_to"),
            data.get("floor_from"),
            data.get("floor_to"),
            data.get("days_depth"),
            data.get("heating", []),
            data.get("features", []),
            is_subscription,
        )


async def get_subscriptions_for_property(prop: dict) -> list:
    """
    Возвращает telegram_id пользователей, чьи подписки совпадают с новым объектом.
    Используется при парсинге нового поста для рассылки уведомлений.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT u.telegram_id
            FROM user_filters f
            JOIN users u ON u.id = f.user_id
            WHERE f.is_subscription = TRUE
              AND (f.deal_type IS NULL OR f.deal_type = $1)
              AND (f.district IS NULL   OR array_length(f.district, 1) IS NULL OR $2 = ANY(f.district))
              AND (f.area_from IS NULL  OR $3 >= f.area_from)
              AND (f.area_to IS NULL    OR $3 <= f.area_to)
              AND (f.floor_from IS NULL OR $4 >= f.floor_from)
              AND (f.floor_to IS NULL   OR $4 <= f.floor_to)
              AND (f.heating IS NULL    OR array_length(f.heating, 1) IS NULL  OR f.heating && $5)
              AND (f.features IS NULL   OR array_length(f.features, 1) IS NULL OR f.features && $6)
        """,
            prop.get("deal_type"),
            prop.get("district"),
            prop.get("area"),
            prop.get("floor"),
            prop.get("heating", []),
            prop.get("features", []),
        )


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------

async def add_to_favorites(user_id: int, property_id: int):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO favorites (user_id, property_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """, user_id, property_id)


async def remove_from_favorites(user_id: int, property_id: int):
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM favorites WHERE user_id = $1 AND property_id = $2
        """, user_id, property_id)


async def get_favorites(user_id: int, offset: int = 0, limit: int = 10) -> list:
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT p.* FROM favorites f
            JOIN properties p ON p.id = f.property_id
            WHERE f.user_id = $1 AND p.is_active = TRUE
            ORDER BY f.added_at DESC
            LIMIT $2 OFFSET $3
        """, user_id, limit, offset)
