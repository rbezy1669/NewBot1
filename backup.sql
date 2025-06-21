BEGIN TRANSACTION;
CREATE TABLE logins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    full_name TEXT,
    platform TEXT,
    ip TEXT,
    geo TEXT,
    browser TEXT,
    language TEXT,
    timezone TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
DELETE FROM "sqlite_sequence";
COMMIT;
