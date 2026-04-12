from aiogram import Router, F
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                            InlineKeyboardButton, ReplyKeyboardMarkup,
                            KeyboardButton, ReplyKeyboardRemove)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from filters_fsm import FilterState
from db import save_user, save_phone, save_filter, get_user_id


router = Router()

RENT_SUBTYPES = {
    "rent_longterm": "📅 Долгосрочная",
    "rent_daily":    "🌙 Посуточно",
}

SALE_SUBTYPES = {
    "sale_apartment":  "🏢 Квартиры",
    "sale_house":      "🏡 Дома / Виллы",
    "sale_land":       "🌿 Земельные участки",
    "sale_commercial": "💼 Коммерция",
}

COMMERCIAL_SUBTYPES = {
    "hotel":           "🏨 Отель",
    "casino":          "🎰 Казино",
    "restaurant":      "🍽️ Ресторан / Кафе",
    "floor":           "🏗️ Целый этаж",
    "land_commercial": "🌐 Участок под коммерцию",
    "office":          "🏪 Офис / Торговая площадь",
}

DISTRICTS = [
    "Центр",
    "Старый Батуми",
    "Новый Бульвар",
    "Гонио",
    "Квариати",
    "Махинджаури",
    "Чакви",
    "Кобулети",
]

HEATING_TYPES = [
    "🔥 Центральное",
    "⚡ Электрическое",
    "❄️ Кондиционер",
    "🦶 Теплый пол",
    "🪔 Карма",
]

FEATURES = [
    "🚿 2 санузла",
    "🛁 Ванна",
    "🌅 Балкон / Терраса",
    "🌊 Вид на море",
    "🅿️ Парковка",
    "🍳 Духовка",
    "🫧 Посудомойка",
    "👕 Сушильная машина",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад",       callback_data="back"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
        ]
    ])


def get_multi_keyboard(options: list[str], selected: list[str], prefix: str) -> InlineKeyboardMarkup:
    keyboard = []
    for option in options:
        mark = "✅ " if option in selected else ""
        keyboard.append([
            InlineKeyboardButton(text=f"{mark}{option}", callback_data=f"{prefix}_{option}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back"),
        InlineKeyboardButton(text="✅ Готово", callback_data=f"{prefix}_done"),
    ])
    keyboard.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _subtypes_kb(subtypes: dict) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=f"subtype_{key}")] for key, label in subtypes.items()]
    rows.append([
        InlineKeyboardButton(text="◀️ Назад",       callback_data="back"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _commercial_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=f"commercial_{key}")] for key, label in COMMERCIAL_SUBTYPES.items()]
    rows.append([
        InlineKeyboardButton(text="◀️ Назад",       callback_data="back"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _edit_bot_msg(message: Message, state: FSMContext, text: str, reply_markup=None):
    """Редактирует сохранённое сообщение бота (используется из текстовых хендлеров)."""
    data = await state.get_data()
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=data["bot_msg_id"],
        text=text,
        reply_markup=reply_markup,
    )


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Начать поиск", callback_data="start_search")],
    ])


