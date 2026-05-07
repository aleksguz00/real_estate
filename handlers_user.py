# handlers_user.py

import asyncio
import logging
import re
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from keyboards import (
    language_kb, subscription_kb, main_menu_kb, search_dashboard_kb,
    fresh_kb, rooms_kb, area_kb, deal_type_kb, land_type_kb,
    district_kb, budget_kb, features_kb, heating_kb, property_card_kb,
    favorites_kb, subscriptions_kb, admin_panel_kb, skip_kb,
    PRICE_RANGES_RENT, PRICE_RANGES_SALE, FRESHNESS_OPTIONS,
)
from locales import t, tl
from filters_fsm import FilterState, AdminState
from db import save_user, is_admin

router = Router()

# Паттерн старого формата хранения фото: "channel_id:msg_id"
_CHANNEL_REF = re.compile(r"^-?\d+:\d+$")

WELCOME_PHOTO = "AgACAgIAAxkBAAILMWnzz-iCdzgaAAGMWhluyR3c4qsyQQACJBdrG_DNoUvZB40620efuQEAAwIAA3cAAzsE"
CHANNEL_USERNAME = "BatumiHome24"
CHANNEL_URL = "https://t.me/BatumiHome24"
OPERATOR_IDS = [7572451975, 8154802423]


async def get_lang(state: FSMContext) -> str:
    """Получить язык пользователя из FSM."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    return data.get("lang", "ru")


# ─────────────────────────────────────────────────────────────────────────────
# БИНГО — тексты
# ─────────────────────────────────────────────────────────────────────────────

BINGO_ADS = [
    "Срочно! Уютная квартира с евроремонтом в тихом районе у трассы. Собственник. Море в 5 минутах. Звоните!",
    "Сдаётся светлая квартира. Евроремонт. Тихий двор. Собственник (перезвонит агент). До моря 5 минут пешком.",
    "Срочно! Продаётся квартира. Свежий ремонт 2005 года. Тихий район, рядом с морем. Собственник. Объявление актуально.",
]


def bingo_result_text(count: int) -> str:
    if count == 0:
        return "0 / 7 — 😇 Кажется, это честное объявление. Такое бывает раз в год!"
    elif count <= 2:
        return f"{count} / 7 — 🙂 Неплохой детектив рынка недвижимости."
    elif count <= 4:
        return f"{count} / 7 — 😏 Хороший результат! Вы явно искали квартиру в Батуми."
    elif count <= 6:
        return f"{count} / 7 — 🧐 Профи! Вас не проведёшь."
    else:
        return (
            "7 / 7 — 🏆 ЛЕГЕНДА! Вы нашли все признаки.\n\n"
            "🎁 При аренде квартиры через Kaufman Estate — бонус <b>$50</b> на карту!\n"
            "Напишите нам и скажите кодовое слово: <b>БИНГО</b>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# /start — выбор языка
# ─────────────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    from google_sheets import add_user_to_sheet
    await state.clear()
    await save_user(message.from_user.id, message.from_user.username)
    await add_user_to_sheet(
        telegram_id=message.from_user.id,
        name=message.from_user.full_name,
        username=message.from_user.username,
        lang=message.from_user.language_code,
    )
    try:
        await message.answer_photo(
            photo=WELCOME_PHOTO,
            caption="Выберите язык / Choose language:",
            reply_markup=language_kb(),
            disable_notification=True,
        )
    except Exception:
        await message.answer(
            "Выберите язык / Choose language:",
            reply_markup=language_kb(),
            disable_notification=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
@router.message(Command("stats"))
async def show_stats(message: Message):
    from db import pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                deal_type,
                COALESCE(rooms, property_type) as type,
                COUNT(*) as count
            FROM properties
            WHERE is_active = TRUE
            GROUP BY deal_type, COALESCE(rooms, property_type)
            ORDER BY deal_type, count DESC
        """)
        total = await conn.fetchval("SELECT COUNT(*) FROM properties WHERE is_active = TRUE")

    lines = [f"📊 <b>Объектов в базе: {total}</b>\n"]
    lines.append("🔑 <b>Аренда:</b>")
    for row in rows:
        if row["deal_type"] == "rent":
            lines.append(f"  • {row['type']}: {row['count']}")
    lines.append("\n💰 <b>Продажа:</b>")
    for row in rows:
        if row["deal_type"] == "sale":
            lines.append(f"  • {row['type']}: {row['count']}")
    await message.answer("\n".join(lines), parse_mode="HTML", disable_notification=True)


# ВЫБОР ЯЗЫКА
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.in_(["lang_ru", "lang_en"]))
async def set_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.replace("lang_", "")
    await state.update_data(lang=lang)
    await callback.answer()
    await _show_main_menu(callback.message, state, edit=True)


