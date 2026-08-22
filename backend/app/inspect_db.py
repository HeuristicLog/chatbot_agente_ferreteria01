import sqlite3
import json

db_path = '/app/app/database.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(tool);")
columns = cursor.fetchall()
print("Tool columns:", [c[1] for c in columns])

cursor.execute("SELECT id, name, func, schema, description FROM tool;")
tools = cursor.fetchall()
for t in tools:
    print(f"\n========================================\nName: {t[1]}\nFunction (code):\n{t[2]}\nSchema: {t[3]}")

conn.close()
