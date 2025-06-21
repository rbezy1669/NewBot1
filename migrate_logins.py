import sqlite3

conn = sqlite3.connect("analytics.db")
c = conn.cursor()

# Список новых столбцов
columns = [
    ("full_name", "TEXT"),
    ("platform", "TEXT"),
    ("geo", "TEXT"),
    ("browser", "TEXT"),
    ("language", "TEXT"),
    ("timezone", "TEXT")
]

# Добавляем каждый, если ещё не существует
for col, dtype in columns:
    try:
        c.execute(f"ALTER TABLE logins ADD COLUMN {col} {dtype}")
        print(f"✅ Добавлено поле: {col}")
    except sqlite3.OperationalError:
        print(f"⚠️ Поле уже есть: {col}")

conn.commit()
conn.close()
