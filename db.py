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


async def get_admin_ids() -> list[int]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT telegram_id FROM admins")
        return [r["telegram_id"] for r in rows]


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

async def save_property(data: dict) -> int:
    """Сохранить объект недвижимости. При повторном парсинге — обновить."""
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            INSERT INTO properties (
                source_channel, message_id, source_code,
                deal_type, property_type, subtype,
                address, district, lat, lon,
                rooms, price, price_season, deposit,
                area, area_land, floor, floors_total,
                heating, features, photos,
                text, media_group_id,
                is_active, published_at
            )
            VALUES (
                $1, $2, $3,
                $4, $5, $6,
                $7, $8, $9, $10,
                $11, $12, $13, $14,
                $15, $16, $17, $18,
                $19, $20, $21,
                $22, $23,
                $24, $25
            )
            ON CONFLICT (source_channel, message_id) DO UPDATE SET
                source_code   = EXCLUDED.source_code,
                deal_type     = EXCLUDED.deal_type,
                property_type = EXCLUDED.property_type,
                address       = EXCLUDED.address,
                district      = EXCLUDED.district,
                lat           = EXCLUDED.lat,
                lon           = EXCLUDED.lon,
                rooms         = EXCLUDED.rooms,
                price         = EXCLUDED.price,
                price_season  = EXCLUDED.price_season,
                deposit       = EXCLUDED.deposit,
                area          = EXCLUDED.area,
                floor         = EXCLUDED.floor,
                floors_total  = EXCLUDED.floors_total,
                heating       = EXCLUDED.heating,
                features      = EXCLUDED.features,
                photos        = EXCLUDED.photos,
                text          = EXCLUDED.text,
                is_active     = EXCLUDED.is_active,
                updated_at    = NOW()
            RETURNING id
        """,
            data.get("source_channel"),
            data.get("message_id"),
            data.get("source_code"),
            data.get("deal_type"),
            data.get("property_type"),
            data.get("subtype"),
            data.get("address"),
            data.get("district"),
            data.get("lat"),
            data.get("lon"),
            data.get("rooms"),
            data.get("price"),
            data.get("price_season"),
            data.get("deposit"),
            data.get("area"),
            data.get("area_land"),
            data.get("floor"),
            data.get("floors_total"),
            data.get("heating", []),
            data.get("features", []),
            data.get("photos", []),
            data.get("text"),
            data.get("media_group_id"),
            data.get("is_active", True),
            data.get("published_at"),
        )


async def update_property_geocode(prop_id: int, district: str | None, lat: float | None, lon: float | None):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE properties SET district = COALESCE($1, district), lat = $2, lon = $3 WHERE id = $4",
            district, lat, lon, prop_id,
        )


async def update_property_photos(prop_id: int, photos: list[str]):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE properties SET photos = $1 WHERE id = $2",
            photos, prop_id,
        )


async def get_last_message_id(channel_id: int) -> int | None:
    """Получить ID последнего сохранённого поста из канала."""
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            SELECT MAX(message_id) FROM properties 
            WHERE source_channel = $1
        """, channel_id)


