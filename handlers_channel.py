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

        @self.client.on(events.MessageDeleted(chats=list(CHANNELS.keys())))
        async def on_deleted_message(event):
            for msg_id in event.deleted_ids:
                await deactivate_property(event.chat_id, msg_id)
                logger.info(f"Объект удалён из канала: {event.chat_id}/{msg_id} → деактивирован")

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

            # Проверяем подписки и уведомляем
            try:
                from db import get_subscriptions_for_property
                subscribers = await get_subscriptions_for_property(data)
                if subscribers:
                    from handlers_user import format_property_card, _send_photos_to
                    card_text = format_property_card(data)
                    for sub in subscribers:
                        try:
                            if data.get("photos"):
                                await _send_photos_to(self.bot, sub["telegram_id"], data)
                            await self.bot.send_message(
                                chat_id=sub["telegram_id"],
                                text=f"🔔 <b>Новый объект по вашей подписке!</b>\n\n{card_text}",
                                disable_web_page_preview=True,
                            )
                        except Exception as e:
                            logger.error(f"Subscription notify error for {sub['telegram_id']}: {e}")
                    logger.info(f"Уведомлено {len(subscribers)} подписчиков")
            except Exception as e:
                logger.error(f"Subscriptions check error: {e}")

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения {msg.id}: {e}")

    # ─────────────────────────────────────────────────────────────────────
    # Получение фотографий
    # ─────────────────────────────────────────────────────────────────────

    async def _get_photos(self, msg: Message, channel_id: int) -> list[str]:
        """
        Сохраняем только первое фото альбома (наименьший message_id).
        Формат: ["channel_id:message_id"]
        """
        try:
            if msg.grouped_id:
                album_msgs = []
                async for album_msg in self.client.iter_messages(
                    channel_id,
                    min_id=msg.id - 3,
                    max_id=msg.id + 20,
                ):
                    if album_msg.grouped_id == msg.grouped_id and album_msg.photo:
                        album_msgs.append(album_msg)
                if album_msgs:
                    first = min(album_msgs, key=lambda m: m.id)
                    return [f"{channel_id}:{first.id}"]
            elif msg.photo:
                return [f"{channel_id}:{msg.id}"]
        except Exception as e:
            logger.error(f"Ошибка получения фото: {e}")

        return []

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

    async def get_album_photo_ids(self, channel_id: int, message_id: int) -> list[str]:
        """Вернуть channel_id:msg_id всех фото в альбоме по одному сообщению."""
        try:
            msg = await self.client.get_messages(channel_id, ids=message_id)
            if not msg:
                return []
            if msg.grouped_id:
                album = []
                async for m in self.client.iter_messages(
                    channel_id,
                    min_id=max(1, msg.id - 20),
                    max_id=msg.id + 20,
                ):
                    if m.grouped_id == msg.grouped_id and m.photo:
                        album.append(m)
                album.sort(key=lambda m: m.id)
                return [f"{channel_id}:{m.id}" for m in album]
            elif msg.photo:
                return [f"{channel_id}:{message_id}"]
        except Exception as e:
            logger.error(f"get_album_photo_ids error: {e}")
        return []

    async def fetch_history_since_days(self, days: int = 90):
        """Загрузить все посты за последние N дней из всех каналов."""
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        for channel_id in CHANNELS:
            logger.info(f"Загрузка {channel_id} с {cutoff.date()} (последние {days} дней)")
            count = 0
            async for msg in self.client.iter_messages(
                channel_id,
                offset_date=cutoff,
                reverse=True,
            ):
                if isinstance(msg, Message):
                    try:
                        await self._process_message(msg, channel_id)
                        count += 1
                        await asyncio.sleep(0.2)
                    except Exception as e:
                        logger.error(f"fetch_history_since_days: {e}")
            logger.info(f"✅ Обработано {count} сообщений из {channel_id}")

    async def fetch_older_posts(self, limit: int | None = None):
        """Загрузить посты старше самого раннего сохранённого (limit=None — без ограничений)."""
        from db import pool
        for channel_id in CHANNELS:
            async with pool.acquire() as conn:
                first_id = await conn.fetchval(
                    "SELECT MIN(message_id) FROM properties WHERE source_channel = $1",
                    channel_id,
                )
            if not first_id:
                await self.fetch_history(channel_id, limit or 500)
                continue

            logger.info(f"Загрузка всей истории {channel_id} до #{first_id}")
            count = 0
            async for msg in self.client.iter_messages(
                channel_id, max_id=first_id, limit=limit
            ):
                if isinstance(msg, Message):
                    try:
                        await self._process_message(msg, channel_id)
                        count += 1
                        if count % 100 == 0:
                            logger.info(f"  [{channel_id}] обработано {count}, msg_id={msg.id}")
                        await asyncio.sleep(0.15)
                    except Exception as e:
                        logger.error(f"fetch_older: {e}")
            logger.info(f"✅ Загружено {count} постов из {channel_id}")

    async def fetch_new_posts(self):
        """Загрузить новые посты. При первом запуске — 500 постов."""
        from db import get_last_message_id
        for channel_id in CHANNELS:
            last_id = await get_last_message_id(channel_id)
            if not last_id:
                logger.info(f"Первый запуск — загрузка 500 постов из {channel_id}")
                await self.fetch_history(channel_id, limit=500)
            else:
                logger.info(f"Загрузка новых постов из {channel_id} после #{last_id}")
                async for msg in self.client.iter_messages(channel_id, min_id=last_id):
                    try:
                        await self._process_message(msg, channel_id)
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        logger.error(f"Ошибка: {e}")


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
