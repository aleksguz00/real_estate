# handlers_user.py

import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from keyboards import (
    language_kb, subscription_kb, main_menu_kb, search_dashboard_kb,
    fresh_kb, rooms_kb, area_kb, deal_type_kb, land_type_kb, commercial_type_kb,
    district_kb, budget_kb, features_kb, heating_kb, property_card_kb,
    favorites_kb, subscriptions_kb, bingo_kb, admin_panel_kb, skip_kb,
    PRICE_RANGES_RENT, PRICE_RANGES_SALE, FRESHNESS_OPTIONS,
)
from locales import t, tl
from filters_fsm import FilterState, AdminState
from db import save_user, is_admin

router = Router()

WELCOME_PHOTO = "AgACAgIAAxkBAANcaezGoxZ_T_N7hNePlMVMkG7KS0kAAloVaxtOiWhLDvo0SciHv48BAAMCAAN5AAM7BA"
CHANNEL_USERNAME = "BatumiHome24"
CHANNEL_URL = "https://t.me/BatumiHome24"


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
    await state.clear()
    await save_user(message.from_user.id, message.from_user.username)
    try:
        await message.answer_photo(
            photo=WELCOME_PHOTO,
            caption="Выберите язык / Choose language:",
            reply_markup=language_kb(),
        )
    except Exception:
        await message.answer(
            "Выберите язык / Choose language:",
            reply_markup=language_kb(),
        )


# ─────────────────────────────────────────────────────────────────────────────
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
        await message.answer_photo(photo=WELCOME_PHOTO, caption=text, reply_markup=kb)
    except Exception:
        await message.answer(text, reply_markup=kb)


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
        await message.answer("⚠️ Введите число, например: 21")


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
        await message.answer(t("error_number", lang))


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
        await state.update_data(prop_types=["commercial"], commercial_type=None)
        await state.set_state(FilterState.choosing_commercial)
        await callback.message.edit_reply_markup(reply_markup=commercial_type_kb(lang=lang))
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
# ТИП КОММЕРЦИИ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(FilterState.choosing_commercial, F.data.startswith("commercial_"))
async def set_commercial(callback: CallbackQuery, state: FSMContext):
    comm = callback.data.replace("commercial_", "")
    await state.update_data(commercial_type=comm)
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_reply_markup(reply_markup=search_dashboard_kb(data, lang))
    await callback.answer()


@router.callback_query(FilterState.choosing_commercial, F.data == "filter_type")
async def back_from_commercial(callback: CallbackQuery, state: FSMContext):
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
    text = message.text.strip()
    await state.update_data(budget_manual=text, budget_label=text)
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

    # Адрес
    if prop.get("address"):
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

    # Оплата за первый и последний месяц
    if prop.get("deal_type") == "rent":
        lines.append("💳 Оплата за первый и последний месяц")

    # Цена в сезон
    if prop.get("price_season"):
        lines.append(f"☀️ Цена в сезон: ${prop['price_season']:,}/мес")

    # Удобства
    features = prop.get("features", [])
    if features:
        feat_map = {
            "балкон": "Балкон", "ванна": "Ванна", "2_санузла": "2 санузла",
            "парковка": "Парковка", "духовка": "Духовой шкаф",
            "посудомойка": "Посудомойка", "вид_на_море": "Вид на море/горы",
            "питомцы": "Питомцы ✓", "кондиционер": "Кондиционер",
            "2_кондиционера": "2 кондиционера+",
        }
        feat_list = [feat_map.get(f, f) for f in features]
        lines.append("✅ " + "  ✅ ".join(feat_list))

    # Отопление
    heating = prop.get("heating", [])
    if heating:
        heat_map = {
            "центральное": "Центральное", "теплый_пол": "Тёплый пол", "карма": "Карма"
        }
        heat_list = [heat_map.get(h, h) for h in heating]
        lines.append(f"🔥 {', '.join(heat_list)}")

    return "\n".join(lines)


# Маппинг FSM-значений (из локалей) в DB-ключи (из парсера)
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


def build_filters_from_state(data: dict) -> dict:
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
        filters["rooms"] = rooms

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

    # Глубина поиска
    fresh = data.get("fresh", "")
    if fresh:
        days_match = __import__("re").search(r"(\d+)", fresh)
        if days_match:
            filters["days_depth"] = int(days_match.group(1))

    return filters


@router.callback_query(F.data == "filter_show")
async def filter_show(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.answer(t("searching", lang))

    filters = build_filters_from_state(data)

    from db import get_properties
    props = await get_properties(filters, limit=10)

    if not props:
        await callback.message.answer(t("no_results", lang))
        return

    # Сохраняем результаты в FSM для пагинации
    prop_ids = [p["id"] for p in props]
    await state.update_data(search_results=prop_ids, search_index=0)

    # Показываем первый объект
    await show_property_card(callback.message, state, props[0], 1, len(props), lang)


# ─────────────────────────────────────────────────────────────────────────────
# ИЗБРАННОЕ
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "⭐️ <b>Избранное</b>\n\n<i>Здесь появятся сохранённые объекты.</i>"
    )


@router.callback_query(F.data.startswith("fav_") & ~F.data.startswith("fav_remove_"))
async def toggle_favorite(callback: CallbackQuery):
    await callback.answer("⭐️ Добавлено в избранное!")


