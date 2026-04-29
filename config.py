import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

_api_id = os.getenv("API_ID")
API_ID = int(_api_id) if _api_id else None
API_HASH = os.getenv("API_HASH") or None

_channel_rent = os.getenv("CHANNEL_RENT")
CHANNEL_RENT = int(_channel_rent) if _channel_rent else None

_channel_sale = os.getenv("CHANNEL_SALE")
CHANNEL_SALE = int(_channel_sale) if _channel_sale else None

YANDEX_GEOCODER_KEY = os.getenv("YANDEX_GEOCODER_KEY") or None

STORAGE_BOT_TOKEN = os.getenv("STORAGE_BOT_TOKEN") or None

_storage_chat = os.getenv("STORAGE_CHAT_ID")
STORAGE_CHAT_ID = int(_storage_chat) if _storage_chat else None