def _deal_kb() -> InlineKeyboardMarkup:
    """Клавиатура первого шага с кнопкой возврата в главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Аренда",  callback_data="deal_rent")],
        [InlineKeyboardButton(text="💰 Продажа", callback_data="deal_sale")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def start_handler(message: Message):
    await save_user(message.from_user.id, message.from_user.username)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером", request_contact=True)],
            [KeyboardButton(text="Пропустить")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(
        "Добро пожаловать в Kaufman Estate Bot 🏠\n\n"
        "Для удобства работы поделитесь номером телефона - "
        "это поможет нашим менеджерам связаться с вами.",
        reply_markup=kb,
    )


@router.message(F.contact)
async def handle_contact(message: Message):
    await save_phone(message.from_user.id, message.contact.phone_number)
    await message.delete()
    await _show_welcome(message)


@router.message(F.text == "Пропустить")
async def handle_skip_phone(message: Message):
    await message.delete()
    await _show_welcome(message)


async def _show_welcome(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Начать поиск", callback_data="start_search")]
    ])
    # Сначала убираем ReplyKeyboard, потом отдельным сообщением - инлайн-кнопка
    await message.answer(
        "Что я умею:\n"
        "📍 Фильтровать по районам: Центр, Старый Батуми, Новый Бульвар, Гонио, Квариати, Махинджаури, Чакви, Кобулети.\n"
        "🎯 Искать по точным параметрам: площадь, этажность и технические детали.\n"
        "⭐️ Добавлять в избранное: сохраняйте лучшие варианты, чтобы не потерять их.\n"
        "🔔 Уведомлять о новинках: настройте свои критерии, и я пришлю новый объект сразу, как он появится.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("Нажмите кнопку ниже, чтобы начать поиск! 👇", reply_markup=kb)


# ---------------------------------------------------------------------------
# Шаг 1: Аренда / Продажа
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data == "main_menu")
async def main_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Главное меню - выберите действие:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "start_search")
async def choose_deal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.choosing_deal)
    await callback.message.edit_text("Выберите категорию:", reply_markup=_deal_kb())
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 2: Подтип
# ---------------------------------------------------------------------------

@router.callback_query(FilterState.choosing_deal, lambda c: c.data.startswith("deal_"))
async def set_deal(callback: CallbackQuery, state: FSMContext):
    deal = callback.data.replace("deal_", "")
    await state.update_data(deal_type=deal, subtype=None)
    await state.set_state(FilterState.choosing_subtype)

    if deal == "rent":
        await callback.message.edit_text("Выберите тип аренды:", reply_markup=_subtypes_kb(RENT_SUBTYPES))
    else:
        await callback.message.edit_text("Выберите категорию:", reply_markup=_subtypes_kb(SALE_SUBTYPES))
    await callback.answer()


@router.callback_query(FilterState.choosing_subtype, lambda c: c.data == "back")
async def back_to_deal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.choosing_deal)
    await callback.message.edit_text("Выберите категорию:", reply_markup=_deal_kb())
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 3: Подтип коммерции
# ---------------------------------------------------------------------------

@router.callback_query(FilterState.choosing_subtype, lambda c: c.data.startswith("subtype_"))
async def set_subtype(callback: CallbackQuery, state: FSMContext):
    deal_type = callback.data.replace("subtype_", "")

    if deal_type == "sale_commercial":
        await state.update_data(deal_type=deal_type)
        await state.set_state(FilterState.choosing_commercial)
        await callback.message.edit_text("Выберите подтип коммерции:", reply_markup=_commercial_kb())
    else:
        await state.update_data(deal_type=deal_type, district=[])
        await state.set_state(FilterState.choosing_district)
        await callback.message.edit_text(
            "Выберите районы (можно несколько):",
            reply_markup=get_multi_keyboard(DISTRICTS, [], "district")
        )
    await callback.answer()


@router.callback_query(FilterState.choosing_commercial, lambda c: c.data == "back")
async def back_to_subtype(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.choosing_subtype)
    await callback.message.edit_text("Выберите категорию:", reply_markup=_subtypes_kb(SALE_SUBTYPES))
    await callback.answer()


@router.callback_query(FilterState.choosing_commercial, lambda c: c.data.startswith("commercial_"))
async def set_commercial(callback: CallbackQuery, state: FSMContext):
    subtype = callback.data.replace("commercial_", "")
    await state.update_data(subtype=subtype, district=[])
    await state.set_state(FilterState.choosing_district)
    await callback.message.edit_text(
        "Выберите районы (можно несколько):",
        reply_markup=get_multi_keyboard(DISTRICTS, [], "district")
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 4: Районы
# ---------------------------------------------------------------------------

@router.callback_query(FilterState.choosing_district, lambda c: c.data == "back")
async def back_from_district(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    deal_type = data.get("deal_type", "")

    if deal_type == "sale_commercial":
        await state.set_state(FilterState.choosing_commercial)
        await callback.message.edit_text("Выберите подтип коммерции:", reply_markup=_commercial_kb())
    elif deal_type.startswith("rent"):
        await state.set_state(FilterState.choosing_subtype)
        await callback.message.edit_text("Выберите тип аренды:", reply_markup=_subtypes_kb(RENT_SUBTYPES))
    else:
        await state.set_state(FilterState.choosing_subtype)
        await callback.message.edit_text("Выберите категорию:", reply_markup=_subtypes_kb(SALE_SUBTYPES))
    await callback.answer()


@router.callback_query(
    FilterState.choosing_district,
    lambda c: c.data.startswith("district_") and c.data != "district_done"
)
async def toggle_district(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("district", [])
    district = callback.data.replace("district_", "")

    if district in selected:
        selected.remove(district)
    else:
        selected.append(district)

    await state.update_data(district=selected)
    await callback.message.edit_reply_markup(
        reply_markup=get_multi_keyboard(DISTRICTS, selected, "district")
    )
    await callback.answer()


@router.callback_query(FilterState.choosing_district, lambda c: c.data == "district_done")
async def district_done(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.area_from)
    # С этого момента начинается фаза текстового ввода.
    # Сохраняем message_id - все следующие шаги будут редактировать это же сообщение.
    await state.update_data(bot_msg_id=callback.message.message_id)
    await callback.message.edit_text("Введите площадь ОТ (м²):", reply_markup=back_button())
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаги 5–8: Площадь и этажность (текстовый ввод)
# ---------------------------------------------------------------------------

@router.callback_query(FilterState.area_from, lambda c: c.data == "back")
async def back_to_district(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(FilterState.choosing_district)
    await callback.message.edit_text(
        "Выберите районы (можно несколько):",
        reply_markup=get_multi_keyboard(DISTRICTS, data.get("district", []), "district")
    )
    await callback.answer()


@router.message(FilterState.area_from)
async def set_area_from(message: Message, state: FSMContext):
    await state.update_data(area_from=int(message.text))
    await state.set_state(FilterState.area_to)
    await message.delete()
    await _edit_bot_msg(message, state, "Введите площадь ДО (м²):", back_button())


@router.callback_query(FilterState.area_to, lambda c: c.data == "back")
async def back_to_area_from(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.area_from)
    await callback.message.edit_text("Введите площадь ОТ (м²):", reply_markup=back_button())
    await callback.answer()


@router.message(FilterState.area_to)
async def set_area_to(message: Message, state: FSMContext):
    await state.update_data(area_to=int(message.text))
    await state.set_state(FilterState.floor_from)
    await message.delete()
    await _edit_bot_msg(message, state, "Введите этаж ОТ:", back_button())


@router.callback_query(FilterState.floor_from, lambda c: c.data == "back")
async def back_to_area_to(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.area_to)
    await callback.message.edit_text("Введите площадь ДО (м²):", reply_markup=back_button())
    await callback.answer()


@router.message(FilterState.floor_from)
async def set_floor_from(message: Message, state: FSMContext):
    await state.update_data(floor_from=int(message.text))
    await state.set_state(FilterState.floor_to)
    await message.delete()
    await _edit_bot_msg(message, state, "Введите этаж ДО:", back_button())


@router.callback_query(FilterState.floor_to, lambda c: c.data == "back")
async def back_to_floor_from(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.floor_from)
    await callback.message.edit_text("Введите этаж ОТ:", reply_markup=back_button())
    await callback.answer()


@router.message(FilterState.floor_to)
async def set_floor_to(message: Message, state: FSMContext):
    await state.update_data(floor_to=int(message.text), heating=[])
    await state.set_state(FilterState.heating)
    await message.delete()
    await _edit_bot_msg(message, state, "Выберите тип отопления:",
                        get_multi_keyboard(HEATING_TYPES, [], "heating"))


# ---------------------------------------------------------------------------
# Шаг 9: Отопление
# ---------------------------------------------------------------------------

@router.callback_query(FilterState.heating, lambda c: c.data == "back")
async def back_to_floor_to(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.floor_to)
    await callback.message.edit_text("Введите этаж ДО:", reply_markup=back_button())
    await callback.answer()


@router.callback_query(
    FilterState.heating,
    lambda c: c.data.startswith("heating_") and c.data != "heating_done"
)
async def toggle_heating(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("heating", [])
    value = callback.data.replace("heating_", "")

    if value in selected:
        selected.remove(value)
    else:
        selected.append(value)

    await state.update_data(heating=selected)
    await callback.message.edit_reply_markup(
        reply_markup=get_multi_keyboard(HEATING_TYPES, selected, "heating")
    )
    await callback.answer()


@router.callback_query(FilterState.heating, lambda c: c.data == "heating_done")
async def heating_done(callback: CallbackQuery, state: FSMContext):
    await state.update_data(features=[])
    await state.set_state(FilterState.features)
    await callback.message.edit_text(
        "Выберите технические детали:",
        reply_markup=get_multi_keyboard(FEATURES, [], "features")
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 10: Технические детали
# ---------------------------------------------------------------------------

@router.callback_query(FilterState.features, lambda c: c.data == "back")
async def back_to_heating(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(FilterState.heating)
    await callback.message.edit_text(
        "Выберите тип отопления:",
        reply_markup=get_multi_keyboard(HEATING_TYPES, data.get("heating", []), "heating")
    )
    await callback.answer()


@router.callback_query(
    FilterState.features,
    lambda c: c.data.startswith("features_") and c.data != "features_done"
)
async def toggle_features(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("features", [])
    value = callback.data.replace("features_", "")

    if value in selected:
        selected.remove(value)
    else:
        selected.append(value)

    await state.update_data(features=selected)
    await callback.message.edit_reply_markup(
        reply_markup=get_multi_keyboard(FEATURES, selected, "features")
    )
    await callback.answer()


@router.callback_query(FilterState.features, lambda c: c.data == "features_done")
async def features_done(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterState.days_depth)
    await callback.message.edit_text("Введите глубину поиска (в днях):", reply_markup=back_button())
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 11: Глубина поиска → сохранение
# ---------------------------------------------------------------------------

@router.callback_query(FilterState.days_depth, lambda c: c.data == "back")
async def back_to_features(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(FilterState.features)
    await callback.message.edit_text(
        "Выберите технические детали:",
        reply_markup=get_multi_keyboard(FEATURES, data.get("features", []), "features")
    )
    await callback.answer()


@router.message(FilterState.days_depth)
async def set_days(message: Message, state: FSMContext):
    await state.update_data(days_depth=int(message.text))
    data = await state.get_data()
    user_id = await get_user_id(message.from_user.id)

    await save_filter(user_id, {
        "deal_type":  data.get("deal_type"),
        "subtype":    data.get("subtype"),
        "district":   data.get("district", []),
        "area_from":  data.get("area_from"),
        "area_to":    data.get("area_to"),
        "floor_from": data.get("floor_from"),
        "floor_to":   data.get("floor_to"),
        "days_depth": data.get("days_depth"),
        "heating":    data.get("heating", []),
        "features":   data.get("features", []),
    })

    bot_msg_id = data["bot_msg_id"]
    await state.clear()
    await message.delete()
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=bot_msg_id,
        text="✅ Фильтр сохранён!\n\nГлавное меню - выберите действие:",
        reply_markup=main_menu_kb(),
    )
