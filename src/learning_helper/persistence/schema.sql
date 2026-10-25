CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    module_id TEXT NOT NULL,
    level INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    choices_json TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    given_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    spec_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_attempts_module_created
    ON attempts (module_id, created_at);

CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    unlocked_modules_json TEXT NOT NULL,
    levels_json TEXT NOT NULL,
    last_interrupt_at TEXT,
    adult_pause_until TEXT,
    -- 180 espelha INITIAL_INTERVAL_SECONDS (config.py).
    interval_seconds INTEGER NOT NULL DEFAULT 180,
    last_bathroom_reminder_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    onboarding_completed INTEGER NOT NULL DEFAULT 0,
    values_json TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS daily_usage (
    day TEXT PRIMARY KEY,
    used_seconds INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT
);