# ─────────────────────────────────────────────────────────────────────────────
# ПРОВЕРКА ПОДПИСКИ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    try:
        member = await callback.bot.get_chat_member(
            chat_id=f"@{CHANNEL_USERNAME}",
            user_id=user_id,
        )
        is_subscribed = member.status not in ["left", "kicked", "banned"]
    except Exception:
        is_subscribed = False

    if is_subscribed:
        await callback.answer("✅ Подписка подтверждена!")
        await _show_main_menu(callback.message, state, edit=True)
    else:
        await callback.answer(
            "❌ Вы не подписаны на канал. Подпишитесь и нажмите снова.",
            show_alert=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# ГЛАВНОЕ МЕНЮ
# ─────────────────────────────────────────────────────────────────────────────

async def _show_main_menu(message: Message, state: FSMContext, edit: bool = False):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    admin = await is_admin(message.chat.id)
    text = t("welcome", lang)
    kb = main_menu_kb(lang=lang, is_admin=admin)

    if edit:
        try:
            await message.edit_caption(caption=text, reply_markup=kb)
            return
        except Exception:
            pass
    try:
        await message.answer_photo(photo=WELCOME_PHOTO, caption=text, reply_markup=kb, disable_notification=True)
    except Exception:
        await message.answer(text, reply_markup=kb, disable_notification=True)


@router.callback_query(F.data == "change_language")
async def change_language(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.edit_caption(
            caption=t("choose_language", "ru"),
            reply_markup=language_kb(),
        )
    except Exception:
        await callback.message.answer(
            t("choose_language", "ru"),
            reply_markup=language_kb(),
            disable_notification=True,
        )


@router.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await callback.answer()
    await _show_main_menu(callback.message, state, edit=True)


# ─────────────────────────────────────────────────────────────────────────────
# ОТКРЫТЬ ПОИСК
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "open_search")
async def open_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.answer()
    await callback.message.answer(
        t("search_title", lang),
        reply_markup=search_dashboard_kb(data, lang),
        disable_notification=True,
    )


@router.callback_query(F.data == "back_to_search")
async def back_to_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(F.data == "filter_reset")
async def filter_reset(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await state.clear()
    await state.update_data(lang=lang)
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb({}))
    await callback.answer(t("cleared", lang))


# ─────────────────────────────────────────────────────────────────────────────
# НОВИЗНА
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "filter_fresh")
async def filter_fresh(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(FilterState.choosing_fresh)
    await callback.message.edit_reply_markup(reply_markup=fresh_kb(data.get("fresh"), lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_fresh, F.data.startswith("fresh_"))
async def set_fresh(callback: CallbackQuery, state: FSMContext):
    key = callback.data.replace("fresh_", "")
    data = await state.get_data()
    lang = data.get("lang", "ru")
    if key == "manual":
        await state.set_state(FilterState.fresh_manual_input)
        await state.update_data(bot_msg_id=callback.message.message_id)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            t("enter_depth", lang),
            reply_markup=skip_kb("skip_fresh", lang),
            disable_notification=True,
        )
        await callback.answer()
        return
    label = next((t(lk, lang) for k, lk in FRESHNESS_OPTIONS if k == f"fresh_{key}"), f"📅 {key}")
    await state.update_data(fresh=f"fresh_{key}", fresh_label=label)
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(FilterState.fresh_manual_input, F.data == "skip_fresh")
async def skip_fresh(callback: CallbackQuery, state: FSMContext):
    await state.update_data(fresh=None, fresh_label=None)
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    bot_msg_id = data.get("bot_msg_id")
    await callback.message.delete()
    if bot_msg_id:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=bot_msg_id,
            reply_markup=search_dashboard_kb(data, lang),
        )
    await callback.answer()


@router.message(FilterState.fresh_manual_input)
async def fresh_manual_input(message: Message, state: FSMContext):
    try:
        val = int(message.text.strip())
        if val <= 0:
            raise ValueError
        await state.update_data(fresh=f"fresh_{val}", fresh_label=f"📅 {val} дней")
        await message.delete()
        await state.set_state(None)
        data = await state.get_data()
        lang = data.get("lang", "ru")
        bot_msg_id = data.get("bot_msg_id")
        if bot_msg_id:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=bot_msg_id,
                reply_markup=search_dashboard_kb(data, lang),
            )
    except ValueError:
        await message.answer("⚠️ Введите число, например: 21", disable_notification=True)


# ─────────────────────────────────────────────────────────────────────────────
# КОМНАТЫ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "filter_rooms")
async def filter_rooms(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(FilterState.choosing_rooms)
    await callback.message.edit_reply_markup(reply_markup=rooms_kb(data.get("rooms", []), lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_rooms, F.data.startswith("room_"))
async def set_room(callback: CallbackQuery, state: FSMContext):
    room = callback.data.replace("room_", "")
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected = data.get("rooms", [])
    if isinstance(selected, str):
        selected = [selected]
    if room in selected:
        selected.remove(room)
    else:
        selected.append(room)
    await state.update_data(rooms=selected)
    await callback.message.edit_reply_markup(reply_markup=rooms_kb(selected, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_rooms, F.data == "rooms_done")
async def rooms_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(FilterState.choosing_area)
    await callback.message.edit_reply_markup(reply_markup=area_kb(lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_rooms, F.data == "back_to_search")
async def back_from_rooms(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# ПЛОЩАДЬ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(FilterState.choosing_area, F.data.startswith("area_"))
async def set_area(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    val = callback.data.replace("area_", "")
    if val == "skip":
        await state.update_data(area_from=None)
        await state.set_state(None)
        data = await state.get_data()
        await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    elif val == "manual":
        await state.set_state(FilterState.area_manual_input)
        await state.update_data(bot_msg_id=callback.message.message_id)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            t("enter_area", lang),
            reply_markup=skip_kb("skip_area", lang),
            disable_notification=True,
        )
    else:
        await state.update_data(area_from=int(val))
        await state.set_state(None)
        data = await state.get_data()
        await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_area, F.data == "back_to_rooms")
async def back_to_rooms(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.choosing_rooms)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=rooms_kb(data.get("rooms"), lang))
    await callback.answer()


@router.callback_query(FilterState.area_manual_input, F.data == "skip_area")
async def skip_area(callback: CallbackQuery, state: FSMContext):
    await state.update_data(area_from=None)
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    bot_msg_id = data.get("bot_msg_id")
    await callback.message.delete()
    if bot_msg_id:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=bot_msg_id,
            reply_markup=search_dashboard_kb(data, lang),
        )
    await callback.answer()


@router.message(FilterState.area_manual_input)
async def area_manual_input(message: Message, state: FSMContext):
    try:
        val = int(message.text.strip())
        if val <= 0:
            raise ValueError
        await state.update_data(area_from=val)
        await message.delete()
        await state.set_state(None)
        data = await state.get_data()
        lang = data.get("lang", "ru")
        bot_msg_id = data.get("bot_msg_id")
        if bot_msg_id:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=bot_msg_id,
                reply_markup=search_dashboard_kb(data, lang),
            )
    except ValueError:
        await message.answer(t("error_number", lang), disable_notification=True)


# ─────────────────────────────────────────────────────────────────────────────
# ТИП СДЕЛКИ И ОБЪЕКТА
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "filter_type")
async def filter_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(FilterState.choosing_type)
    await callback.message.edit_reply_markup(
        reply_markup=deal_type_kb(data.get("deal_type"), data.get("prop_types", []), lang)
    )
    await callback.answer()


