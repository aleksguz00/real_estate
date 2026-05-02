import asyncio, aiohttp

async def geocode(session, address):
    url = "https://geocode-maps.yandex.ru/1.x/"
    p = {"apikey": "aa3a5066-e53f-492d-a329-6124f9239782",
         "geocode": f"{address}, Батуми, Грузия",
         "format": "json", "results": 1}
    async with session.get(url, params=p) as r:
        d = await r.json()
        try:
            pos = d["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"]["pos"]
            lon, lat = map(float, pos.split())
            return lat, lon
        except:
            return None, None

async def main():
    landmarks = [
        ("площадь европы", "Старый Батуми"),
        ("улица горгиладзе 5", "Старый Батуми"),
        ("улица химшиашвили 5", "Химшиашвили"),
        ("улица агмашенебели 5", "Агмашенебели"),
        ("улица джавахишвили 5", "Джавахишвили"),
        ("улица багратиони 5", "Багратиони"),
        ("аэропорт батуми", "Аэропорт"),
        ("махинджаури", "Махинджаури"),
    ]
    async with aiohttp.ClientSession() as s:
        for address, district in landmarks:
            lat, lon = await geocode(s, address)
            if lat:
                print(f"{district:20s} | lat={lat:.4f} lon={lon:.4f}")
            await asyncio.sleep(0.3)

asyncio.run(main())
