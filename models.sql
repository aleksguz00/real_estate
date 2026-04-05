CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    source_channel BIGINT,
    message_id BIGINT,
    deal_type TEXT,
    district TEXT,
    area INTEGER,
    floor INTEGER,
    text TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE user_filters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    deal_type TEXT,
    district TEXT[],
    area_from INTEGER,
    area_to INTEGER,
    floor_from INTEGER,
    floor_to INTEGER,
    days_depth INTEGER
);