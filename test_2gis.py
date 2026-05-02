import asyncio, aiohttp, asyncpg, json

API_KEY = "91e07e8c-868f-425f-ba4a-7b2c8a506252"

async def main():
    # Подключение к БД
    conn = await asyncpg.connect(
        host="localhost", database="real_estate", user="postgres"
    )

    # Берём 10 случайных адресов аренды за 60 дней
    rows = await conn.fetch("""
        SELECT id, address, district
        FROM properties
        WHERE deal_type = 'rent'
        AND published_at >= NOW() - INTERVAL '60 days'
        AND address IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 10
    """)
    await conn.close()

    async with aiohttp.ClientSession() as s:
        for row in rows:
            address = row['address']
            current_district = row['district']

            # Запрос к 2GIS
            params = {
                "q": f"{address} Батуми Грузия",
                "fields": "items.adm_div,items.address,items.point",
                "key": API_KEY
            }
            async with s.get(
                "https://catalog.api.2gis.com/3.0/items/geocode",
                params=params
            ) as r:
                data = await r.json()

            # Выводим полный ответ для анализа
            items = data.get("result", {}).get("items", [])
            if items:
                item = items[0]
                adm_div = item.get("adm_div", [])
                point = item.get("point", {})
                print(f"\nАдрес: {address}")
                print(f"Текущий район в БД: {current_district}")
                print(f"Координаты: {point}")
                print(f"adm_div от 2GIS:")
                for a in adm_div:
                    print(f"  type={a.get('type')} name={a.get('name')}")
            else:
                print(f"\nАдрес: {address}")
                print(f"2GIS: НЕ НАЙДЕН")

            await asyncio.sleep(0.5)

asyncio.run(main())
