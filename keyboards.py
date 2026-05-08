# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from locales import t, tl


# ─────────────────────────────────────────────────────────────────────────────
# ДАННЫЕ
# ─────────────────────────────────────────────────────────────────────────────

DISTRICTS = [
    "Старый Батуми", "Химшиашвили", "Аэропорт", "Новый Бульвар",
    "Руставели", "Джавахишвили", "Багратиони", "Агмашенебели",
    "Тамар", "Бони Городок", "Кахабери", "Махинджаури",
]

DISTRICTS_EN = {
    "Новый Бульвар": "New Boulevard",
}

PRICE_RANGES_RENT = [
    ("rent_1", "до $350"),    ("rent_2", "$350 — $500"),
    ("rent_3", "$500 — $700"),("rent_4", "$700 — $850"),
    ("rent_5", "$850 — $1 000"),("rent_6", "от $1 000"),
]

PRICE_RANGES_SALE = [
    ("sale_1", "до $70K"),    ("sale_2", "$70K — $120K"),
    ("sale_3", "$120K — $180K"),("sale_4", "$180K — $260K"),
    ("sale_5", "$260K — $380K"),("sale_6", "от $380K"),
]

FRESHNESS_OPTIONS = [
    ("fresh_7",  "depth_7"),
    ("fresh_14", "depth_14"),
    ("fresh_30", "depth_30"),
]

BINGO_ITEMS_KEY = "bingo_items"


# ─────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ
# ─────────────────────────────────────────────────────────────────────────────

def skip_kb(skip_callback: str, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_skip", lang), callback_data=skip_callback),
            InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_to_search"),
        ]
    ])


# ─────────────────────────────────────────────────────────────────────────────
# ВЫБОР ЯЗЫКА
# ─────────────────────────────────────────────────────────────────────────────

def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ]
    ])


# ─────────────────────────────────────────────────────────────────────────────
# ПОДПИСКА НА КАНАЛ
# ─────────────────────────────────────────────────────────────────────────────

def subscription_kb(channel_url: str, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kaufman Estate", url=channel_url)],
        [InlineKeyboardButton(text="✅ " + ("Я подписался" if lang == "ru" else "I subscribed"), callback_data="check_subscription")],
    ])


# ─────────────────────────────────────────────────────────────────────────────
# ГЛАВНОЕ МЕНЮ
# ─────────────────────────────────────────────────────────────────────────────

def main_menu_kb(lang: str = "ru", is_admin: bool = False) -> InlineKeyboardMarkup:
    flag = "RU" if lang == "ru" else "EN"
    rows = [
        [InlineKeyboardButton(text=f"🌐 {flag}", callback_data="change_language")],
        [InlineKeyboardButton(text=t("btn_search", lang),        callback_data="open_search")],
        [InlineKeyboardButton(text=t("btn_favorites", lang),     callback_data="favorites")],
        [InlineKeyboardButton(text=t("btn_subscriptions", lang), callback_data="subscriptions")],
        [InlineKeyboardButton(text=t("btn_contact", lang),       callback_data="contact_us")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text=t("btn_admin", lang), callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# ПОИСК — ДАШБОРД
# ─────────────────────────────────────────────────────────────────────────────

def search_dashboard_kb(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    rooms_raw = data.get("rooms", [])
    if isinstance(rooms_raw, str):
        rooms_raw = [rooms_raw]
    if rooms_raw:
        rooms = "/".join(rooms_raw) if len(rooms_raw) <= 3 else f"{len(rooms_raw)} типа"
    else:
        rooms = "—"
    deal     = data.get("deal_type")
    prop     = data.get("prop_types", [])
    district = data.get("district", [])
    budget   = data.get("budget_label") or "——"
    features = len(data.get("features", []))
    heating  = len(data.get("heating", []))
    fresh    = data.get("fresh_label") or "—"
    address  = data.get("address_label") or "—"

    type_label = "—"
    if deal and prop:
        deal_name = t("btn_rent" if deal == "rent" else "btn_sale", lang)
        type_label = deal_name
    elif deal:
        type_label = t("btn_rent" if deal == "rent" else "btn_sale", lang)

    if len(district) == 0:
        dist_label = "—"
    elif len(district) == 1:
        dist_label = district[0]
    else:
        dist_label = f"{len(district)}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{t('btn_depth', lang)}: {fresh}",    callback_data="filter_fresh"),
            InlineKeyboardButton(text=f"{t('btn_type', lang)}: {type_label}", callback_data="filter_type"),
        ],
        [
            InlineKeyboardButton(text=f"{t('btn_rooms', lang)}: {rooms}",    callback_data="filter_rooms"),
            InlineKeyboardButton(text=f"{t('btn_budget', lang)}: {budget}",  callback_data="filter_budget"),
        ],
        [
            InlineKeyboardButton(text=f"{t('btn_location', lang)}: {dist_label}", callback_data="filter_district"),
            InlineKeyboardButton(text=f"{t('btn_address', lang)}: {address}", callback_data="filter_address"),
        ],
        [
            InlineKeyboardButton(text=f"{t('btn_details', lang)}: {features}", callback_data="filter_features"),
            InlineKeyboardButton(text=f"{t('btn_heating', lang)}: {heating}", callback_data="filter_heating"),
        ],
        [
            InlineKeyboardButton(text=t("btn_clear", lang), callback_data="filter_reset"),
            InlineKeyboardButton(text=t("btn_show", lang),  callback_data="filter_show"),
        ],
        [
            InlineKeyboardButton(text=t("btn_back", lang),  callback_data="main_menu"),
        ],
    ])


