import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
YANDEX_GEOCODER_KEY = os.getenv("YANDEX_GEOCODER_KEY")
GIS_API_KEY = os.getenv("GIS_API_KEY")
CHANNEL_RENT = int(os.getenv("CHANNEL_RENT"))
CHANNEL_SALE = int(os.getenv("CHANNEL_SALE"))
STORAGE_BOT_TOKEN = os.getenv("STORAGE_BOT_TOKEN")
STORAGE_CHAT_ID = int(os.getenv("STORAGE_CHAT_ID"))