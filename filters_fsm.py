# filters_fsm.py

from aiogram.fsm.state import State, StatesGroup


class FilterState(StatesGroup):
    # Новизна
    choosing_fresh      = State()
    fresh_manual_input  = State()
    # Фильтры
    choosing_rooms      = State()
    choosing_area       = State()
    area_manual_input   = State()
    choosing_type       = State()
    choosing_land       = State()
    choosing_district   = State()
    entering_address    = State()
    choosing_budget     = State()
    budget_manual_input = State()
    choosing_features   = State()
    choosing_heating    = State()
    # Контакт
    waiting_contact_message   = State()
    waiting_phone_for_contact = State()
    in_dialog                 = State()
    # Бинго
    bingo_game = State()


class AdminState(StatesGroup):
    waiting_viewing_datetime = State()
    waiting_rental_date      = State()
    waiting_close_date       = State()
    waiting_client_phone     = State()
    waiting_broadcast        = State()
    waiting_reply_text       = State()
    waiting_reminder_choice  = State()


class FixDistrict(StatesGroup):
    waiting_district = State()