async def deactivate_property(source_channel: int, message_id: int):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE properties SET is_active = FALSE
            WHERE source_channel = $1 AND message_id = $2
        """, source_channel, message_id)


async def get_property_ids(filters: dict) -> list[int]:
    """Вернуть все ID объектов, подходящих под фильтры (без лимита)."""
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
    if filters.get("address"):
        words = filters["address"].strip().split()
        for word in words:
            if len(word) >= 2:
                conditions.append(f"address ILIKE '%' || ${i} || '%'")
                params.append(word)
                i += 1
    if filters.get("price_min") is not None:
        conditions.append(f"price >= ${i}")
        params.append(filters["price_min"])
        i += 1
    if filters.get("price_max") is not None:
        conditions.append(f"price <= ${i}")
        params.append(filters["price_max"])
        i += 1
    if filters.get("area_min") is not None:
        conditions.append(f"area >= ${i}")
        params.append(filters["area_min"])
        i += 1
    if filters.get("area_max") is not None:
        conditions.append(f"area <= ${i}")
        params.append(filters["area_max"])
        i += 1
    if filters.get("floor_min") is not None:
        conditions.append(f"floor >= ${i}")
        params.append(filters["floor_min"])
        i += 1
    if filters.get("floor_max") is not None:
        conditions.append(f"floor <= ${i}")
        params.append(filters["floor_max"])
        i += 1
    if filters.get("days_depth") is not None:
        conditions.append(f"published_at >= NOW() - (${i} * INTERVAL '1 day')")
        params.append(filters["days_depth"])
        i += 1
    if filters.get("rooms"):
        conditions.append(f"rooms = ANY(${i}::text[])")
        params.append(filters["rooms"])
        i += 1
    if filters.get("property_type"):
        conditions.append(f"property_type = ANY(${i}::text[])")
        params.append(filters["property_type"])
        i += 1
    if filters.get("heating"):
        conditions.append(f"heating && ${i}::text[]")
        params.append(filters["heating"])
        i += 1
    if filters.get("features"):
        conditions.append(f"features && ${i}::text[]")
        params.append(filters["features"])
        i += 1

    where = " AND ".join(conditions)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT id FROM properties WHERE {where} ORDER BY published_at DESC",
            *params,
        )
    return [r["id"] for r in rows]


async def get_properties(filters: dict, offset: int = 0, limit: int = 10) -> list:
    conditions = ["is_active = TRUE"]
    params = []
    i = 1

    # Поиск по конкретным ID
    if filters.get("id_in"):
        conditions = [f"id = ANY(${i})"]
        params.append(filters["id_in"])
        i += 1
        async with pool.acquire() as conn:
            return await conn.fetch(f"""
                SELECT * FROM properties WHERE {' AND '.join(conditions)}
            """, *params)

    if filters.get("deal_type"):
        conditions.append(f"deal_type = ${i}")
        params.append(filters["deal_type"])
        i += 1

    if filters.get("district"):
        conditions.append(f"district = ANY(${i})")
        params.append(filters["district"])
        i += 1

    if filters.get("address"):
        words = filters["address"].strip().split()
        for word in words:
            if len(word) >= 2:
                conditions.append(f"address ILIKE '%' || ${i} || '%'")
                params.append(word)
                i += 1

    if filters.get("price_min") is not None:
        conditions.append(f"price >= ${i}")
        params.append(filters["price_min"])
        i += 1

    if filters.get("price_max") is not None:
        conditions.append(f"price <= ${i}")
        params.append(filters["price_max"])
        i += 1

    if filters.get("area_min") is not None:
        conditions.append(f"area >= ${i}")
        params.append(filters["area_min"])
        i += 1

    if filters.get("area_max") is not None:
        conditions.append(f"area <= ${i}")
        params.append(filters["area_max"])
        i += 1

    if filters.get("floor_min") is not None:
        conditions.append(f"floor >= ${i}")
        params.append(filters["floor_min"])
        i += 1

    if filters.get("floor_max") is not None:
        conditions.append(f"floor <= ${i}")
        params.append(filters["floor_max"])
        i += 1

    if filters.get("days_depth") is not None:
        conditions.append(f"published_at >= NOW() - (${i} * INTERVAL '1 day')")
        params.append(filters["days_depth"])
        i += 1

    if filters.get("rooms"):
        conditions.append(f"rooms = ANY(${i}::text[])")
        params.append(filters["rooms"])
        i += 1

    if filters.get("property_type"):
        conditions.append(f"property_type = ANY(${i}::text[])")
        params.append(filters["property_type"])
        i += 1

    if filters.get("heating"):
        conditions.append(f"heating && ${i}::text[]")
        params.append(filters["heating"])
        i += 1

    if filters.get("features"):
        conditions.append(f"features && ${i}::text[]")
        params.append(filters["features"])
        i += 1

    where = " AND ".join(conditions)
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        return await conn.fetch(f"""
            SELECT * FROM properties
            WHERE {where}
            ORDER BY published_at DESC
            LIMIT ${i} OFFSET ${i + 1}
        """, *params)


# ---------------------------------------------------------------------------
# Filters / Subscriptions
# ---------------------------------------------------------------------------

async def save_filter(user_id: int, data: dict, is_subscription: bool = False):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_filters
                (user_id, deal_type, property_type, district, rooms,
                 price_min, price_max, area_min, area_max,
                 floor_min, floor_max, days_depth,
                 heating, features, is_subscription)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        """,
            user_id,
            data.get("deal_type"),
            data.get("property_type", []),
            data.get("district", []),
            data.get("rooms", []),
            data.get("price_min"),
            data.get("price_max"),
            data.get("area_min"),
            data.get("area_max"),
            data.get("floor_min"),
            data.get("floor_max"),
            data.get("days_depth"),
            data.get("heating", []),
            data.get("features", []),
            is_subscription,
        )


