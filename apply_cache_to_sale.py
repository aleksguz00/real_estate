import asyncio, asyncpg, json

async def main():
    with open('/Users/fixdive/real_estate/district_cache.json') as f:
        cache = json.load(f)

    conn = await asyncpg.connect(
        host='localhost', database='real_estate', user='postgres'
    )

    updated = 0
    skipped = 0

    for address, district in cache.items():
        if not district:
            skipped += 1
            continue
        result = await conn.execute(
            "UPDATE properties SET district=$1 WHERE address=$2 AND deal_type='sale'",
            district, address
        )
        count = int(result.split()[-1])
        if count > 0:
            updated += count
            print(f"{address} → {district}")

    await conn.close()
    print(f"\nОбновлено: {updated}")
    print(f"Без района (пропущено): {skipped}")

asyncio.run(main())
