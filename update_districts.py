"""
Скрипт для обновления районов у уже сохранённых объектов.
Запуск: python3 update_districts.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from db import init_db, pool
from utils import find_district_by_street


async def update_districts():
    await init_db()
    import db as db_module
    conn_pool = db_module.pool

    async with conn_pool.acquire() as conn:
        # Получаем все объекты без района
        rows = await conn.fetch("""
            SELECT id, address FROM properties 
            WHERE (district IS NULL OR district = '')
            AND address IS NOT NULL AND address != ''
        """)

        print(f"Объектов без района: {len(rows)}")
        updated = 0

        for row in rows:
            address = row['address']
            if not address:
                continue

            district = find_district_by_street(None, address)

            if district:
                await conn.execute("""
                    UPDATE properties SET district = $1 WHERE id = $2
                """, district, row['id'])
                print(f"✅ #{row['id']} {address} → {district}")
                updated += 1
            else:
                print(f"❌ #{row['id']} {address} → не определён")

        print(f"\nОбновлено: {updated} из {len(rows)}")


asyncio.run(update_districts())