async def get_subscriptions_for_property(prop: dict) -> list:
    """Возвращает telegram_id пользователей чьи подписки совпадают с объектом."""
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT u.telegram_id
            FROM user_filters f
            JOIN users u ON u.id = f.user_id
            WHERE f.is_subscription = TRUE
              AND (f.deal_type IS NULL OR f.deal_type = $1)
              AND (f.district IS NULL OR array_length(f.district, 1) IS NULL OR $2 = ANY(f.district))
              AND (f.price_min IS NULL OR $3 >= f.price_min)
              AND (f.price_max IS NULL OR $3 <= f.price_max)
              AND (f.area_min IS NULL  OR $4 >= f.area_min)
              AND (f.area_max IS NULL  OR $4 <= f.area_max)
              AND (f.floor_min IS NULL OR $5 >= f.floor_min)
              AND (f.floor_max IS NULL OR $5 <= f.floor_max)
              AND (f.heating IS NULL OR array_length(f.heating, 1) IS NULL OR f.heating && $6)
              AND (f.features IS NULL OR array_length(f.features, 1) IS NULL OR f.features && $7)
        """,
            prop.get("deal_type"),
            prop.get("district"),
            prop.get("price"),
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


async def is_favorite_prop(user_id: int, property_id: int) -> bool:
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            "SELECT 1 FROM favorites WHERE user_id = $1 AND property_id = $2",
            user_id, property_id
        )
        return result is not None


async def get_favorites_count(user_id: int) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM favorites f JOIN properties p ON p.id = f.property_id WHERE f.user_id = $1 AND p.is_active = TRUE",
            user_id
        )


async def get_favorites(user_id: int, offset: int = 0, limit: int = 10) -> list:
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT p.* FROM favorites f
            JOIN properties p ON p.id = f.property_id
            WHERE f.user_id = $1 AND p.is_active = TRUE
            ORDER BY f.added_at DESC
            LIMIT $2 OFFSET $3
        """, user_id, limit, offset)


# ---------------------------------------------------------------------------
# Viewings
# ---------------------------------------------------------------------------

async def save_viewing(telegram_id: int, property_id: int, viewing_datetime: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO viewings (telegram_id, property_id, viewing_datetime, status)
            VALUES ($1, $2, $3, 'Назначен')
        """, telegram_id, property_id, viewing_datetime)


async def confirm_rental(telegram_id: int, property_id: int, rental_start: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO viewings (telegram_id, property_id, rental_start, status)
            VALUES ($1, $2, $3, 'Арендовал')
            ON CONFLICT (telegram_id, property_id)
            DO UPDATE SET
                rental_start = EXCLUDED.rental_start,
                status = 'Арендовал'
        """, telegram_id, property_id, rental_start)


async def close_rental(telegram_id: int, property_id: int, rental_end: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE viewings
            SET rental_end = $1, status = 'Сдал'
            WHERE telegram_id = $2 AND property_id = $3
        """, rental_end, telegram_id, property_id)


# ---------------------------------------------------------------------------
# User info
# ---------------------------------------------------------------------------

async def get_user_info(telegram_id: int) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT telegram_id, username, phone, full_name
            FROM users WHERE telegram_id = $1
        """, telegram_id)
        if row:
            return dict(row)
        return {}


# ---------------------------------------------------------------------------
# Google Sheets — логирование
# ---------------------------------------------------------------------------

async def log_to_sheets(telegram_id: int, property_id: int, data: dict):
    # TODO: подключить gspread
    print(f"[Sheets] user={telegram_id} prop={property_id} data={data}")