@router.callback_query(FilterState.choosing_type, F.data.startswith("deal_"))
async def set_deal(callback: CallbackQuery, state: FSMContext):
    deal = callback.data.replace("deal_", "")
    await state.update_data(deal_type=deal, budget=None, budget_label=None, budgets=[])
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(
        reply_markup=deal_type_kb(deal, data.get("prop_types", []), lang)
    )
    await callback.answer()


@router.callback_query(FilterState.choosing_type, F.data.startswith("prop_") & ~F.data.endswith("_done"))
async def set_prop_type(callback: CallbackQuery, state: FSMContext):
    prop = callback.data.replace("prop_", "")
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected = data.get("prop_types", [])

    if prop == "commercial":
        if "commercial" in selected:
            selected.remove("commercial")
        else:
            selected.append("commercial")
        await state.update_data(prop_types=selected)
        data = await state.get_data()
        await callback.message.edit_reply_markup(
            reply_markup=deal_type_kb(data.get("deal_type"), selected, lang)
        )
    elif prop == "land":
        await state.update_data(prop_types=["land"], land_type=None)
        await state.set_state(FilterState.choosing_land)
        await callback.message.edit_reply_markup(reply_markup=land_type_kb(lang=lang))
    else:
        if prop in selected:
            selected.remove(prop)
        else:
            selected.append(prop)
        await state.update_data(prop_types=selected)
        data = await state.get_data()
        lang = data.get("lang", "ru")
        await callback.message.edit_reply_markup(
            reply_markup=deal_type_kb(data.get("deal_type"), selected, lang)
        )
    await callback.answer()


@router.callback_query(FilterState.choosing_type, F.data == "prop_done")
async def prop_done(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_type, F.data == "back_to_search")
async def back_from_type(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# ТИП ЗЕМЛИ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(FilterState.choosing_land, F.data.startswith("land_"))
async def set_land_type(callback: CallbackQuery, state: FSMContext):
    land = callback.data.replace("land_", "")
    await state.update_data(land_type=land)
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_land, F.data == "filter_type")
async def back_from_land(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.choosing_type)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(
        reply_markup=deal_type_kb(data.get("deal_type"), data.get("prop_types", []), lang)
    )
    await callback.answer()



# ─────────────────────────────────────────────────────────────────────────────
# АДРЕС
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "filter_address")
async def filter_address(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(FilterState.entering_address)
    await state.update_data(bot_msg_id=callback.message.message_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await callback.message.answer(
        t("enter_address", lang),
        reply_markup=skip_kb("skip_address", lang),
        disable_notification=True,
    )


@router.callback_query(FilterState.entering_address, F.data == "skip_address")
async def skip_address_btn(callback: CallbackQuery, state: FSMContext):
    await state.update_data(address=None, address_label=None)
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    bot_msg_id = data.get("bot_msg_id")
    await callback.message.delete()
    if bot_msg_id:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=bot_msg_id,
            reply_markup=search_dashboard_kb(data, lang),
        )
    await callback.answer()


@router.message(FilterState.entering_address)
async def set_address(message: Message, state: FSMContext):
    address = message.text.strip()
    label = address[:12] + "..." if len(address) > 12 else address
    await state.update_data(address=address, address_label=label)
    await message.delete()
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    bot_msg_id = data.get("bot_msg_id")
    if bot_msg_id:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=bot_msg_id,
            reply_markup=search_dashboard_kb(data, lang),
        )