@router.callback_query(F.data.startswith("fav_remove_"))
async def remove_favorite(callback: CallbackQuery):
    await callback.answer("🗑 Удалено из избранного")


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
        "✉️ <b>Написать нам</b>\n\nОпишите что вы ищете — менеджер свяжется в течение 15 минут 👇"
    )


@router.callback_query(F.data.startswith("contact_") & ~F.data.endswith("_us"))
async def contact_from_card(callback: CallbackQuery, state: FSMContext):
    prop_id = callback.data.replace("contact_", "")
    await state.update_data(contact_prop_id=prop_id)
    await state.set_state(FilterState.waiting_contact_message)
    await callback.answer()
    await callback.message.answer("✉️ Напишите ваш вопрос — менеджер ответит в течение 15 минут 👇")


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
    )
    if prop_id and prop_id != "0":
        staff_text += f"🏠 Объект: #{prop_id}\n"
    staff_text += f"\n💬 Сообщение:\n{message.text}"

    staff_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить просмотр", callback_data=f"op_confirm_{user.id}_{prop_id or 0}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"op_decline_{user.id}"),
        ]
    ])

    # TODO: раскомментировать после настройки STAFF_GROUP_ID
    # await message.bot.send_message(STAFF_GROUP_ID, staff_text, reply_markup=staff_kb)

    await state.set_state(None)
    await message.answer("✅ Ваш запрос отправлен!\nМенеджер свяжется с вами в течение 15 минут.")


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
    await callback.message.answer("⚙️ <b>Админпанель</b>", reply_markup=admin_panel_kb(lang))


@router.callback_query(F.data == "admin_requests")
async def admin_requests(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("📋 <b>Заявки</b>\n\n<i>Здесь появятся входящие заявки от клиентов.</i>")


@router.callback_query(F.data == "admin_search")
async def admin_search(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.answer("🔍 Подбор объектов для клиента:", reply_markup=search_dashboard_kb(data, lang))


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("📊 <b>Статистика</b>\n\n<i>Будет доступна после подключения базы данных.</i>")


@router.callback_query(F.data == "admin_clients")
async def admin_clients(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("👥 <b>Клиенты</b>\n\n<i>База клиентов появится после подключения базы данных.</i>")


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminState.waiting_broadcast)
    await callback.message.answer("📤 Введите текст рассылки:")


@router.message(AdminState.waiting_broadcast)
async def handle_broadcast(message: Message, state: FSMContext):
    await state.set_state(None)
    # TODO: разослать всем пользователям
    await message.answer("✅ Рассылка запущена!")


# ─────────────────────────────────────────────────────────────────────────────
# БАТУМСКОЕ БИНГО
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "bingo")
async def start_bingo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    ad = random.choice(BINGO_ADS)
    await state.update_data(bingo_checked=[], bingo_ad=ad)
    await state.set_state(FilterState.bingo_game)
    await callback.answer()
    items = tl("bingo_items", lang)
    items_text = "\n".join(f"☐ {item}" for item in items)
    await callback.message.answer(
        f"{t('bingo_title', lang)}\n\n📋 <i>{ad}</i>\n\n{t('bingo_find', lang)}\n\n{items_text}",
        reply_markup=bingo_kb([], lang),
    )


@router.callback_query(FilterState.bingo_game, F.data.startswith("bingo_") & ~F.data.endswith("_result"))
async def toggle_bingo(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.replace("bingo_", ""))
    data = await state.get_data()
    lang = data.get("lang", "ru")
    checked = data.get("bingo_checked", [])
    if idx in checked:
        checked.remove(idx)
    else:
        checked.append(idx)
    await state.update_data(bingo_checked=checked)
    ad = data.get("bingo_ad", "")
    items = tl("bingo_items", lang)
    items_text = "\n".join(
        f"{'✅' if i in checked else '☐'} {item}"
        for i, item in enumerate(items)
    )
    await callback.message.edit_text(
        f"{t('bingo_title', lang)}\n\n📋 <i>{ad}</i>\n\n{t('bingo_find', lang)}\n\n{items_text}",
        reply_markup=bingo_kb(checked, lang),
    )
    await callback.answer()


@router.callback_query(FilterState.bingo_game, F.data == "bingo_result")
async def bingo_result(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    checked = data.get("bingo_checked", [])
    await state.set_state(None)
    await callback.answer()
    await callback.message.answer(f"🎰 <b>Результат:</b>\n\n{bingo_result_text(len(checked))}")


async def show_property_card(message, state: FSMContext, prop, current: int, total: int, lang: str):
    """Показать карточку объекта."""
    admin = await is_admin(message.chat.id)

    text = format_property_card(dict(prop), lang)
    kb = property_card_kb(
        current=current,
        total=total,
        prop_id=prop["id"],
        is_admin=admin,
        lang=lang,
    )

    # Пересылаем фото из канала
    photos = prop.get("photos", [])
    if photos:
        try:
            first_photo = str(photos[0])
            if ":" in first_photo:
                channel_id, msg_id = first_photo.split(":")
                await message.bot.forward_message(
                    chat_id=message.chat.id,
                    from_chat_id=int(channel_id),
                    message_id=int(msg_id),
                )
        except Exception as e:
            pass

    await message.answer(text, reply_markup=kb)


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
