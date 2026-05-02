import asyncio, aiohttp

async def main():
    url = "https://overpass-api.de/api/interpreter"
    query = """
[out:json];
area["name"="Batumi"]->.batumi;
way["highway"]["name:ru"](area.batumi);
out tags;
"""
    async with aiohttp.ClientSession() as s:
        async with s.post(url, data={"data": query}) as r:
            data = await r.json()
            streets = set()
            for el in data.get("elements", []):
                name = el.get("tags", {}).get("name:ru")
                if name:
                    streets.add(name.lower())
            print(f"Найдено улиц: {len(streets)}")
            for street in sorted(streets):
                print(street)

asyncio.run(main())