# ─────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "filter_district")
async def filter_district(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(FilterState.choosing_district)
    await callback.message.edit_reply_markup(reply_markup=district_kb(data.get("district", []), lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_district, F.data.startswith("dist_") & ~F.data.endswith("_done"))
async def toggle_district(callback: CallbackQuery, state: FSMContext):
    district = callback.data.replace("dist_", "")
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected = data.get("district", [])
    if district in selected:
        selected.remove(district)
    else:
        selected.append(district)
    await state.update_data(district=selected)
    await callback.message.edit_reply_markup(reply_markup=district_kb(selected, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_district, F.data == "dist_done")
async def district_done(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_district, F.data == "back_to_search")
async def back_from_district(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# БЮДЖЕТ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "filter_budget")
async def filter_budget(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    deal_type = data.get("deal_type")
    if not deal_type:
        await callback.answer("⚠️ Сначала выберите Аренда или Продажа в разделе Тип", show_alert=True)
        return
    await state.set_state(FilterState.choosing_budget)
    await callback.message.edit_reply_markup(reply_markup=budget_kb(deal_type, data.get("budgets", []), lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_budget, F.data.startswith("budget_") & ~F.data.endswith("_done") & ~F.data.endswith("_manual"))
async def toggle_budget(callback: CallbackQuery, state: FSMContext):
    key = callback.data.replace("budget_", "")
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected = data.get("budgets", [])
    deal_type = data.get("deal_type")
    if key in selected:
        selected.remove(key)
    else:
        selected.append(key)
    await state.update_data(budgets=selected)
    await callback.message.edit_reply_markup(reply_markup=budget_kb(deal_type, selected, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_budget, F.data == "budget_manual")
async def budget_manual(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(FilterState.budget_manual_input)
    await state.update_data(bot_msg_id=callback.message.message_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        t("enter_budget", lang),
        reply_markup=skip_kb("skip_budget", lang),
        disable_notification=True,
    )
    await callback.answer()


@router.callback_query(FilterState.budget_manual_input, F.data == "skip_budget")
async def skip_budget(callback: CallbackQuery, state: FSMContext):
    await state.update_data(budget_manual=None)
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    bot_msg_id = data.get("bot_msg_id")
    await callback.message.delete()
    if bot_msg_id:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=bot_msg_id,
            reply_markup=search_dashboard_kb(data, lang),
        )
    await callback.answer()


@router.message(FilterState.budget_manual_input)
async def budget_manual_input(message: Message, state: FSMContext):
    import re as _re
    text = message.text.strip()
    price_min = None
    price_max = None
    range_match = _re.search(r"(\d+)\s*[-–]\s*(\d+)", text)
    if range_match:
        price_min = int(range_match.group(1))
        price_max = int(range_match.group(2))
    else:
        max_match = _re.search(r"до\s*(\d+)", text, _re.IGNORECASE)
        if max_match:
            price_max = int(max_match.group(1))
        min_match = _re.search(r"от\s*(\d+)", text, _re.IGNORECASE)
        if min_match:
            price_min = int(min_match.group(1))
        if not price_min and not price_max:
            num_match = _re.search(r"(\d+)", text)
            if num_match:
                price_max = int(num_match.group(1))
    await state.update_data(
        budget_manual=text, budget_label=text,
        price_min=price_min, price_max=price_max,
    )
    await message.delete()
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    bot_msg_id = data.get("bot_msg_id")
    if bot_msg_id:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=bot_msg_id,
            reply_markup=search_dashboard_kb(data, lang),
        )


@router.callback_query(FilterState.choosing_budget, F.data == "budget_done")
async def budget_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    budgets = data.get("budgets", [])
    deal_type = data.get("deal_type")
    ranges = PRICE_RANGES_RENT if deal_type == "rent" else PRICE_RANGES_SALE
    if budgets:
        labels = [l for k, l in ranges if k in budgets]
        await state.update_data(budget_label=" / ".join(labels))
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_budget, F.data == "back_to_search")
async def back_from_budget(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# ДЕТАЛИ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "filter_features")
async def filter_features(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(FilterState.choosing_features)
    await callback.message.edit_reply_markup(reply_markup=features_kb(data.get("features", []), lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_features, F.data.startswith("feat_") & ~F.data.endswith("_done"))
async def toggle_feature(callback: CallbackQuery, state: FSMContext):
    feature = callback.data.replace("feat_", "")
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected = data.get("features", [])
    if feature in selected:
        selected.remove(feature)
    else:
        selected.append(feature)
    await state.update_data(features=selected)
    await callback.message.edit_reply_markup(reply_markup=features_kb(selected, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_features, F.data == "feat_done")
async def features_done(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_features, F.data == "back_to_search")
async def back_from_features(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# ОТОПЛЕНИЕ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "filter_heating")
async def filter_heating(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(FilterState.choosing_heating)
    await callback.message.edit_reply_markup(reply_markup=heating_kb(data.get("heating", []), lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_heating, F.data.startswith("heat_") & ~F.data.endswith("_done"))
async def toggle_heating(callback: CallbackQuery, state: FSMContext):
    h = callback.data.replace("heat_", "")
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected = data.get("heating", [])
    if h in selected:
        selected.remove(h)
    else:
        selected.append(h)
    await state.update_data(heating=selected)
    await callback.message.edit_reply_markup(reply_markup=heating_kb(selected, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_heating, F.data == "heat_done")
async def heating_done(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_heating, F.data == "back_to_search")
async def back_from_heating(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# ПОКАЗАТЬ РЕЗУЛЬТАТЫ
# ─────────────────────────────────────────────────────────────────────────────

def format_property_card(prop: dict, lang: str = "ru") -> str:
    """Форматировать карточку объекта."""
    lines = []

    # Тип объекта (дом)
    if prop.get("property_type") == "house":
        lines.append("🏡 Дом")

    # Адрес с геоссылкой
    if prop.get("lat") and prop.get("lon"):
        maps_url = f"https://yandex.ru/maps/?pt={prop['lon']},{prop['lat']}&z=17"
        lines.append(f"📍 <a href='{maps_url}'>{prop['address']}</a>")
    elif prop.get("address"):
        lines.append(f"📍 {prop['address']}")

    # Параметры
    info = []
    if prop.get("rooms"):
        info.append(f"🛏 {prop['rooms']}")
    if prop.get("floor"):
        floor_str = str(prop["floor"])
        if prop.get("floors_total"):
            floor_str += f"/{prop['floors_total']}"
        info.append(f"🏢 {floor_str} эт.")
    if prop.get("area"):
        info.append(f"📐 {prop['area']} м²")
    if prop.get("area_land"):
        info.append(f"🌿 Участок: {prop['area_land']} сот.")
    if info:
        lines.append(" | ".join(info))

    # Цена
    if prop.get("price"):
        deal = prop.get("deal_type", "")
        suffix = "/мес" if deal == "rent" else ""
        price_str = f"💰 ${prop['price']:,}{suffix}"
        if prop.get("deposit"):
            price_str += f"\n💳 Депозит: ${prop['deposit']:,}"
        lines.append(price_str)

    # Цена в сезон
    if prop.get("price_season"):
        lines.append(f"☀️ Цена в сезон: ${prop['price_season']:,}/мес")

    # Удобства
    features = prop.get("features", [])
    if features:
        feat_icons = {
            "балкон": "🟢 Балкон",
            "духовка": "🟢 Духовка",
            "посудомойка": "🟢 Посудомойка",
            "ванна": "🛁 Ванна",
            "2_санузла": "🟢 2 санузла",
            "парковка": "🚘 Парковка",
            "питомцы": "🐶 Питомцы",
            "вид_на_море": "🌊 Вид на море",
            "вид_на_горы": "⛰️ Вид на горы",
            "вид_на_море_горы": "🌊 Вид на море/горы",
            "кондиционер": "🟢 Кондиционер",
            "2_кондиционера": "🟢 2 кондиционера+",
        }
        feat_list = [feat_icons.get(f, f) for f in features]
        lines.append("  ".join(feat_list))

    # Отопление
    heating = prop.get("heating", [])
    if heating:
        heat_map = {
            "центральное": "Центральное", "теплый_пол": "Тёплый пол", "карма": "Карма"
        }
        heat_list = [heat_map.get(h, h) for h in heating]
        lines.append(f"🔥 {', '.join(heat_list)}")

    # ID и дата
    source_code = prop.get("source_code", "")
    published_at = prop.get("published_at")
    date_str = published_at.strftime("%d.%m.%Y") if published_at else "—"
    if source_code:
        lines.append(f"─────────────\nID: {source_code}   {date_str}")

    return "\n".join(lines)


# Маппинг FSM-значений (из локалей) в DB-ключи (из парсера)
_ROOMS_TO_DB = {
    "студия": "Студия",
    "1+1": "1+1",
    "2+1": "2+1",
    "3+1": "3+1",
    "4+1+": "4+1",
    "studio": "Студия",
}

_HEATING_TO_DB = {
    "центральное": "центральное",
    "карма": "карма",
    "тёплый пол": "теплый_пол",
    "теплый пол": "теплый_пол",
    "central": "центральное",
    "karma": "карма",
    "underfloor heating": "теплый_пол",
}

_FEATURES_TO_DB = {
    "балкон": "балкон",
    "посудомоечная": "посудомойка",
    "духовой шкаф": "духовка",
    "ванна": "ванна",
    "2 санузла": "2_санузла",
    "2 кондиционера+": "2_кондиционера",
    "парковка": "парковка",
    "вид на море / горы": "вид_на_море",
    "можно с питомцами": "питомцы",
    "balcony": "балкон",
    "dishwasher": "посудомойка",
    "oven": "духовка",
    "bathtub": "ванна",
    "2 bathrooms": "2_санузла",
    "2+ ac units": "2_кондиционера",
    "parking": "парковка",
    "sea / mountain view": "вид_на_море",
    "pets allowed": "питомцы",
}



def build_filters_from_state(data: dict, telegram_id: int = None) -> dict:
    """Собрать фильтры из FSM данных."""
    filters = {}

    if data.get("deal_type"):
        filters["deal_type"] = data["deal_type"]

    if data.get("prop_types"):
        filters["property_type"] = data["prop_types"]

    if data.get("district"):
        filters["district"] = data["district"]

    if data.get("rooms"):
        rooms = data["rooms"]
        if isinstance(rooms, str):
            rooms = [rooms]
        db_rooms = [_ROOMS_TO_DB.get(r.lower(), r) for r in rooms]
        filters["rooms"] = db_rooms
        if "Студия" in db_rooms:
            prop_types = filters.get("property_type", [])
            if "apartment" in prop_types and "studio" not in prop_types:
                prop_types.append("studio")
            elif not prop_types:
                prop_types = ["apartment", "studio"]
            filters["property_type"] = prop_types

    if data.get("area_from"):
        filters["area_min"] = data["area_from"]

    if data.get("features"):
        filters["features"] = [
            _FEATURES_TO_DB.get(f.lower(), f.lower()) for f in data["features"]
        ]

    if data.get("heating"):
        filters["heating"] = [
            _HEATING_TO_DB.get(h.lower(), h.lower()) for h in data["heating"]
        ]

    # Бюджет — разбираем диапазон
    budgets = data.get("budgets", [])
    deal = data.get("deal_type", "rent")
    if budgets:
        from keyboards import PRICE_RANGES_RENT, PRICE_RANGES_SALE
        ranges = PRICE_RANGES_RENT if deal == "rent" else PRICE_RANGES_SALE
        range_map = {
            "rent_1": (0, 350), "rent_2": (350, 500), "rent_3": (500, 700),
            "rent_4": (700, 850), "rent_5": (850, 1000), "rent_6": (1000, 99999),
            "sale_1": (0, 70000), "sale_2": (70000, 120000), "sale_3": (120000, 180000),
            "sale_4": (180000, 260000), "sale_5": (260000, 380000), "sale_6": (380000, 9999999),
        }
        mins = [range_map[b][0] for b in budgets if b in range_map]
        maxs = [range_map[b][1] for b in budgets if b in range_map]
        if mins:
            filters["price_min"] = min(mins)
        if maxs:
            filters["price_max"] = max(maxs)

    # Ручной ввод бюджета
    if data.get("price_min") is not None and "price_min" not in filters:
        filters["price_min"] = data["price_min"]
    if data.get("price_max") is not None and "price_max" not in filters:
        filters["price_max"] = data["price_max"]

    # Глубина поиска
    fresh = data.get("fresh", "")
    if fresh:
        days_match = re.search(r"(\d+)", fresh)
        if days_match:
            filters["days_depth"] = int(days_match.group(1))
    else:
        effective_id = telegram_id or data.get("user_id")
        if effective_id and effective_id in OPERATOR_IDS:
            pass
        else:
            filters["days_depth"] = 30

    return filters


@router.callback_query(F.data == "filter_show")
async def filter_show(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.answer(t("searching", lang))

    filters = build_filters_from_state(data, telegram_id=callback.from_user.id)

    from db import get_property_ids, get_properties
    prop_ids = await get_property_ids(filters)

    if not prop_ids:
        await callback.message.answer(t("no_results", lang), disable_notification=True)
        return

    await state.update_data(search_results=prop_ids, search_index=0)

    props = await get_properties({"id_in": [prop_ids[0]]}, limit=1)
    if props:
        await show_property_card(callback.message, state, props[0], 1, len(prop_ids), lang)


# ─────────────────────────────────────────────────────────────────────────────
# ИЗБРАННОЕ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery, state: FSMContext):
    from db import get_user_id, get_favorites, get_favorites_count
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.answer()

    user_id = await get_user_id(callback.from_user.id)
    if not user_id:
        await callback.message.answer("⭐️ Избранное пусто.", disable_notification=True)
        return

    total = await get_favorites_count(user_id)
    if total == 0:
        await callback.message.answer("⭐️ <b>Избранное пусто.</b>\n\nДобавляйте объекты кнопкой ⭐️ В избранное.", disable_notification=True)
        return

    props = await get_favorites(user_id, offset=0, limit=1)
    if props:
        await state.update_data(fav_index=0)
        await show_favorite_card(callback.message, state, props[0], 1, total, lang)


async def show_favorite_card(message, state: FSMContext, prop, current: int, total: int, lang: str):
    from db import get_user_id
    admin   = await is_admin(message.chat.id)
    text = format_property_card(dict(prop), lang)
    kb = favorites_kb(current=current, total=total, prop_id=prop["id"], lang=lang)
    await _send_photos(message, prop)
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True, disable_notification=True)


async def _send_photos_to(bot, chat_id, prop):
    """Отправить все фото объекта в указанный chat_id."""
    photos   = prop.get("photos", []) or []
    refs     = [str(p) for p in photos if _CHANNEL_REF.match(str(p))]
    file_ids = [str(p) for p in photos if not _CHANNEL_REF.match(str(p))]

    logger.info(f"[photos_to] chat={chat_id} prop={prop.get('id')} refs={refs}")

    album_refs = refs
    if len(refs) <= 1:
        src_ch = prop.get("source_channel")
        msg_id = prop.get("message_id")
        if src_ch and msg_id:
            try:
                from handlers_channel import parser as _parser
                if _parser:
                    full = await _parser.get_album_photo_ids(int(src_ch), int(msg_id))
                    logger.info(f"[photos_to] telethon album: {full}")
                    if full:
                        album_refs = full
            except Exception as _e:
                logger.warning(f"[photos] Telethon: {_e}")

    if album_refs:
        ch_id   = int(album_refs[0].split(":")[0])
        msg_ids = [int(r.split(":")[1]) for r in album_refs]
        logger.info(f"[photos_to] copy_messages → chat={chat_id} from={ch_id} msgs={msg_ids}")
        try:
            await bot.copy_messages(
                chat_id=chat_id,
                from_chat_id=ch_id,
                message_ids=msg_ids,
                remove_caption=True,
                disable_notification=True,
            )
            logger.info(f"[photos_to] copy_messages OK")
            return
        except Exception as _e:
            logger.warning(f"[photos] copy_messages FAILED: {_e}")
            # Фолбэк: forward_messages сохраняет атрибуцию, но надёжнее
            try:
                await bot.forward_messages(
                    chat_id=chat_id,
                    from_chat_id=ch_id,
                    message_ids=msg_ids,
                    disable_notification=True,
                )
                logger.info(f"[photos_to] forward_messages OK")
                return
            except Exception as _e2:
                logger.warning(f"[photos] forward_messages FAILED: {_e2}")

    if file_ids:
        if len(file_ids) == 1:
            await bot.send_photo(chat_id=chat_id, photo=file_ids[0], disable_notification=True)
        else:
            await bot.send_media_group(
                chat_id=chat_id,
                media=[InputMediaPhoto(media=fid) for fid in file_ids],
                disable_notification=True,
            )


async def _send_photos(message, prop):
    await _send_photos_to(message.bot, message.chat.id, prop)


@router.callback_query(F.data.startswith("fav_") & ~F.data.startswith("fav_remove_") & ~F.data.startswith("fav_prev") & ~F.data.startswith("fav_next"))
async def toggle_favorite(callback: CallbackQuery, state: FSMContext):
    from db import get_user_id, add_to_favorites, remove_from_favorites, is_favorite_prop
    data = await state.get_data()
    lang = data.get("lang", "ru")
    prop_id = int(callback.data.replace("fav_", ""))

    user_id = await get_user_id(callback.from_user.id)
    if not user_id:
        await callback.answer("Ошибка: пользователь не найден", show_alert=True)
        return

    already = await is_favorite_prop(user_id, prop_id)
    if already:
        await remove_from_favorites(user_id, prop_id)
        await callback.answer("🗑 Удалено из избранного")
    else:
        await add_to_favorites(user_id, prop_id)
        await callback.answer("⭐️ Добавлено в избранное!")


@router.callback_query(F.data.startswith("fav_remove_"))
async def remove_favorite(callback: CallbackQuery, state: FSMContext):
    from db import get_user_id, remove_from_favorites, get_favorites, get_favorites_count
    data = await state.get_data()
    lang = data.get("lang", "ru")
    prop_id = int(callback.data.replace("fav_remove_", ""))

    user_id = await get_user_id(callback.from_user.id)
    if user_id:
        await remove_from_favorites(user_id, prop_id)

    await callback.answer("🗑 Удалено из избранного")

    total = await get_favorites_count(user_id) if user_id else 0
    if total == 0:
        await callback.message.answer("⭐️ Избранное теперь пусто.", disable_notification=True)
        return

    index = max(0, data.get("fav_index", 0) - 1)
    await state.update_data(fav_index=index)
    props = await get_favorites(user_id, offset=index, limit=1)
    if props:
        await show_favorite_card(callback.message, state, props[0], index + 1, total, lang)


@router.callback_query(F.data == "fav_prev")
async def fav_prev(callback: CallbackQuery, state: FSMContext):
    from db import get_user_id, get_favorites, get_favorites_count
    data = await state.get_data()
    lang = data.get("lang", "ru")
    index = data.get("fav_index", 0)
    if index <= 0:
        await callback.answer()
        return
    index -= 1
    await state.update_data(fav_index=index)
    user_id = await get_user_id(callback.from_user.id)
    total = await get_favorites_count(user_id)
    props = await get_favorites(user_id, offset=index, limit=1)
    await callback.answer()
    if props:
        await show_favorite_card(callback.message, state, props[0], index + 1, total, lang)


@router.callback_query(F.data == "fav_next")
async def fav_next(callback: CallbackQuery, state: FSMContext):
    from db import get_user_id, get_favorites, get_favorites_count
    data = await state.get_data()
    lang = data.get("lang", "ru")
    index = data.get("fav_index", 0)
    user_id = await get_user_id(callback.from_user.id)
    total = await get_favorites_count(user_id)
    if index >= total - 1:
        await callback.answer()
        return
    index += 1
    await state.update_data(fav_index=index)
    props = await get_favorites(user_id, offset=index, limit=1)
    await callback.answer()
    if props:
        await show_favorite_card(callback.message, state, props[0], index + 1, total, lang)


# ─────────────────────────────────────────────────────────────────────────────
# ПОДПИСКИ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "subscriptions")
async def show_subscriptions(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.answer()
    await callback.message.answer(
        f"🔔 <b>{t('subscriptions_title', lang)}</b>\n\n{t('subscriptions_text', lang)}",
        reply_markup=subscriptions_kb(has_active=False, lang=lang),
        disable_notification=True,
    )


@router.callback_query(F.data == "subscribe")
async def subscribe(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.answer(t("sub_activated", lang), show_alert=True)


@router.callback_query(F.data == "sub_disable")
async def sub_disable(callback: CallbackQuery):
    await callback.answer("🔕 Уведомления отключены")


@router.callback_query(F.data == "sub_enable")
async def sub_enable(callback: CallbackQuery):
    await callback.answer("🔔 Уведомления включены!")


# ─────────────────────────────────────────────────────────────────────────────
# НАПИСАТЬ НАМ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "contact_us")
async def contact_us(callback: CallbackQuery, state: FSMContext):
    await state.update_data(contact_prop_id=None)
    await state.set_state(FilterState.waiting_contact_message)
    await callback.answer()
    await callback.message.answer(
        "✉️ <b>Написать нам</b>\n\nОпишите что вы ищете — менеджер свяжется в течение 15 минут 👇",
        disable_notification=True,
    )


@router.callback_query(F.data.startswith("contact_") & ~F.data.endswith("_us"))
async def contact_from_card(callback: CallbackQuery, state: FSMContext):
    prop_id = callback.data.replace("contact_", "")
    await state.update_data(contact_prop_id=prop_id)
    await state.set_state(FilterState.waiting_contact_message)
    await callback.answer()
    await callback.message.answer("✉️ Напишите ваш вопрос — менеджер ответит в течение 15 минут 👇", disable_notification=True)


@router.message(FilterState.waiting_contact_message)
async def handle_contact_message(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    prop_id = data.get("contact_prop_id")
    user = message.from_user

    staff_text = (
        f"📩 <b>Новая заявка!</b>\n\n"
        f"👤 Имя: {user.full_name}\n"
        f"🔗 Username: @{user.username or '—'}\n"
        f"🆔 TG ID: <code>{user.id}</code>\n"
        f"\n💬 Сообщение:\n{message.text}"
    )

    prop = None
    if prop_id and prop_id != "0":
        from db import pool
        async with pool.acquire() as conn:
            prop = await conn.fetchrow("SELECT * FROM properties WHERE id=$1", int(prop_id))

    for op_id in OPERATOR_IDS:
        await message.bot.send_message(
            chat_id=op_id,
            text=staff_text,
            disable_notification=True,
        )

        if prop:
            await _send_photos_to(message.bot, op_id, prop)

            card_text = format_property_card(dict(prop), "ru")
            op_kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить просмотр",
                        callback_data=f"op_confirm_{user.id}_{prop_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="💬 Ответить клиенту",
                        callback_data=f"op_reply_{user.id}_{prop_id or 0}",
                    ),
                    InlineKeyboardButton(
                        text="📞 Написать владельцу",
                        callback_data=f"op_owner_{prop_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔍 Проверить объект",
                        callback_data=f"op_check_{prop_id}",
                    ),
                ],
            ])
            await message.bot.send_message(
                chat_id=op_id,
                text=card_text,
                reply_markup=op_kb,
                disable_notification=True,
                disable_web_page_preview=True,
            )

    await state.set_state(None)
    await message.answer("✅ Ваш запрос отправлен!\nМенеджер свяжется с вами в течение 15 минут.", disable_notification=True)


@router.message(FilterState.in_dialog)
async def handle_dialog_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    operator_id = data.get("dialog_operator_id")
    prop_id = data.get("dialog_prop_id", 0)
    user = message.from_user

    if not operator_id:
        await state.set_state(None)
        return

    await message.bot.send_message(
        chat_id=operator_id,
        text=(
            f"💬 <b>Ответ клиента {user.full_name}:</b>\n\n"
            f"{message.text}"
        ),
        parse_mode="HTML",
    )
    kb_op = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Ответить",
            callback_data=f"op_reply_{user.id}_{prop_id}",
        )]
    ])
    await message.bot.send_message(
        chat_id=operator_id,
        text="Выберите действие:",
        reply_markup=kb_op,
        disable_notification=True,
    )

    kb_client = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🏠 Главное меню" if lang == "ru" else "🏠 Main menu",
            callback_data="end_dialog",
        )]
    ])
    await message.answer(
        "✅ Сообщение отправлено менеджеру!" if lang == "ru" else "✅ Message sent to the manager!",
        reply_markup=kb_client,
        disable_notification=True,
    )


@router.callback_query(F.data == "end_dialog")
async def end_dialog(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    saved = {k: v for k, v in data.items() if k in ["lang", "user_id", "search_results", "search_index"]}
    await state.clear()
    await state.update_data(**saved)
    await callback.answer()
    await _show_main_menu(callback.message, state)


# ─────────────────────────────────────────────────────────────────────────────
# АДМИНПАНЕЛЬ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.answer()
    await callback.message.answer("⚙️ <b>Админпанель</b>", reply_markup=admin_panel_kb(lang), disable_notification=True)


@router.callback_query(F.data == "admin_requests")
async def admin_requests(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("📋 <b>Заявки</b>\n\n<i>Здесь появятся входящие заявки от клиентов.</i>", disable_notification=True)


@router.callback_query(F.data == "admin_search")
async def admin_search(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.answer("🔍 Подбор объектов для клиента:", reply_markup=search_dashboard_kb(data, lang), disable_notification=True)


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("📊 <b>Статистика</b>\n\n<i>Будет доступна после подключения базы данных.</i>", disable_notification=True)


@router.callback_query(F.data == "admin_clients")
async def admin_clients(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("👥 <b>Клиенты</b>\n\n<i>База клиентов появится после подключения базы данных.</i>", disable_notification=True)


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminState.waiting_broadcast)
    await callback.message.answer("📤 Введите текст рассылки:", disable_notification=True)


@router.message(AdminState.waiting_broadcast)
async def handle_broadcast(message: Message, state: FSMContext):
    await state.set_state(None)
    # TODO: разослать всем пользователям
    await message.answer("✅ Рассылка запущена!", disable_notification=True)






logger = logging.getLogger(__name__)


async def _resolve_file_ids(bot, album_refs: list[str]) -> list[str]:
    """
    Пересылает фото альбома в STORAGE_CHAT_ID, забирает file_id,
    удаляет сообщения из хранилища. Возвращает список file_id в том же порядке.
    """
    from config import STORAGE_CHAT_ID
    if not STORAGE_CHAT_ID or not album_refs:
        logger.warning("[photos] STORAGE_CHAT_ID не задан или пустой album_refs")
        return []

    tasks = [
        bot.forward_message(
            chat_id=STORAGE_CHAT_ID,
            from_chat_id=int(r.split(":")[0]),
            message_id=int(r.split(":")[1]),
            disable_notification=True,
        )
        for r in album_refs
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    file_ids: list[str] = []
    storage_ids: list[int] = []
    for ref, res in zip(album_refs, results):
        if isinstance(res, Exception):
            logger.warning(f"[photos] forward {ref} → {res}")
            continue
        storage_ids.append(res.message_id)
        if res.photo:
            file_ids.append(res.photo[-1].file_id)

    logger.info(f"[photos] resolved {len(file_ids)}/{len(album_refs)} file_ids via storage")

    if storage_ids:
        try:
            await bot.delete_messages(chat_id=STORAGE_CHAT_ID, message_ids=storage_ids)
        except Exception as e:
            logger.warning(f"[photos] delete from storage: {e}")

    return file_ids


async def show_property_card(message, state: FSMContext, prop, current: int, total: int, lang: str):
    """Показать карточку объекта."""
    from db import get_user_id, is_favorite_prop
    admin   = await is_admin(message.chat.id)
    user_id = await get_user_id(message.chat.id)
    is_fav  = await is_favorite_prop(user_id, prop["id"]) if user_id else False

    text = format_property_card(dict(prop), lang)
    kb = property_card_kb(
        current=current,
        total=total,
        prop_id=prop["id"],
        is_favorite=is_fav,
        is_admin=admin,
        lang=lang,
    )

    await _send_photos(message, prop)
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True, disable_notification=True)


# ─────────────────────────────────────────────────────────────────────────────
# НАВИГАЦИЯ ПО КАРТОЧКАМ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "card_prev")
async def card_prev(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    results = data.get("search_results", [])
    index = data.get("search_index", 0)

    if not results or index <= 0:
        await callback.answer()
        return

    index -= 1
    await state.update_data(search_index=index)

    from db import get_properties
    props = await get_properties({"id_in": [results[index]]}, limit=1)
    if props:
        await callback.answer()
        await show_property_card(callback.message, state, props[0], index + 1, len(results), lang)


@router.callback_query(F.data == "card_next")
async def card_next(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    results = data.get("search_results", [])
    index = data.get("search_index", 0)

    if not results or index >= len(results) - 1:
        await callback.answer()
        return

    index += 1
    await state.update_data(search_index=index)

    from db import get_properties
    props = await get_properties({"id_in": [results[index]]}, limit=1)
    if props:
        await callback.answer()
        await show_property_card(callback.message, state, props[0], index + 1, len(results), lang)


@router.callback_query(F.data == "card_count")
async def card_count(callback: CallbackQuery):
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# INLINE — пересылка объекта клиенту
# ─────────────────────────────────────────────────────────────────────────────

@router.inline_query(F.query.startswith("prop_"))
async def inline_property(query: InlineQuery):
    try:
        prop_id = int(query.query.replace("prop_", ""))
    except ValueError:
        await query.answer([])
        return

    from db import pool
    async with pool.acquire() as conn:
        prop = await conn.fetchrow("SELECT * FROM properties WHERE id=$1", prop_id)

    if not prop:
        await query.answer([])
        return

    prop = dict(prop)
    text = format_property_card(prop, "ru")

    address = prop.get("address") or "Объект"
    rooms = prop.get("rooms") or ""
    price = prop.get("price")
    deal = prop.get("deal_type", "")
    price_str = f"${price:,}" + ("/мес" if deal == "rent" else "") if price else ""
    description = ", ".join(filter(None, [rooms, price_str]))

    result = InlineQueryResultArticle(
        id=str(prop_id),
        title=f"🏠 {address}",
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        ),
    )

    await query.answer([result], cache_time=1)


# ─────────────────────────────────────────────────────────────────────────────
# ОПЕРАТОРЫ — подтверждение / отклонение просмотра
# ─────────────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("op_decline_"))
async def op_decline_viewing(callback: CallbackQuery):
    client_id = int(callback.data.split("_")[2])
    await callback.answer("Отклонено")
    await callback.bot.send_message(
        chat_id=client_id,
        text=(
            "😔 К сожалению, по данному объекту просмотр невозможен.\n"
            "Наш менеджер подберёт вам другие варианты."
        ),
    )
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("op_owner_"))
async def op_owner(callback: CallbackQuery):
    import re as _re
    prop_id = callback.data.split("_")[2]
    await callback.answer()

    from db import pool
    async with pool.acquire() as conn:
        prop = await conn.fetchrow(
            "SELECT source_code, deal_type FROM properties WHERE id=$1",
            int(prop_id)
        )

    if not prop:
        await callback.message.answer("❌ Объект не найден", disable_notification=True)
        return

    from google_sheets import get_owner_phone
    phone = await get_owner_phone(prop["source_code"], prop["deal_type"])

    if not phone:
        await callback.message.answer(
            f"❌ Номер не найден для объекта {prop['source_code']}",
            disable_notification=True,
        )
        return

    phone_clean = _re.sub(r"[^\d+]", "", str(phone))
    if not phone_clean.startswith("+"):
        phone_clean = "+" + phone_clean

    wa_url = f"https://wa.me/{phone_clean.replace('+', '')}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💬 WhatsApp {phone_clean}",
            url=wa_url,
        )],
    ])
    await callback.message.answer(
        f"📞 Собственник {prop['source_code']}:\n{phone_clean}",
        reply_markup=kb,
        disable_notification=True,
    )


@router.callback_query(F.data.startswith("op_check_"))
async def op_check(callback: CallbackQuery):
    import re as _re
    prop_id = callback.data.split("_")[2]
    await callback.answer()

    from db import pool
    async with pool.acquire() as conn:
        prop = await conn.fetchrow(
            "SELECT source_code, deal_type FROM properties WHERE id=$1",
            int(prop_id)
        )

    if not prop:
        await callback.message.answer("❌ Объект не найден", disable_notification=True)
        return

    from google_sheets import get_owner_phone
    phone = await get_owner_phone(prop["source_code"], prop["deal_type"])

    if not phone:
        await callback.message.answer(
            f"❌ Номер не найден для объекта {prop['source_code']}",
            disable_notification=True,
        )
        return

    phone_clean = _re.sub(r"[^\d+]", "", str(phone))
    if not phone_clean.startswith("+"):
        phone_clean = "+" + phone_clean

    wa_url = f"https://wa.me/{phone_clean.replace('+', '')}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💬 WhatsApp {phone_clean}",
            url=wa_url,
        )],
    ])
    await callback.message.answer(
        f"📞 Собственник {prop['source_code']}:\n{phone_clean}",
        reply_markup=kb,
        disable_notification=True,
    )
