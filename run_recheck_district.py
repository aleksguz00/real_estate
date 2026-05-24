import asyncio, json
import db
from utils import geocode_2gis, normalize_address, _load_gis_cache, _save_gis_cache

TARGET = "Джавахишвили"
MAX_API_CALLS = 90

async def main():
    await db.init_db()
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, address FROM properties "
            "WHERE district=$1 AND is_active=TRUE "
            "AND deal_type='rent' AND address IS NOT NULL ORDER BY id",
            TARGET
        )
    print(f"{TARGET} (аренда): {len(rows)}")

    manual = json.load(open('/root/kaufman_estate/district_cache.json'))
    gis_cache = _load_gis_cache()
    changed = 0; processed = 0; api_calls = 0; consecutive_none = 0

    for r in rows:
        addr = r["address"]; norm = normalize_address(addr); processed += 1
        if norm in manual and manual[norm]:
            continue
        if norm in gis_cache and gis_cache[norm]:
            district = gis_cache[norm]
        else:
            if api_calls >= MAX_API_CALLS:
                print(f"Достигнут потолок {MAX_API_CALLS} вызовов. Стоп на {processed}.")
                break
            district = await geocode_2gis(addr)
            api_calls += 1
            gis_cache[norm] = district
            _save_gis_cache(gis_cache)
            await asyncio.sleep(0.3)
            consecutive_none = consecutive_none + 1 if district is None else 0
            if consecutive_none >= 40:
                print(f"!!! 40 None подряд — возможно лимит. Стоп на {processed}.")
                break
        if district and district != TARGET:
            async with db.pool.acquire() as conn:
                await conn.execute("UPDATE properties SET district=$1 WHERE id=$2", district, r["id"])
            changed += 1
            print(f"  id={r['id']} {addr!r}: {TARGET} -> {district}")
        if processed % 20 == 0:
            print(f"Обработано {processed}/{len(rows)} | изменено {changed} | API {api_calls}")

    print(f"ИТОГО: обработано {processed}, изменено {changed}, вызовов 2ГИС {api_calls}")

asyncio.run(main())
