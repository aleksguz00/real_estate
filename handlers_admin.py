# handlers_admin.py
# Обработчики для операторов — подтверждение просмотров, аренды, закрытия

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from filters_fsm import AdminState
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


@router.message(AdminState.waiting_client_phone, F.contact)
async def save_client_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    # TODO: сохранить телефон клиента в БД и таблицу
    await log_to_sheets(message.from_user.id, 0, {"phone": phone})
    await state.set_state(None)
    await message.answer("✅ Телефон сохранён! Ждём вас на просмотре 🏠")
