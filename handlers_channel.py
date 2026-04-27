# handlers_channel.py
"""
Парсер Telegram каналов через Telethon.
Читает посты из BatumiHome24 (аренда) и BatumiFlatsGe (продажа).
Сохраняет объекты в БД и рассылает уведомления подписчикам.
"""

import logging
import asyncio
from datetime import datetime

from telethon import TelegramClient, events
from telethon.tl.types import Message, MessageMediaPhoto, MessageMediaDocument

from config import API_ID, API_HASH, CHANNEL_RENT, CHANNEL_SALE
from db import save_property, deactivate_property, get_subscriptions_for_property, get_user_id
from utils import parse_post, SOLD_KEYWORDS

logger = logging.getLogger(__name__)

# Сессия Telethon (файл сохраняется рядом с ботом)
SESSION_NAME = "kaufman_parser"

# Каналы для мониторинга
CHANNELS = {
    CHANNEL_RENT: "rent",
    CHANNEL_SALE: "sale",
}


class ChannelParser:
    def __init__(self, bot=None):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        self.bot = bot  # aiogram Bot для отправки уведомлений

    # ─────────────────────────────────────────────────────────────────────
    # Запуск клиента
    # ─────────────────────────────────────────────────────────────────────

    async def start(self):
        await self.client.start()
        logger.info("✅ Telethon клиент запущен")
        self._register_handlers()

    async def stop(self):
        await self.client.disconnect()
        logger.info("Telethon клиент остановлен")

    # ─────────────────────────────────────────────────────────────────────
    # Обработчики событий (новые и отредактированные посты)
    # ─────────────────────────────────────────────────────────────────────

    def _register_handlers(self):
        @self.client.on(events.NewMessage(chats=list(CHANNELS.keys())))
        async def on_new_message(event):
            await self._process_message(event.message, event.chat_id)

        @self.client.on(events.MessageEdited(chats=list(CHANNELS.keys())))
        async def on_edited_message(event):
            await self._process_message(event.message, event.chat_id)

        logger.info("✅ Обработчики каналов зарегистрированы")

    # ─────────────────────────────────────────────────────────────────────
    # Обработка одного сообщения
    # ─────────────────────────────────────────────────────────────────────

    async def _process_message(self, msg: Message, channel_id: int):
        """Обработать одно сообщение из канала."""
        text = msg.text or ""
        if not text and hasattr(msg, 'file') and msg.file:
            text = getattr(msg, 'message', "") or ""
        if not text:
            return

        try:
            data = await parse_post(text)
            if data is None:
                return

            # Объект снят с рынка
            if not data.get("is_active", True):
                await deactivate_property(channel_id, msg.id)
                logger.info(f"Объект деактивирован: {channel_id}/{msg.id}")
                return

            # Фотографии
            photos = await self._get_photos(msg, channel_id)

            # Дополняем данные
            data.update({
                "source_channel": channel_id,
                "message_id":     msg.id,
                "photos":         photos,
                "published_at":   msg.date.replace(tzinfo=None) if msg.date else datetime.utcnow(),
                "media_group_id": str(msg.grouped_id) if msg.grouped_id else None,
            })

            # Сохраняем в БД
            prop_id = await save_property(data)
            logger.info(f"✅ Объект #{prop_id} сохранён [{data.get('source_code', '')}]")

            # Отправляем уведомления подписчикам
            if prop_id and self.bot:
                await self._notify_subscribers(prop_id, data)

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения {msg.id}: {e}")

    # ─────────────────────────────────────────────────────────────────────
    # Получение фотографий
    # ─────────────────────────────────────────────────────────────────────

    async def _get_photos(self, msg: Message, channel_id: int) -> list[str]:
        """
        Сохраняем только message_id для последующей пересылки.
        Формат: "channel_id:message_id"
        """
        photos = []

        try:
            if msg.grouped_id:
                # Альбом — собираем ID всех сообщений группы
                async for album_msg in self.client.iter_messages(
                    channel_id,
                    min_id=msg.id - 15,
                    max_id=msg.id + 1,
                ):
                    if album_msg.grouped_id == msg.grouped_id and album_msg.photo:
                        photos.append(f"{channel_id}:{album_msg.id}")
                        if len(photos) >= 10:
                            break
            elif msg.photo:
                photos.append(f"{channel_id}:{msg.id}")

        except Exception as e:
            logger.error(f"Ошибка получения ID фото: {e}")

        return photos

    # ─────────────────────────────────────────────────────────────────────
    # Уведомления подписчикам
    # ─────────────────────────────────────────────────────────────────────

    async def _notify_subscribers(self, prop_id: int, data: dict):
        """Отправить уведомление пользователям чьи фильтры совпадают."""
        try:
            subscribers = await get_subscriptions_for_property(data)
            if not subscribers:
                return

            text = self._format_notification(data)

            for sub in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=sub["telegram_id"],
                        text=f"🔔 <b>Новый объект по вашим фильтрам!</b>\n\n{text}",
                        parse_mode="HTML",
                    )
                    await asyncio.sleep(0.1)  # Антиспам
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления {sub['telegram_id']}: {e}")

        except Exception as e:
            logger.error(f"Ошибка рассылки уведомлений: {e}")

    def _format_notification(self, data: dict) -> str:
        """Форматировать краткое уведомление об объекте."""
        parts = []

        if data.get("address"):
            parts.append(f"📍 {data['address']}")

        info = []
        if data.get("rooms"):
            info.append(f"🛏 {data['rooms']}")
        if data.get("floor"):
            floor_str = str(data["floor"])
            if data.get("floors_total"):
                floor_str += f"/{data['floors_total']}"
            info.append(f"🏢 {floor_str} эт.")
        if data.get("area"):
            info.append(f"📐 {data['area']} м²")
        if info:
            parts.append(" | ".join(info))

        if data.get("price"):
            deal = data.get("deal_type", "")
            suffix = "/мес" if deal == "rent" else ""
            parts.append(f"💰 ${data['price']:,}{suffix}")

        return "\n".join(parts)

    # ─────────────────────────────────────────────────────────────────────
    # Загрузка истории канала
    # ─────────────────────────────────────────────────────────────────────

    async def fetch_history(self, channel_id: int, limit: int = 100):
        """Загрузить последние N постов из канала (первичный парсинг)."""
        logger.info(f"Загрузка истории канала {channel_id}, limit={limit}")
        count = 0

        async for msg in self.client.iter_messages(channel_id, limit=limit):
            if isinstance(msg, Message):
                try:
                    await self._process_message(msg, channel_id)
                    count += 1
                    await asyncio.sleep(0.5)  # Пауза чтобы не перегружать API
                except Exception as e:
                    logger.error(f"Ошибка при загрузке истории {msg.id}: {e}")

        logger.info(f"✅ Загружено {count} постов из канала {channel_id}")

    async def fetch_all_channels(self, limit: int = 300):
        """Загрузить историю из всех каналов."""
        for channel_id in CHANNELS:
            await self.fetch_history(channel_id, limit)

    async def fetch_new_posts(self):
        """Загрузить только новые посты которых нет в БД."""
        from db import get_last_message_id
        for channel_id in CHANNELS:
            last_id = await get_last_message_id(channel_id)
            if last_id:
                # Загружаем только посты новее последнего сохранённого
                logger.info(f"Загрузка новых постов из {channel_id} после #{last_id}")
                async for msg in self.client.iter_messages(channel_id, min_id=last_id):
                    try:
                        await self._process_message(msg, channel_id)
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Ошибка: {e}")
            else:
                # Первый запуск — загружаем 300 постов
                logger.info(f"Первый запуск — загрузка 300 постов из {channel_id}")
                await self.fetch_history(channel_id, limit=300)


# ─────────────────────────────────────────────────────────────────────────────
# Глобальный экземпляр парсера
# ─────────────────────────────────────────────────────────────────────────────

parser: ChannelParser | None = None


async def start_parser(bot=None) -> ChannelParser:
    """Запустить парсер и вернуть экземпляр."""
    global parser
    parser = ChannelParser(bot=bot)
    await parser.start()
    return parser
