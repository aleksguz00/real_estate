from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from filters_fsm import FilterState
from db import save_user, save_filter, get_user_id


router = Router()

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


@router.callback_query(lambda c: c.data.startswith("deal_"))
async def set_deal(callback: CallbackQuery, state: FSMContext):
    deal = callback.data.replace("deal_", "")

    await state.update_data(deal_type=deal)
    await state.update_data(district=[])
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
    await state.set_state(FilterState.days_depth)
    await message.answer("Введите глубину поиска (в днях):")


@router.message(FilterState.days_depth)
async def set_days(message: Message, state: FSMContext):
    await state.update_data(days_depth=int(message.text))

    data = await state.get_data()

    user_id = await get_user_id(message.from_user.id)

    await save_filter(user_id, (
        user_id,
        data["deal_type"],
        data["district"],
        data["area_from"],
        data["area_to"],
        data["floor_from"],
        data["floor_to"],
        data["days_depth"]
    ))

    await message.answer("✅ Фильтр сохранён!")
    await state.clear()