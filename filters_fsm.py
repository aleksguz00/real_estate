from aiogram.fsm.state import StatesGroup, State

class FilterState(StatesGroup):
    choosing_deal = State()
    choosing_district = State()

    area_from = State()
    area_to = State()

    floor_from = State()
    floor_to = State()

    heating = State()
    features = State()

    days_depth = State()