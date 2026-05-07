# handlers_admin.py
# Обработчики для операторов — подтверждение просмотров, аренды, закрытия

import asyncio

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from filters_fsm import AdminState, FixDistrict
from db import (
    is_admin, get_user_info,
    save_viewing, confirm_rental, close_rental,
    log_to_sheets,
)

router = Router()

REPLY_TEMPLATES = {
    "ru": [
        ("✅ Актуален + вопросы",
         "Объект актуален ✅\n\nУточните пожалуйста:\n• Сколько человек будет проживать?\n• Планируемая дата заезда?\n• Период аренды?\n• Есть ли домашние животные?"),
        ("🐾 Питомцы запрещены",
         "К сожалению, проживание с питомцами запрещено 🚫\n\nМожем подобрать другие варианты где питомцы разрешены 🏠"),
        ("📅 Записать на просмотр",
         "Готовы организовать просмотр.\nКогда вам удобно?"),
        ("✅ Подтвердить просмотр", "CONFIRM_VIEWING"),
        ("❌ Объект сдан",
         "К сожалению, объект уже сдан.\nМожем подобрать другие варианты 🏠"),
        ("✍️ Свой ответ", None),
    ],
    "en": [
        ("✅ Available + questions",
         "Property is available ✅\n\nPlease clarify:\n• How many people will be living?\n• Planned move-in date?\n• Rental period?\n• Do you have pets?"),
        ("🐾 No pets allowed",
         "Unfortunately, pets are not allowed 🚫\n\nWe can find other options where pets are welcome 🏠"),
        ("📅 Schedule viewing",
         "Ready to arrange a viewing.\nWhen is convenient for you?"),
        ("✅ Confirm viewing", "CONFIRM_VIEWING"),
        ("❌ Already rented",
         "Unfortunately, this property is already rented.\nWe can find other options 🏠"),
        ("✍️ Custom reply", None),
    ],
}


def _parse_op_data(data: str):
    """Парсим callback_data формата op_action_USERID_PROPID."""
    parts = data.split("_")
    user_id = int(parts[-2])
    prop_id = int(parts[-1])
    return user_id, prop_id


