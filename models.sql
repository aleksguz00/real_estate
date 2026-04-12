CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Белый список администраторов (доступ по Telegram ID)
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    added_at TIMESTAMP DEFAULT NOW()
);

-- Объекты недвижимости, спарсенные из каналов
CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    source_channel BIGINT,
    message_id BIGINT,

    -- deal_type: rent_longterm | rent_daily | sale_apartment | sale_house | sale_land | sale_commercial
    deal_type TEXT,
    -- subtype (только для sale_commercial): hotel | casino | restaurant | floor | land_commercial | office
    subtype TEXT,

    district TEXT,

    area INTEGER,
    floor INTEGER,

    -- Тип отопления: центральное | электрическое | кондиционер | теплый_пол | карма
    heating TEXT[],
    -- Технические детали: 2_санузла | ванна | балкон | вид_на_море | парковка | духовка | посудомойка | сушилка
    features TEXT[],

    text TEXT,
    media_group_id TEXT,  -- для группировки фото-альбомов

    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE (source_channel, message_id)
);

-- Фильтры поиска и подписки на автопоиск
CREATE TABLE IF NOT EXISTS user_filters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

    deal_type TEXT,
    district TEXT[],

    area_from INTEGER,
    area_to INTEGER,

    floor_from INTEGER,
    floor_to INTEGER,

    days_depth INTEGER,

    heating TEXT[],
    features TEXT[],

    -- FALSE = разовый поиск, TRUE = автопоиск (подписка на уведомления)
    is_subscription BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Избранное
CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, property_id)
);
