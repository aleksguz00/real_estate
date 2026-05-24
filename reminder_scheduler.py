import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


async def check_reminders(bot):
    while True:
        try:
            now = datetime.now(ZoneInfo("Asia/Tbilisi"))
            # Не отправляем ночью (22:00 - 09:00)
            if now.hour >= 22 or now.hour < 9:
                await asyncio.sleep(60)
                continue

            from db import pool
            async with pool.acquire() as conn:
                reminders = await conn.fetch("""
                    SELECT * FROM reminders
                    WHERE reminded = FALSE
                    AND reminder_dt <= (NOW() AT TIME ZONE 'Asia/Tbilisi')
                """)

                for r in reminders:
                    try:
                        prop_address = ""
                        if r["prop_id"]:
                            prop_address = await conn.fetchval(
                                "SELECT address FROM properties WHERE id=$1",
                                r["prop_id"]
                            ) or ""

                        client = await conn.fetchrow(
                            "SELECT full_name, username, phone FROM users WHERE telegram_id=$1",
                            r["client_id"]
                        )
                        client_name = client["full_name"] if client else str(r["client_id"])
                        client_phone = client["phone"] if client else ""
                        client_username = client["username"] if client else ""

                        client_text = (
                            f"📅 Напоминание о просмотре!\n\n"
                            f"🕐 {r['viewing_dt'].strftime('%d.%m.%Y %H:%M')}\n"
                            f"📍 {prop_address}"
                        )

                        operator_text = (
                            f"⚡️ Напоминание о просмотре!\n\n"
                            f"🕐 {r['viewing_dt'].strftime('%d.%m.%Y %H:%M')}\n"
                            f"📍 {prop_address}\n\n"
                            f"👤 Клиент: {client_name}\n"
                            f"📱 Телефон: {client_phone or '—'}\n"
                            f"🔗 Username: @{client_username or '—'}"
                        )

                        await bot.send_message(chat_id=r["client_id"], text=client_text)
                        await bot.send_message(chat_id=r["operator_id"], text=operator_text)

                        await conn.execute(
                            "UPDATE reminders SET reminded=TRUE WHERE id=$1", r["id"]
                        )
                    except Exception as e:
                        logger.error(f"Reminder send error: {e}")

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        await asyncio.sleep(60)
