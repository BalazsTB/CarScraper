CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    postcode TEXT NOT NULL,
    radius INTEGER,
    year_from INTEGER,
    year_to INTEGER,
    price_from INTEGER,
    price_to INTEGER,
    cars_json TEXT NOT NULL,
    max_pages INTEGER NOT NULL,
    delay_seconds REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS search_results (
    id INTEGER PRIMARY KEY,
    search_id INTEGER NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    name TEXT,
    link TEXT NOT NULL,
    price INTEGER,
    year INTEGER,
    mileage INTEGER,
    miles_pa INTEGER,
    owners INTEGER,
    distance REAL,
    location TEXT,
    engine TEXT,
    transmission TEXT,
    fuel TEXT,
    UNIQUE (search_id, link)
);
