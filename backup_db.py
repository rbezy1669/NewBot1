import sqlite3

with open("backup.sql", "w", encoding="utf-8") as f:
    for line in sqlite3.connect("analytics.db").iterdump():
        f.write(f"{line}\n")

print("✅ Бэкап сохранён в backup.sql")