# ─────────────────────────────────────────────────────────────────────────────
# Оператор нажал «✅ Подтвердить просмотр»
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("op_confirm_"))
async def op_confirm_viewing(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    user_id, prop_id = _parse_op_data(callback.data)
    await state.update_data(
        viewing_client_id=user_id,
        viewing_prop_id=prop_id,
        viewing_operator_id=callback.from_user.id,
        reply_lang="ru",
    )
    await state.set_state(AdminState.waiting_viewing_datetime)
    await callback.answer()
    await callback.message.answer(
        f"📅 Введите дату и время просмотра для клиента <code>{user_id}</code>\n\n"
        f"Формат: <b>15.05.2026 14:00</b>",
        disable_notification=True,
    )


@router.message(AdminState.waiting_viewing_datetime)
async def save_viewing_datetime(message: Message, state: FSMContext):
    data = await state.get_data()
    datetime_str = message.text.strip()
    lang = data.get("reply_lang", "ru")

    client_id = (
        data.get("viewing_client_id") or
        data.get("confirm_client_id")
    )
    prop_id = (
        data.get("viewing_prop_id") or
        data.get("confirm_prop_id")
    )
    operator_id = data.get("viewing_operator_id") or message.from_user.id

    print(f"DEBUG save_viewing: client_id={client_id} prop_id={prop_id} datetime={datetime_str}")

    await state.update_data(
        viewing_datetime_str=datetime_str,
        viewing_client_id=client_id,
        viewing_prop_id=prop_id,
        viewing_operator_id=operator_id,
    )
    await state.set_state(AdminState.waiting_reminder_choice)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ За 1 час", callback_data="reminder_1")],
        [InlineKeyboardButton(text="⏰ За 2 часа", callback_data="reminder_2")],
        [InlineKeyboardButton(text="⏰ За 3 часа", callback_data="reminder_3")],
    ])
    await message.answer(
        "За сколько времени напомнить о просмотре?",
        reply_markup=kb,
        disable_notification=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Оператор нажал «❌ Отклонить»
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("op_decline_"))
async def op_decline(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    user_id = int(callback.data.replace("op_decline_", ""))
    await callback.answer()

    await callback.bot.send_message(
        chat_id=user_id,
        text=(
            "😔 К сожалению, по данному объекту не удалось организовать просмотр.\n\n"
            "Напишите нам — подберём другие варианты!"
        )
    )
    await callback.message.answer(f"❌ Клиент <code>{user_id}</code> уведомлён об отклонении.")


# ─────────────────────────────────────────────────────────────────────────────
# Подтверждение аренды
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("op_rental_"))
async def op_confirm_rental(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    user_id, prop_id = _parse_op_data(callback.data)
    await state.update_data(target_user_id=user_id, target_prop_id=prop_id)
    await state.set_state(AdminState.waiting_rental_date)
    await callback.answer()
    await callback.message.answer(
        f"📅 Введите дату начала аренды для клиента <code>{user_id}</code>\n\n"
        f"Формат: <b>01 мая 2026</b>"
    )


@router.message(AdminState.waiting_rental_date)
async def save_rental_date(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    data = await state.get_data()
    user_id = data["target_user_id"]
    prop_id = data["target_prop_id"]
    date_str = message.text.strip()

    await confirm_rental(user_id, prop_id, date_str)
    await log_to_sheets(user_id, prop_id, {"rental_start": date_str, "status": "Арендовал"})

    await state.set_state(None)
    await message.answer(
        f"✅ Аренда подтверждена!\n"
        f"Клиент: <code>{user_id}</code>\n"
        f"Объект: #{prop_id}\n"
        f"Дата въезда: {date_str}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Закрытие аренды (клиент съехал)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("op_close_"))
async def op_close_rental(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    user_id, prop_id = _parse_op_data(callback.data)
    await state.update_data(target_user_id=user_id, target_prop_id=prop_id)
    await state.set_state(AdminState.waiting_close_date)
    await callback.answer()
    await callback.message.answer(
        f"📅 Введите дату окончания аренды для клиента <code>{user_id}</code>\n\n"
        f"Формат: <b>01 июня 2026</b>"
    )


@router.message(AdminState.waiting_close_date)
async def save_close_date(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    data = await state.get_data()
    user_id = data["target_user_id"]
    prop_id = data["target_prop_id"]
    date_str = message.text.strip()

    await close_rental(user_id, prop_id, date_str)
    await log_to_sheets(user_id, prop_id, {"rental_end": date_str, "status": "Сдал"})

    await state.set_state(None)
    await message.answer(
        f"✅ Аренда закрыта!\n"
        f"Клиент: <code>{user_id}</code>\n"
        f"Объект: #{prop_id}\n"
        f"Дата выезда: {date_str}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Проверить объект (только для админов — телефон из таблицы)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_check_"))
async def admin_check_property(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    prop_id = int(callback.data.replace("admin_check_", ""))
    # TODO: получить телефон из Google Sheets по prop_id
    phone = "Загрузка из таблицы..."

    await callback.answer(
        f"📞 Контакт собственника:\n{phone}",
        show_alert=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# Клиент поделился телефоном после подтверждения просмотра
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "share_phone_viewing")
async def share_phone_viewing(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📱 Поделитесь номером телефона — менеджер свяжется с вами перед просмотром."
    )
    await state.set_state(AdminState.waiting_client_phone)


@router.callback_query(F.data == "skip_phone_viewing")
async def skip_phone_viewing(callback: CallbackQuery):
    await callback.answer("Хорошо, ждём вас на просмотре! 🏠")


# ─────────────────────────────────────────────────────────────────────────────
# Загрузка истории каналов
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_fetch_history")
async def admin_fetch_history(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await callback.answer()
    msg = await callback.message.answer(
        "⬇️ <b>Загрузка истории каналов запущена...</b>\n\n"
        "Загружаю все посты за последние 90 дней из каждого канала.\n"
        "Это займёт несколько минут — бот остаётся рабочим."
    )

    async def _run():
        from handlers_channel import parser
        if not parser:
            await msg.edit_text("❌ Парсер не запущен.")
            return
        before = await _count_properties()
        await parser.fetch_history_since_days(days=90)
        after = await _count_properties()
        added = after - before
        await msg.edit_text(
            f"✅ <b>Загрузка завершена!</b>\n\n"
            f"Было объектов: {before}\n"
            f"Стало объектов: {after}\n"
            f"Добавлено: <b>+{added}</b>"
        )

    asyncio.create_task(_run())


@router.callback_query(F.data == "admin_fetch_all")
async def admin_fetch_all(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await callback.answer()
    msg = await callback.message.answer(
        "⏬ <b>Загрузка ВСЕЙ истории каналов запущена...</b>\n\n"
        "Загружаю все посты старше уже сохранённых — без ограничений.\n"
        "Может занять 10–30 минут. Бот остаётся рабочим."
    )

    async def _run_all():
        from handlers_channel import parser
        if not parser:
            await msg.edit_text("❌ Парсер не запущен.")
            return
        before = await _count_properties()
        await parser.fetch_older_posts(limit=None)
        after = await _count_properties()
        await msg.edit_text(
            f"✅ <b>Загрузка всей истории завершена!</b>\n\n"
            f"Было объектов: {before}\n"
            f"Стало объектов: {after}\n"
            f"Добавлено: <b>+{after - before}</b>"
        )

    asyncio.create_task(_run_all())


async def _count_properties() -> int:
    from db import pool
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM properties")


@router.callback_query(F.data == "admin_geocode_all")
async def admin_geocode_all(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await callback.answer()
    msg = await callback.message.answer(
        "🗺 <b>Геокодирование запущено...</b>\n\n"
        "Обновляю координаты для объектов без lat/lon.\n"
        "Это займёт несколько минут — бот остаётся рабочим."
    )

    async def _run():
        import asyncio
        import logging
        from db import pool, update_property_geocode
        from utils import geocode_address

        _log = logging.getLogger(__name__)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, address FROM properties WHERE address IS NOT NULL AND (district IS NULL OR district = '')"
            )

        total = len(rows)
        _log.info(f"[geocode] Найдено объектов без района: {total}")
        for r in rows[:3]:
            _log.info(f"[geocode] Пример: id={r['id']} address={r['address']!r}")

        if rows:
            first = rows[0]
            _log.info(f"[geocode] Тестовый geocode для id={first['id']}: {first['address']!r}")
            try:
                test_result = await geocode_address(first["address"])
                _log.info(f"[geocode] Результат geocode_address → {test_result}")
            except Exception as e:
                _log.error(f"[geocode] Ошибка тестового geocode: {e}")

        updated = 0
        for row in rows:
            try:
                district, lat, lon = await geocode_address(row["address"])
                if district:
                    _log.info(
                        f"[geocode] UPDATE id={row['id']} district={district!r} lat={lat} lon={lon}"
                    )
                    await update_property_geocode(row["id"], district, lat, lon)
                    updated += 1
                else:
                    _log.warning(f"[geocode] Район не определён для id={row['id']} address={row['address']!r}")
                await asyncio.sleep(0.25)
            except Exception as e:
                _log.error(f"[geocode] Исключение для id={row['id']}: {e}")
                pass

        await msg.edit_text(
            f"✅ <b>Геокодирование завершено!</b>\n\n"
            f"Всего без координат: {total}\n"
            f"Обновлено: <b>{updated}</b>"
        )

    asyncio.create_task(_run())


# ─────────────────────────────────────────────────────────────────────────────
# Исправить район объекта (только для операторов)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fix_district:"))
async def fix_district_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    property_id = callback.data.split(":")[1]

    current_data = await state.get_data()
    search_results = current_data.get("search_results")
    search_index   = current_data.get("search_index", 0)
    lang           = current_data.get("lang", "ru")

    await state.set_state(FixDistrict.waiting_district)
    await state.update_data(
        property_id=property_id,
        search_results=search_results,
        search_index=search_index,
        lang=lang,
    )

    районы = [
        "Старый Батуми", "Химшиашвили", "Аэропорт", "Новый Бульвар",
        "Руставели", "Джавахишвили", "Багратиони", "Агмашенебели",
        "Тамар", "Бони Городок", "Кахабери", "Махинджаури",
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=r, callback_data=f"set_district:{r}")]
        for r in районы
    ])
    await callback.answer()
    await callback.message.answer("Выбери правильный район:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("set_district:"), FixDistrict.waiting_district)
async def fix_district_set(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    property_id    = data["property_id"]
    search_results = data.get("search_results")
    search_index   = data.get("search_index", 0)
    lang           = data.get("lang", "ru")
    district = callback.data.split(":", 1)[1]

    from db import pool, get_properties
    import json

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT address FROM properties WHERE id=$1", int(property_id)
        )
        address = row["address"]
        updated = await conn.execute(
            "UPDATE properties SET district=$1 WHERE address=$2",
            district, address,
        )

    cache_file = "/Users/fixdive/real_estate/district_cache.json"
    try:
        with open(cache_file, encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        cache = {}
    cache[address] = district
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    await state.clear()
    await callback.answer()

    await callback.message.answer(
        f"✅ Район исправлен на '{district}'\n"
        f"Адрес: {address}\n"
        f"Обновлено объектов: {updated.split()[-1]}"
    )

    # Восстанавливаем навигацию и показываем текущую карточку
    if search_results:
        await state.set_data({"search_results": search_results, "search_index": search_index, "lang": lang})
        props = await get_properties({"id_in": [search_results[search_index]]}, limit=1)
        if props:
            from handlers_user import show_property_card
            await show_property_card(
                callback.message, state, props[0],
                search_index + 1, len(search_results), lang,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Временная команда: загрузить историю канала продажи за 60 дней
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("fetch_sale"))
async def fetch_sale_history(message: Message):
    from handlers_user import OPERATOR_IDS
    if message.from_user.id not in OPERATOR_IDS:
        return

    await message.answer("⏳ Загружаю историю продаж за 60 дней...")

    from handlers_channel import parser
    from datetime import datetime, timedelta, timezone
    from telethon.tl.types import Message as TelethonMessage
    from config import CHANNEL_SALE

    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    count = 0
    async for msg in parser.client.iter_messages(
        CHANNEL_SALE,
        offset_date=cutoff,
        reverse=True,
    ):
        if isinstance(msg, TelethonMessage):
            await parser._process_message(msg, CHANNEL_SALE)
            count += 1

    await message.answer(f"✅ Загружено {count} постов продажи")


# ─────────────────────────────────────────────────────────────────────────────
# Ответить клиенту по шаблону
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("op_reply_"))
async def op_reply_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    client_id = int(parts[2])
    prop_id = int(parts[3]) if len(parts) > 3 else 0

    from db import pool
    async with pool.acquire() as conn:
        lang = await conn.fetchval(
            "SELECT lang FROM users WHERE telegram_id=$1", client_id
        ) or "ru"

    await state.update_data(reply_client_id=client_id, reply_lang=lang, reply_prop_id=prop_id)

    templates = REPLY_TEMPLATES.get(lang, REPLY_TEMPLATES["ru"])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=label,
            callback_data=f"op_tpl_{i}_{client_id}_{prop_id}",
        )]
        for i, (label, _) in enumerate(templates)
    ])
    await callback.answer()
    await callback.message.answer(
        "Выберите шаблон ответа:" if lang == "ru" else "Choose reply template:",
        reply_markup=kb,
        disable_notification=True,
    )


@router.callback_query(F.data.startswith("op_tpl_"))
async def op_reply_template(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    tpl_idx = int(parts[2])
    client_id = int(parts[3])
    prop_id = int(parts[4]) if len(parts) > 4 else 0

    data = await state.get_data()
    lang = data.get("reply_lang", "ru")
    templates = REPLY_TEMPLATES.get(lang, REPLY_TEMPLATES["ru"])
    label, text = templates[tpl_idx]

    if text == "CONFIRM_VIEWING":
        print(f"DEBUG CONFIRM_VIEWING: client_id={client_id}")
        await state.update_data(
            viewing_client_id=client_id,
            viewing_prop_id=data.get("reply_prop_id") or data.get("confirm_prop_id") or prop_id or 0,
            viewing_operator_id=callback.from_user.id,
            reply_lang=lang,
        )
        await state.set_state(AdminState.waiting_viewing_datetime)
        await callback.answer()
        await callback.message.answer(
            "📅 Введите дату и время просмотра:\nНапример: 15.05.2026 14:00"
            if lang == "ru" else
            "📅 Enter date and time:\nExample: 15.05.2026 14:00",
            disable_notification=True,
        )
        return
    elif text:
        await callback.bot.send_message(
            chat_id=client_id,
            text=f"💬 <b>{'Ответ менеджера' if lang == 'ru' else 'Manager reply'}:</b>\n\n{text}",
            parse_mode="HTML",
        )
        # Открываем диалог — клиент может ответить
        from db import pool
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO active_dialogs (client_id, operator_id, prop_id)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (client_id) DO UPDATE SET
                       operator_id = EXCLUDED.operator_id,
                       prop_id = EXCLUDED.prop_id,
                       created_at = NOW()""",
                client_id, callback.from_user.id, prop_id or None,
            )
        await callback.bot.send_message(
            chat_id=client_id,
            text="💬 Напишите ваш ответ 👇",
            disable_notification=False,
        )
        await callback.answer("✅ Отправлено!" if lang == "ru" else "✅ Sent!")
        await callback.message.answer(
            "✅ Ответ отправлен клиенту",
            disable_notification=True,
        )
        await state.clear()
    else:
        await state.update_data(reply_client_id=client_id, reply_prop_id=prop_id)
        await state.set_state(AdminState.waiting_reply_text)
        await callback.answer()
        await callback.message.answer(
            "✍️ Напишите ваш ответ клиенту:" if lang == "ru" else "✍️ Write your reply:",
            disable_notification=True,
        )


@router.message(AdminState.waiting_reply_text)
async def op_reply_custom(message: Message, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("reply_client_id")
    prop_id = data.get("reply_prop_id", 0)
    lang = data.get("reply_lang", "ru")

    await message.bot.send_message(
        chat_id=client_id,
        text=f"💬 <b>{'Ответ менеджера' if lang == 'ru' else 'Manager reply'}:</b>\n\n{message.text}",
        parse_mode="HTML",
    )
    # Открываем диалог — клиент может ответить
    from db import pool
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO active_dialogs (client_id, operator_id, prop_id)
               VALUES ($1, $2, $3)
               ON CONFLICT (client_id) DO UPDATE SET
                   operator_id = EXCLUDED.operator_id,
                   prop_id = EXCLUDED.prop_id,
                   created_at = NOW()""",
            client_id, message.from_user.id, prop_id or None,
        )
    await message.bot.send_message(
        chat_id=client_id,
        text="💬 Напишите ваш ответ 👇",
        disable_notification=False,
    )
    await message.answer("✅ Ответ отправлен клиенту!", disable_notification=True)
    await state.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Выбор времени напоминания о просмотре
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(AdminState.waiting_reminder_choice, F.data.startswith("reminder_"))
async def set_reminder(callback: CallbackQuery, state: FSMContext):
    hours = int(callback.data.split("_")[1])
    data = await state.get_data()
    client_id = data.get("viewing_client_id")
    prop_id = data.get("viewing_prop_id")
    operator_id = data.get("viewing_operator_id") or callback.from_user.id
    datetime_str = data.get("viewing_datetime_str")
    lang = data.get("reply_lang", "ru")

    from datetime import datetime, timedelta
    viewing_dt = None
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y в %H:%M"):
        try:
            viewing_dt = datetime.strptime(datetime_str, fmt)
            break
        except Exception:
            pass

    if not viewing_dt:
        await callback.answer()
        await callback.message.answer(
            "❌ Неверный формат даты. Введите: 15.05.2026 14:00",
            disable_notification=True,
        )
        await state.set_state(AdminState.waiting_viewing_datetime)
        return

    reminder_dt = viewing_dt - timedelta(hours=hours)

    from db import save_viewing, pool
    if client_id and prop_id:
        await save_viewing(client_id, prop_id, datetime_str)

    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO reminders
               (client_id, operator_id, prop_id, viewing_dt, reminder_dt, reminded)
               VALUES ($1, $2, $3, $4, $5, FALSE)""",
            client_id, operator_id, prop_id or None, viewing_dt, reminder_dt,
        )

    prop_address = ""
    if prop_id:
        async with pool.acquire() as conn:
            prop_address = await conn.fetchval(
                "SELECT address FROM properties WHERE id=$1", prop_id
            ) or ""

    from google_sheets import add_viewing_to_sheet
    if client_id:
        await add_viewing_to_sheet(client_id, prop_id or 0, datetime_str)

    hours_text = {1: "час", 2: "часа", 3: "часа"}
    await callback.bot.send_message(
        chat_id=client_id,
        text=(
            f"✅ Просмотр подтверждён!\n"
            f"📅 {datetime_str}\n"
            f"📍 {prop_address}\n\n"
            f"Напомним за {hours} {hours_text.get(hours, 'часа')} до встречи!"
        ) if lang == "ru" else (
            f"✅ Viewing confirmed!\n"
            f"📅 {datetime_str}\n"
            f"📍 {prop_address}\n\n"
            f"We'll remind you {hours} hour(s) before!"
        ),
    )

    await callback.answer("✅ Просмотр записан!")
    await callback.message.answer(
        f"✅ Просмотр записан на {datetime_str}\n"
        f"Напоминание за {hours} ч. будет отправлено обоим.",
        disable_notification=True,
    )
    await state.clear()
    await state.update_data(lang=lang)


@router.message(AdminState.waiting_client_phone, F.contact)
async def save_client_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    # TODO: сохранить телефон клиента в БД и таблицу
    await log_to_sheets(message.from_user.id, 0, {"phone": phone})
    await state.set_state(None)
    await message.answer("✅ Телефон сохранён! Ждём вас на просмотре 🏠")
