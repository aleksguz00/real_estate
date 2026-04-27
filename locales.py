# locales.py

TEXTS = {
    "ru": {
        # ── Старт ────────────────────────────────────────────────
        "choose_language":   "Выберите язык / Choose language:",
        "welcome":           "🌊 Kaufman Estate",

        # ── Главное меню ─────────────────────────────────────────
        "btn_search":        "🔍 Поиск",
        "btn_favorites":     "⭐️ Избранное",
        "btn_subscriptions": "🔔 Мои подписки",
        "btn_contact":       "✉️ Написать нам",
        "btn_game":          "🎮 Игра",
        "btn_admin":         "⚙️ Админпанель",

        # ── Поиск ────────────────────────────────────────────────
        "search_title":      "🔍 Настройте фильтры поиска:",
        "btn_depth":         "🕐 Глубина",
        "btn_type":          "🏙 Тип",
        "btn_rooms":         "🛏 Комнаты",
        "btn_budget":        "💵 Бюджет",
        "btn_location":      "📍 Локация",
        "btn_address":       "🏠 Адрес",
        "btn_details":       "🌴 Детали",
        "btn_heating":       "☀️ Отопление",
        "btn_clear":         "🔄 Очистить",
        "btn_show":          "🔍 Показать",
        "btn_back":          "◀️ Назад",
        "btn_done":          "✅ Готово",
        "btn_skip":          "⏭️ Пропустить",
        "btn_manual":        "✏️ Ввести вручную",

        # ── Тип сделки ───────────────────────────────────────────
        "btn_rent":          "🔑 Аренда",
        "btn_sale":          "💰 Продажа",
        "btn_apartment":     "🏢 Квартира",
        "btn_house":         "🏡 Дом",
        "btn_land":          "🏔 Земельный участок",
        "btn_commercial":    "💼 Коммерция",
        "btn_land_agri":     "🌾 Сельхоз",
        "btn_land_non_agri": "🏘️ Несельхоз",
        "btn_hotel":         "🏨 Гостиница",
        "btn_restaurant":    "🍽️ Ресторан / Кафе",
        "btn_beauty":        "💅 Салон красоты",
        "btn_office":        "🏢 Офисное помещение",
        "btn_retail":        "🛍️ Торговая площадь",
        "btn_warehouse":     "🏭 Складские помещения",

        # ── Комнаты ──────────────────────────────────────────────
        "rooms_list": ["Студия", "1+1", "2+1", "3+1", "4+1+"],
        "enter_area":        "✏️ Введите площадь от (м²), например: 60",

        # ── Глубина ──────────────────────────────────────────────
        "depth_7":           "📅 7 дней",
        "depth_14":          "📅 14 дней",
        "depth_30":          "📅 30 дней",
        "enter_depth":       "✏️ Введите количество дней, например: 21",

        # ── Бюджет ───────────────────────────────────────────────
        "enter_budget":      "✏️ Введите диапазон цен, например: 400-600",
        "budget_no_type":    "⚠️ Сначала выберите Аренда или Продажа в разделе Тип",

        # ── Адрес ────────────────────────────────────────────────
        "enter_address":     "🏠 Введите адрес для поиска:\n<i>например: Руставели 23 или Химшиашвили 5</i>",

        # ── Детали ───────────────────────────────────────────────
        "features_list": [
            "Балкон", "Посудомоечная", "Духовой шкаф", "Ванна",
            "2 санузла", "2 кондиционера+", "Парковка",
            "Вид на море / горы", "Можно с питомцами",
        ],

        # ── Отопление ────────────────────────────────────────────
        "heating_list": ["Центральное", "Карма", "Тёплый пол"],

        # ── Карточка объекта ─────────────────────────────────────
        "btn_favorite":      "⭐️ В избранное",
        "btn_favorited":     "❤️ В избранном",
        "btn_contact_card":  "✉️ Написать нам",
        "btn_subscribe":     "🔔 Подписаться на фильтр",
        "btn_filters":       "🔍 Фильтры",
        "btn_main_menu":     "🏠 Главное меню",
        "btn_forward":       "📤 Переслать клиенту",
        "btn_check":         "🔑 Проверить объект",

        # ── Избранное ────────────────────────────────────────────
        "favorites_title":   "⭐️ Избранное",
        "favorites_empty":   "Здесь появятся сохранённые объекты.",
        "btn_remove_fav":    "🗑 Удалить",
        "fav_added":         "⭐️ Добавлено в избранное!",
        "fav_removed":       "🗑 Удалено из избранного",

        # ── Подписки ─────────────────────────────────────────────
        "subscriptions_title": "🔔 Мои подписки",
        "subscriptions_text":  "Получайте уведомления о новых объектах по вашим фильтрам.",
        "btn_sub_on":        "🔔 Включить уведомления",
        "btn_sub_off":       "🔕 Отключить уведомления",
        "sub_activated":     "🔔 Подписка активирована!",
        "sub_disabled":      "🔕 Уведомления отключены",
        "sub_enabled":       "🔔 Уведомления включены!",

        # ── Написать нам ─────────────────────────────────────────
        "contact_text":      "✉️ <b>Написать нам</b>\n\nОпишите что вы ищете — менеджер свяжется в течение 15 минут 👇",
        "contact_card_text": "✉️ Напишите ваш вопрос — менеджер ответит в течение 15 минут 👇",
        "contact_sent":      "✅ Ваш запрос отправлен!\nМенеджер свяжется с вами в течение 15 минут.",

        # ── Поиск результатов ────────────────────────────────────
        "searching":         "⏳ Ищем объекты...",
        "no_results":        "😔 По вашим фильтрам ничего не найдено. Попробуйте изменить параметры.",
        "cleared":           "🔄 Фильтры сброшены",

        # ── Бинго ────────────────────────────────────────────────
        "bingo_title":       "🎰 Батумское Бинго",
        "bingo_find":        "Отметь что нашёл в объявлении:",
        "bingo_result_btn":  "🎯 Проверить результат",
        "bingo_items": [
            "🦠 Плесень в углу",
            "🧱 Вид на стену соседа",
            "🛠️ «Евроремонт» 2005 года",
            "🚗 «Тихий район» у трассы",
            "⏳ «Срочно!» висит 3 месяца",
            "🏖️ «Море в 5 минутах» (пешком 40 мин)",
            "🤵 «Собственник» (позвонит риелтор)",
        ],

        # ── Ошибки ───────────────────────────────────────────────
        "error_number":      "⚠️ Введите корректное число, например: 60",
        "no_access":         "⛔️ Нет доступа",
    },

    "en": {
        # ── Start ────────────────────────────────────────────────
        "choose_language":   "Выберите язык / Choose language:",
        "welcome":           "🌊 Kaufman Estate",

        # ── Main menu ────────────────────────────────────────────
        "btn_search":        "🔍 Search",
        "btn_favorites":     "⭐️ Favorites",
        "btn_subscriptions": "🔔 My subscriptions",
        "btn_contact":       "✉️ Contact us",
        "btn_game":          "🎮 Game",
        "btn_admin":         "⚙️ Admin panel",

        # ── Search ───────────────────────────────────────────────
        "search_title":      "🔍 Set your search filters:",
        "btn_depth":         "🕐 Depth",
        "btn_type":          "🏙 Type",
        "btn_rooms":         "🛏 Rooms",
        "btn_budget":        "💵 Budget",
        "btn_location":      "📍 Location",
        "btn_address":       "🏠 Address",
        "btn_details":       "🌴 Details",
        "btn_heating":       "☀️ Heating",
        "btn_clear":         "🔄 Clear",
        "btn_show":          "🔍 Show",
        "btn_back":          "◀️ Back",
        "btn_done":          "✅ Done",
        "btn_skip":          "⏭️ Skip",
        "btn_manual":        "✏️ Enter manually",

        # ── Deal type ────────────────────────────────────────────
        "btn_rent":          "🔑 Rent",
        "btn_sale":          "💰 Sale",
        "btn_apartment":     "🏢 Apartment",
        "btn_house":         "🏡 House",
        "btn_land":          "🏔 Land plot",
        "btn_commercial":    "💼 Commercial",
        "btn_land_agri":     "🌾 Agricultural",
        "btn_land_non_agri": "🏘️ Non-agricultural",
        "btn_hotel":         "🏨 Hotel",
        "btn_restaurant":    "🍽️ Restaurant / Cafe",
        "btn_beauty":        "💅 Beauty salon",
        "btn_office":        "🏢 Office space",
        "btn_retail":        "🛍️ Retail space",
        "btn_warehouse":     "🏭 Warehouse",

        # ── Rooms ────────────────────────────────────────────────
        "rooms_list": ["Studio", "1+1", "2+1", "3+1", "4+1+"],
        "enter_area":        "✏️ Enter minimum area (m²), e.g.: 60",

        # ── Depth ────────────────────────────────────────────────
        "depth_7":           "📅 7 days",
        "depth_14":          "📅 14 days",
        "depth_30":          "📅 30 days",
        "enter_depth":       "✏️ Enter number of days, e.g.: 21",

        # ── Budget ───────────────────────────────────────────────
        "enter_budget":      "✏️ Enter price range, e.g.: 400-600",
        "budget_no_type":    "⚠️ Please select Rent or Sale in the Type section first",

        # ── Address ──────────────────────────────────────────────
        "enter_address":     "🏠 Enter address to search:\n<i>e.g.: Rustaveli 23 or Khimshiashvili 5</i>",

        # ── Details ──────────────────────────────────────────────
        "features_list": [
            "Balcony", "Dishwasher", "Oven", "Bathtub",
            "2 bathrooms", "2+ AC units", "Parking",
            "Sea / mountain view", "Pets allowed",
        ],

        # ── Heating ──────────────────────────────────────────────
        "heating_list": ["Central", "Karma", "Underfloor heating"],

        # ── Property card ────────────────────────────────────────
        "btn_favorite":      "⭐️ Add to favorites",
        "btn_favorited":     "❤️ In favorites",
        "btn_contact_card":  "✉️ Contact us",
        "btn_subscribe":     "🔔 Subscribe to filter",
        "btn_filters":       "🔍 Filters",
        "btn_main_menu":     "🏠 Main menu",
        "btn_forward":       "📤 Forward to client",
        "btn_check":         "🔑 Check property",

        # ── Favorites ────────────────────────────────────────────
        "favorites_title":   "⭐️ Favorites",
        "favorites_empty":   "Your saved properties will appear here.",
        "btn_remove_fav":    "🗑 Remove",
        "fav_added":         "⭐️ Added to favorites!",
        "fav_removed":       "🗑 Removed from favorites",

        # ── Subscriptions ────────────────────────────────────────
        "subscriptions_title": "🔔 My subscriptions",
        "subscriptions_text":  "Get notified about new properties matching your filters.",
        "btn_sub_on":        "🔔 Enable notifications",
        "btn_sub_off":       "🔕 Disable notifications",
        "sub_activated":     "🔔 Subscription activated!",
        "sub_disabled":      "🔕 Notifications disabled",
        "sub_enabled":       "🔔 Notifications enabled!",

        # ── Contact ──────────────────────────────────────────────
        "contact_text":      "✉️ <b>Contact us</b>\n\nDescribe what you're looking for — a manager will reply within 15 minutes 👇",
        "contact_card_text": "✉️ Write your question — a manager will reply within 15 minutes 👇",
        "contact_sent":      "✅ Your request has been sent!\nA manager will contact you within 15 minutes.",

        # ── Search results ───────────────────────────────────────
        "searching":         "⏳ Searching...",
        "no_results":        "😔 No results found for your filters. Try changing the parameters.",
        "cleared":           "🔄 Filters cleared",

        # ── Game ─────────────────────────────────────────────────
        "bingo_title":       "🎰 Batumi Bingo",
        "bingo_find":        "Check what you found in the listing:",
        "bingo_result_btn":  "🎯 Check result",
        "bingo_items": [
            "🦠 Mold in the corner",
            "🧱 View of neighbor's wall",
            "🛠️ 'Euro-renovation' from 2005",
            "🚗 'Quiet area' next to highway",
            "⏳ 'Urgent!' listed for 3 months",
            "🏖️ 'Sea in 5 min' (40 min walk)",
            "🤵 'Owner' (realtor will call)",
        ],

        # ── Errors ───────────────────────────────────────────────
        "error_number":      "⚠️ Please enter a valid number, e.g.: 60",
        "no_access":         "⛔️ Access denied",
    }
}


def t(key: str, lang: str = "ru") -> str:
    """Получить текст по ключу и языку."""
    return TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"].get(key, key))


def tl(key: str, lang: str = "ru") -> list:
    """Получить список по ключу и языку."""
    return TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"].get(key, []))
