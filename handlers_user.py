from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from filters_fsm import FilterState
from db import save_user, save_filter, get_user_id


router = Router()

RENT_SUBTYPES = {
    "rent_longterm": "Долгосрочная",
    "rent_daily":    "Посуточно",
}

SALE_SUBTYPES = {
    "sale_apartment":  "Квартиры",
    "sale_house":      "Дома / Виллы",
    "sale_land":       "Земельные участки",
    "sale_commercial": "Коммерция",
}

COMMERCIAL_SUBTYPES = {
    "hotel":           "Отель",
    "casino":          "Казино",
    "restaurant":      "Ресторан / Кафе",
    "floor":           "Целый этаж",
    "land_commercial": "Участок под коммерцию",
    "office":          "Офис / Торговая площадь",
}

DISTRICTS = [
    "Центр",
    "Старый Батуми",
    "Новый Бульвар",
    "Гонио",
    "Квариати",
    "Махинджаури",
    "Чакви",
    "Кобулети"
]

HEATING_TYPES = [
    "Центральное",
    "Электрическое",
    "Кондиционер",
    "Теплый пол",
    "Карма"
]

FEATURES = [
    "2 санузла",
    "Ванна",
    "Балкон / Терраса",
    "Вид на море",
    "Парковка",
    "Духовка",
    "Посудомойка",
    "Сушильная машина"
]

#
# def get_district_keyboard(selected: list[str]):
#     keyboard = []
#
#     for district in DISTRICTS:
#         mark = "✅ " if district in selected else ""
#         keyboard.append([
#             InlineKeyboardButton(
#                 text=f"{mark}{district}",
#                 callback_data=f"district_{district}"
#             )
#         ])
#
#     keyboard.append([
#         InlineKeyboardButton(text="Готово", callback_data="district_done")
#     ])
#
#     return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_multi_keyboard(options: list[str], selected: list[str], prefix: str):
    keyboard = []

    for option in options:
        mark = "✅ " if option in selected else ""
        keyboard.append([
            InlineKeyboardButton(
                text=f"{mark}{option}",
                callback_data=f"{prefix}_{option}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="Готово", callback_data=f"{prefix}_done")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(CommandStart())
async def start_handler(message: Message):
    await save_user(message.from_user.id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Начать поиск", callback_data="start_search")]
    ])

    await message.answer(
   "Добро пожаловать в Kaufman Estate Bot 🏠\n"
        "> Я помогаю найти актуальные предложения по аренде или покупке недвижимости в Батуми.\n"
        "> Что я умею:\n"
        "> 📍 Фильтровать по районам: (Центр, Старый Батуми, Новый Бульвар, Гонио, Квариати, Махинджаури, Чакви, Кобулети\n"
        "> 🎯 Искать по точным параметрам: площадь , этажность и технические детали.\n"
        "> ⭐️ Добавлять в избранное: сохраняйте лучшие варианты, чтобы не потерять их.\n"
        "> 🔔 Уведомлять о новинках: настройте свои критерии, и я пришлю новый объект сразу, как он появится.\n"
        "> Нажмите кнопку ниже, чтобы начать поиск! 👇\n",
        reply_markup=kb
    )


@router.callback_query(lambda c: c.data == "start_search")
async def choose_deal(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Аренда", callback_data="deal_rent")],
        [InlineKeyboardButton(text="Продажа", callback_data="deal_sale")]
    ])

    await state.set_state(FilterState.choosing_deal)
    await callback.message.answer("Выберите категорию:", reply_markup=kb)
    await callback.answer()


@router.callback_query(FilterState.choosing_deal, lambda c: c.data.startswith("deal_"))
async def set_deal(callback: CallbackQuery, state: FSMContext):
    deal = callback.data.replace("deal_", "")
    await state.update_data(deal_type=deal, subtype=None)
    await state.set_state(FilterState.choosing_subtype)

    if deal == "rent":
        subtypes = RENT_SUBTYPES
        text = "Выберите тип аренды:"
    else:
        subtypes = SALE_SUBTYPES
        text = "Выберите категорию:"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"subtype_{key}")]
        for key, label in subtypes.items()
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(FilterState.choosing_subtype, lambda c: c.data.startswith("subtype_"))
async def set_subtype(callback: CallbackQuery, state: FSMContext):
    deal_type = callback.data.replace("subtype_", "")

    if deal_type == "sale_commercial":
        await state.update_data(deal_type=deal_type)
        await state.set_state(FilterState.choosing_commercial)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"commercial_{key}")]
            for key, label in COMMERCIAL_SUBTYPES.items()
        ])
        await callback.message.answer("Выберите подтип коммерции:", reply_markup=kb)
    else:
        await state.update_data(deal_type=deal_type, district=[])
        await state.set_state(FilterState.choosing_district)
        await callback.message.answer(
            "Выберите районы (можно несколько):",
            reply_markup=get_multi_keyboard(DISTRICTS, [], "district")
        )

    await callback.answer()


@router.callback_query(FilterState.choosing_commercial, lambda c: c.data.startswith("commercial_"))
async def set_commercial(callback: CallbackQuery, state: FSMContext):
    subtype = callback.data.replace("commercial_", "")
    await state.update_data(subtype=subtype, district=[])
    await state.set_state(FilterState.choosing_district)

    await callback.message.answer(
        "Выберите районы (можно несколько):",
        reply_markup=get_multi_keyboard(DISTRICTS, [], "district")
    )
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

    await callback.message.answer("Введите площадь ОТ (м2):")
    await callback.answer()


@router.message(FilterState.area_from)
async def set_area_from(message: Message, state: FSMContext):
    await state.update_data(area_from=int(message.text))
    await state.set_state(FilterState.area_to)
    await message.answer("Введите площадь ДО (м2):")


@router.message(FilterState.area_to)
async def set_area_to(message: Message, state: FSMContext):
    await state.update_data(area_to=int(message.text))
    await state.set_state(FilterState.floor_from)
    await message.answer("Введите этаж ОТ:")


@router.message(FilterState.floor_from)
async def set_floor_from(message: Message, state: FSMContext):
    await state.update_data(floor_from=int(message.text))
    await state.set_state(FilterState.floor_to)
    await message.answer("Введите этаж ДО:")


@router.message(FilterState.floor_to)
async def set_floor_to(message: Message, state: FSMContext):
    await state.update_data(floor_to=int(message.text))
    await state.update_data(heating=[])
    await state.set_state(FilterState.heating)
    await message.answer(
        "Выберите тип отопления:",
        reply_markup=get_multi_keyboard(HEATING_TYPES, [], "heating")
    )
    
    
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
    
    await callback.message.answer(
        "Выберите технические детали:",
        reply_markup=get_multi_keyboard(FEATURES, [], "features")
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
    await callback.message.answer("Введите глубину поиска (в днях):")
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

    await message.answer("✅ Фильтр сохранён!")
    await state.clear()