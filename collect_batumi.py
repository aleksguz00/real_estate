import asyncio, aiohttp, json

API_KEY = "91e07e8c-868f-425f-ba4a-7b2c8a506252"

GRID_POINTS = [
    (41.6509, 41.6361), (41.6509, 41.6261), (41.6509, 41.6161),
    (41.6459, 41.6461), (41.6459, 41.6361), (41.6459, 41.6261), (41.6459, 41.6161),
    (41.6409, 41.6561), (41.6409, 41.6461), (41.6409, 41.6361), (41.6409, 41.6261),
    (41.6359, 41.6561), (41.6359, 41.6461), (41.6359, 41.6361), (41.6359, 41.6261),
    (41.6309, 41.6561), (41.6309, 41.6461), (41.6309, 41.6361),
    (41.6259, 41.6461), (41.6259, 41.6361), (41.6259, 41.6261),
    (41.6159, 41.6361), (41.6159, 41.6261), (41.6109, 41.6261),
    (41.6759, 41.6961), (41.6809, 41.6961),
]

# Georgian district names → Russian
GEO_TO_RU_DISTRICT = {
    "ხიმშიაშვილი":    "Химшиашвили",
    "რუსთაველი":      "Руставели",
    "ბაგრატიონი":     "Багратиони",
    "აღმაშენებელი":   "Агмашенебели",
    "ჯავახიშვილი":    "Джавахишвили",
    "თამარი":         "Тамар",
    "თამარ":          "Тамар",
    "ბონი":           "Бони Городок",
    "ბონი ქალაქი":    "Бони Городок",
    "აეროპორტი":      "Аэропорт",
    "ყაჩახაბერი":     "Кахабери",
    "კახაბერი":       "Кахабери",
    "მახინჯაური":     "Махинджаური",
    "ძველი ბათუმი":   "Старый Батуми",
    "ბათუმი":         "Старый Батуми",  # fallback for city center
}

async def fetch_buildings(session, lat, lon):
    url = "https://catalog.api.2gis.com/3.0/items"
    params = {
        "q": "дом",
        "location": f"{lon},{lat}",
        "radius": 600,
        "type": "building",
        "page_size": 50,
        "key": API_KEY,
        "fields": "items.adm_div,items.address,items.point",
        "lang": "ru"
    }
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            return await r.json()
    except Exception as e:
        print(f"  Ошибка: {e}")
        return {}

def parse_street_house(addr: dict):
    """Extract street name and house number from address components."""
    components = addr.get("components", [])
    for comp in components:
        if comp.get("type") == "street_number":
            street = comp.get("street", "").strip()
            house  = comp.get("number", "").strip()
            if street and house:
                return street, house
    return "", ""

def map_district(adm_div: list) -> str:
    """Map Georgian district name to Russian."""
    district_geo = next(
        (a["name"] for a in adm_div if a.get("type") == "district"),
        ""
    )
    return GEO_TO_RU_DISTRICT.get(district_geo, "")

async def main():
    results = []
    seen = set()
    total_requests = 0
    unknown_districts = set()

    async with aiohttp.ClientSession() as s:
        for lat, lon in GRID_POINTS:
            data = await fetch_buildings(s, lat, lon)
            total_requests += 1

            items = data.get("result", {}).get("items", [])
            for item in items:
                adm   = item.get("adm_div", [])
                addr  = item.get("address", {})
                point = item.get("point", {})

                street, house = parse_street_house(addr)
                district = map_district(adm)

                # Track unmapped Georgian district names for debugging
                if not district:
                    geo_district = next(
                        (a["name"] for a in adm if a.get("type") == "district"), ""
                    )
                    if geo_district:
                        unknown_districts.add(geo_district)

                if street and house and district:
                    key = f"{street}_{house}"
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "street": street.lower().strip(),
                            "house": house.strip(),
                            "district": district,
                            "lat": point.get("lat", ""),
                            "lon": point.get("lon", ""),
                        })

            print(f"Точка ({lat:.4f},{lon:.4f}): {len(items)} объектов | Запросов: {total_requests} | Всего: {len(results)}")
            await asyncio.sleep(0.3)

    if unknown_districts:
        print(f"\n⚠️  Неизвестные районы (нет маппинга): {unknown_districts}")

    output = "/Users/fixdive/real_estate/batumi_geo_base.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nГотово! Объектов: {len(results)} | Запросов: {total_requests}/1000")
    print(f"Сохранено: {output}")

asyncio.run(main())
