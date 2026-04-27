-- ─────────────────────────────────────────────────────────────────────────────
-- KAUFMAN ESTATE BOT — Структура базы данных
-- ─────────────────────────────────────────────────────────────────────────────

-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username    TEXT,
    full_name   TEXT,
    phone       TEXT,
    lang        TEXT DEFAULT 'ru',
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Белый список администраторов
CREATE TABLE IF NOT EXISTS admins (
    id          SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    added_at    TIMESTAMP DEFAULT NOW()
);

-- Объекты недвижимости
CREATE TABLE IF NOT EXISTS properties (
    id              SERIAL PRIMARY KEY,
    source_channel  BIGINT,
    message_id      BIGINT,
    source_code     TEXT,          -- Код из объявления: 2336АК / 554РК

    -- Тип сделки и объекта
    deal_type       TEXT,          -- rent / sale
    property_type   TEXT,          -- apartment / house / commercial / studio
    subtype         TEXT,          -- office / warehouse / hotel / restaurant / beauty / retail

    -- Локация
    address         TEXT,          -- Полный адрес из поста (без скобок)
    district        TEXT,          -- Район (определяется Яндекс Геокодером)
    lat             FLOAT,         -- Широта (из Яндекс Геокодера)
    lon             FLOAT,         -- Долгота (из Яндекс Геокодера)

    -- Параметры
    rooms           TEXT,          -- Студия / 1+1 / 2+1 / 3+1 / 4+1+
    price           INTEGER,       -- Цена в USD
    price_season    INTEGER,       -- Цена в сезон (если есть)
    deposit         INTEGER,       -- Депозит (если есть)
    area            INTEGER,       -- Площадь м²
    area_land       FLOAT,         -- Площадь участка в сотках (для домов)
    floor           INTEGER,       -- Этаж квартиры
    floors_total    INTEGER,       -- Этажей в доме

    -- Отопление
    heating         TEXT[],        -- центральное / теплый_пол / карма

    -- Технические детали
    features        TEXT[],        -- балкон / ванна / 2_санузла / парковка / духовка / посудомойка / вид_на_море / питомцы / кондиционер

    -- Медиа
    photos          TEXT[],        -- Массив file_id фотографий из Telegram

    -- Оригинальный текст поста (очищенный)
    text            TEXT,
    media_group_id  TEXT,          -- Для группировки фото-альбомов

    -- Статус
    is_active       BOOLEAN DEFAULT TRUE,   -- FALSE = Сдано / Продано
    published_at    TIMESTAMP,              -- Дата публикации в канале
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),

    UNIQUE (source_channel, message_id)
);

-- Фильтры поиска и подписки
CREATE TABLE IF NOT EXISTS user_filters (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,

    deal_type   TEXT,
    property_type TEXT[],
    district    TEXT[],
    address     TEXT,

    rooms       TEXT[],
    price_min   INTEGER,
    price_max   INTEGER,
    area_min    INTEGER,
    area_max    INTEGER,
    floor_min   INTEGER,
    floor_max   INTEGER,
    floors_total_min INTEGER,
    floors_total_max INTEGER,
    days_depth  INTEGER DEFAULT 30,

    heating     TEXT[],
    features    TEXT[],

    is_subscription BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Избранное
CREATE TABLE IF NOT EXISTS favorites (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
    added_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, property_id)
);

-- Просмотры и аренда (для операторов)
CREATE TABLE IF NOT EXISTS viewings (
    id               SERIAL PRIMARY KEY,
    telegram_id      BIGINT NOT NULL,
    property_id      INTEGER REFERENCES properties(id),
    viewing_datetime TEXT,
    rental_start     TEXT,
    rental_end       TEXT,
    status           TEXT DEFAULT 'Назначен',
    created_at       TIMESTAMP DEFAULT NOW(),
    UNIQUE (telegram_id, property_id)
);
