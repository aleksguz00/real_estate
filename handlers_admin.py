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
    await state.update_data(target_user_id=user_id, target_prop_id=prop_id)
    await state.set_state(AdminState.waiting_viewing_datetime)
    await callback.answer()
    await callback.message.answer(
        f"📅 Введите дату и время просмотра для клиента <code>{user_id}</code>\n\n"
        f"Формат: <b>27 апреля 15:00</b>"
    )


@router.message(AdminState.waiting_viewing_datetime)
async def save_viewing_datetime(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    data = await state.get_data()
    user_id = data["target_user_id"]
    prop_id = data["target_prop_id"]
    datetime_str = message.text.strip()

    # Сохраняем в БД и таблицу
    await save_viewing(user_id, prop_id, datetime_str)
    await log_to_sheets(user_id, prop_id, {"viewing_date": datetime_str, "status": "Назначен"})

    await state.set_state(None)

    # Уведомляем клиента
    client_info = await get_user_info(user_id)
    phone = client_info.get("phone", "")
    phone_text = f"\n\n📱 Подтвердите номер телефона (необязательно)" if not phone else ""

    confirm_kb = None
    if not phone:
        confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Поделиться номером",
                    callback_data="share_phone_viewing"
                ),
                InlineKeyboardButton(text="Пропустить", callback_data="skip_phone_viewing"),
            ]
        ])

    await message.bot.send_message(
        chat_id=user_id,
        text=(
            f"✅ <b>Просмотр подтверждён!</b>\n\n"
            f"🏠 Объект: #{prop_id}\n"
            f"📅 Дата и время: <b>{datetime_str}</b>\n\n"
            f"Ждём вас! Если возникнут вопросы — пишите нам."
            f"{phone_text}"
        ),
        reply_markup=confirm_kb,
    )

    await message.answer(f"✅ Клиент <code>{user_id}</code> уведомлён о просмотре {datetime_str}")


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


@router.message(AdminState.waiting_client_phone, F.contact)
async def save_client_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    # TODO: сохранить телефон клиента в БД и таблицу
    await log_to_sheets(message.from_user.id, 0, {"phone": phone})
    await state.set_state(None)
    await message.answer("✅ Телефон сохранён! Ждём вас на просмотре 🏠")