# ─────────────────────────────────────────────────────────────────────────────
# НОВИЗНА
# ─────────────────────────────────────────────────────────────────────────────

def fresh_kb(selected: str | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    for key, label_key in FRESHNESS_OPTIONS:
        mark = "✅ " if key == selected else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{t(label_key, lang)}", callback_data=f"fresh_{key}")])
    rows.append([InlineKeyboardButton(text=t("btn_manual", lang), callback_data="fresh_manual")])
    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_to_search")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# КОМНАТЫ + ПЛОЩАДЬ
# ─────────────────────────────────────────────────────────────────────────────

def rooms_kb(selected: list | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    if selected is None:
        selected = []
    row = []
    for room in tl("rooms_list", lang):
        mark = "✅ " if room in selected else ""
        row.append(InlineKeyboardButton(text=f"{mark}{room}", callback_data=f"room_{room}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        row,
        [
            InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_to_search"),
            InlineKeyboardButton(text=t("btn_done", lang), callback_data="rooms_done"),
        ],
    ])


def area_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    options = [30, 40, 50, 60, 70, 80, 100]
    rows = []
    row = []
    for val in options:
        row.append(InlineKeyboardButton(text=f"от {val} м²", callback_data=f"area_{val}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text=t("btn_manual", lang), callback_data="area_manual"),
        InlineKeyboardButton(text=t("btn_skip", lang),   callback_data="area_skip"),
    ])
    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_to_rooms")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# ТИП СДЕЛКИ И ОБЪЕКТА
# ─────────────────────────────────────────────────────────────────────────────

def deal_type_kb(selected_deal: str | None = None, selected_props: list | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    if selected_props is None:
        selected_props = []

    deal_row = []
    for key, text_key in [("rent", "btn_rent"), ("sale", "btn_sale")]:
        mark = "✅ " if key == selected_deal else ""
        deal_row.append(InlineKeyboardButton(text=f"{mark}{t(text_key, lang)}", callback_data=f"deal_{key}"))

    prop_items = [
        ("apartment", "btn_apartment"), ("house", "btn_house"),
        ("land", "btn_land"), ("commercial", "btn_commercial"),
    ]
    prop_rows = []
    for i in range(0, len(prop_items), 2):
        row = []
        for key, text_key in prop_items[i:i+2]:
            mark = "✅ " if key in selected_props else ""
            row.append(InlineKeyboardButton(text=f"{mark}{t(text_key, lang)}", callback_data=f"prop_{key}"))
        prop_rows.append(row)

    return InlineKeyboardMarkup(inline_keyboard=[
        deal_row, *prop_rows,
        [
            InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_to_search"),
            InlineKeyboardButton(text=t("btn_done", lang), callback_data="prop_done"),
        ],
    ])


def land_type_kb(selected: str | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    items = [("land_agri", "btn_land_agri"), ("land_non_agri", "btn_land_non_agri")]
    rows = []
    for key, text_key in items:
        mark = "✅ " if key == selected else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{t(text_key, lang)}", callback_data=f"land_{key}")])
    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="filter_type")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ
# ─────────────────────────────────────────────────────────────────────────────

def district_kb(selected: list[str], lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    for district in DISTRICTS:
        mark = "✅ " if district in selected else ""
        label = DISTRICTS_EN.get(district, district) if lang == "en" else district
        rows.append([InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"dist_{district}")])
    rows.append([
        InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_to_search"),
        InlineKeyboardButton(text=t("btn_done", lang), callback_data="dist_done"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# БЮДЖЕТ
# ─────────────────────────────────────────────────────────────────────────────

def budget_kb(deal_type: str | None, selected: list | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    if selected is None:
        selected = []
    ranges = PRICE_RANGES_RENT if deal_type == "rent" else PRICE_RANGES_SALE
    rows = []
    row = []
    for key, label in ranges:
        mark = "✅ " if key in selected else ""
        row.append(InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"budget_{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t("btn_manual", lang), callback_data="budget_manual")])
    rows.append([
        InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_to_search"),
        InlineKeyboardButton(text=t("btn_done", lang), callback_data="budget_done"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# ДЕТАЛИ
# ─────────────────────────────────────────────────────────────────────────────

def features_kb(selected: list[str], lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    for feature in tl("features_list", lang):
        mark = "✅ " if feature in selected else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{feature}", callback_data=f"feat_{feature}")])
    rows.append([
        InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_to_search"),
        InlineKeyboardButton(text=t("btn_done", lang), callback_data="feat_done"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# ОТОПЛЕНИЕ
# ─────────────────────────────────────────────────────────────────────────────

def heating_kb(selected: list[str], lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    for h in tl("heating_list", lang):
        mark = "✅ " if h in selected else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{h}", callback_data=f"heat_{h}")])
    rows.append([
        InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_to_search"),
        InlineKeyboardButton(text=t("btn_done", lang), callback_data="heat_done"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# КАРТОЧКА ОБЪЕКТА
# ─────────────────────────────────────────────────────────────────────────────

def property_card_kb(current: int, total: int, prop_id: int,
                     is_favorite: bool = False, is_admin: bool = False,
                     lang: str = "ru") -> InlineKeyboardMarkup:
    fav_text = t("btn_favorited" if is_favorite else "btn_favorite", lang)
    rows = [
        [
            InlineKeyboardButton(text=fav_text, callback_data=f"fav_{prop_id}"),
            InlineKeyboardButton(text=t("btn_contact_card", lang), callback_data=f"contact_{prop_id}"),
        ],
        [
            InlineKeyboardButton(text="◀️", callback_data="card_prev"),
            InlineKeyboardButton(text=f"{current} / {total}", callback_data="card_count"),
            InlineKeyboardButton(text="▶️", callback_data="card_next"),
        ],
        [InlineKeyboardButton(text=t("btn_subscribe", lang), callback_data="subscribe")],
        [
            InlineKeyboardButton(text=t("btn_filters", lang),   callback_data="open_search"),
            InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="main_menu"),
        ],
    ]
    if is_admin:
        rows.append([
            InlineKeyboardButton(text=t("btn_check", lang), callback_data=f"op_check_{prop_id}"),
        ])
        fix_label = "✏️ Fix district" if lang == "en" else "✏️ Исправить район"
        rows.append([
            InlineKeyboardButton(text=fix_label, callback_data=f"fix_district:{prop_id}"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# ИЗБРАННОЕ
# ─────────────────────────────────────────────────────────────────────────────

def favorites_kb(current: int, total: int, prop_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_remove_fav", lang), callback_data=f"fav_remove_{prop_id}"),
            InlineKeyboardButton(text=t("btn_contact_card", lang), callback_data=f"contact_{prop_id}"),
        ],
        [
            InlineKeyboardButton(text="◀️", callback_data="fav_prev"),
            InlineKeyboardButton(text=f"{current} / {total}", callback_data="fav_count"),
            InlineKeyboardButton(text="▶️", callback_data="fav_next"),
        ],
        [InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="main_menu")],
    ])


# ─────────────────────────────────────────────────────────────────────────────
# ПОДПИСКИ
# ─────────────────────────────────────────────────────────────────────────────

def subscriptions_kb(has_active: bool, lang: str = "ru") -> InlineKeyboardMarkup:
    btn = t("btn_sub_off" if has_active else "btn_sub_on", lang)
    cb  = "sub_disable" if has_active else "sub_enable"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn, callback_data=cb)],
        [InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="main_menu")],
    ])


# ─────────────────────────────────────────────────────────────────────────────
# АДМИНПАНЕЛЬ
# ─────────────────────────────────────────────────────────────────────────────

def admin_panel_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Заявки",          callback_data="admin_requests")],
        [InlineKeyboardButton(text="🔍 Подбор объектов", callback_data="admin_search")],
        [InlineKeyboardButton(text="📊 Статистика",      callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Клиенты",         callback_data="admin_clients")],
        [InlineKeyboardButton(text="📤 Рассылка",        callback_data="admin_broadcast")],
        [
            InlineKeyboardButton(
                text="👤 Добавить админа" if lang == "ru" else "👤 Add admin",
                callback_data="admin_add",
            ),
            InlineKeyboardButton(
                text="🗑 Удалить админа" if lang == "ru" else "🗑 Remove admin",
                callback_data="admin_remove",
            ),
        ],
        [InlineKeyboardButton(text="⬇️ Загрузить историю (90 дней)", callback_data="admin_fetch_history")],
        [InlineKeyboardButton(text="⏬ Загрузить ВСЁ из канала", callback_data="admin_fetch_all")],
        [InlineKeyboardButton(text="🗺 Геокодировать все объекты", callback_data="admin_geocode_all")],
        [InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="main_menu")],
    ])


# ─────────────────────────────────────────────────────────────────────────────
# БАТУМСКОЕ БИНГО
# ─────────────────────────────────────────────────────────────────────────────

def bingo_kb(checked: list[int], lang: str = "ru") -> InlineKeyboardMarkup:
    items = tl("bingo_items", lang)
    rows = []
    for i, item in enumerate(items):
        mark = "✅ " if i in checked else "☐ "
        rows.append([InlineKeyboardButton(text=f"{mark}{item}", callback_data=f"bingo_{i}")])
    rows.append([InlineKeyboardButton(text=t("bingo_result_btn", lang), callback_data="bingo_result")])
    rows.append([InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
