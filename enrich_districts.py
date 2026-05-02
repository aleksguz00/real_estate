import asyncio, aiohttp, asyncpg, json
from pathlib import Path

API_KEY   = "91e07e8c-868f-425f-ba4a-7b2c8a506252"
CACHE_FILE  = "/Users/fixdive/real_estate/district_cache.json"
MISSED_FILE = "/Users/fixdive/real_estate/missed_districts.txt"

GEO_TO_RU = {
    "ძველი ბათუმი":   "Старый Батуми",
    "ხიმშიაშვილი":    "Химшиашвили",
    "რუსთაველი":      "Руставели",
    "ბაგრატიონი":     "Багратиони",
    "აღმაშენებელი":   "Агмашенебели",
    "ჯავახიშვილი":    "Джавахишвили",
    "თამარი":         "Тамар",
    "ბონი დასახლება": "Бони Городок",
    "აეროპორტი":      "Аэропорт",
    "ყაჩაბეთი":       "Кахабери",
    "მახინჯაური":     "Махинджаури",
}


def load_cache() -> dict:
    p = Path(CACHE_FILE)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


async def geocode(session: aiohttp.ClientSession, address: str) -> str | None:
    """Вернуть русское название района или None."""
    params = {
        "q": f"{address} Батуми Грузия",
        "fields": "items.adm_div",
        "key": API_KEY,
    }
    try:
        async with session.get(
            "https://catalog.api.2gis.com/3.0/items/geocode",
            params=params,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            data = await r.json()
    except Exception as e:
        print(f"  [HTTP ERROR] {address}: {e}")
        return None

    items = data.get("result", {}).get("items", [])
    if not items:
        return None

    adm_div = items[0].get("adm_div", [])
    geo_district = next(
        (a["name"] for a in adm_div if a.get("type") == "district"),
        None,
    )
    if not geo_district:
        return None

    return GEO_TO_RU.get(geo_district)


async def main():
    conn = await asyncpg.connect(
        host="localhost", database="real_estate", user="postgres"
    )

    rows = await conn.fetch("""
        SELECT id, address
        FROM properties
        WHERE deal_type = 'rent'
          AND published_at < NOW() - INTERVAL '60 days'
          AND address IS NOT NULL
        ORDER BY id
    """)

    print(f"Всего объектов: {len(rows)}")

    cache = load_cache()
    missed: list[str] = []

    total     = len(rows)
    found     = 0
    not_found = 0
    api_calls = 0

    async with aiohttp.ClientSession() as session:
        for i, row in enumerate(rows, 1):
            prop_id = row["id"]
            address = row["address"]

            if address in cache:
                district = cache[address]
            else:
                district = await geocode(session, address)
                api_calls += 1
                cache[address] = district  # None тоже кэшируем — чтобы не запрашивать повторно
                save_cache(cache)
                await asyncio.sleep(0.5)

            if district:
                await conn.execute(
                    "UPDATE properties SET district = $1 WHERE id = $2",
                    district, prop_id,
                )
                found += 1
            else:
                not_found += 1
                if address not in missed:
                    missed.append(address)

            if i % 10 == 0 or i == total:
                print(
                    f"Обработано {i}/{total} | "
                    f"Найдено {found} | "
                    f"Не найдено {not_found} | "
                    f"Запросов к API: {api_calls}"
                )

    await conn.close()

    with open(MISSED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(missed))

    print(f"\nГотово!")
    print(f"  Обновлено:   {found}")
    print(f"  Не найдено:  {not_found} → {MISSED_FILE}")
    print(f"  API запросов: {api_calls}")
    print(f"  Кэш:         {CACHE_FILE}")


asyncio.run(main())
