import sqlite3

db_path = '/app/app/database.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(credential);")
columns = cursor.fetchall()
print("Credential columns:", [c[1] for c in columns])

cursor.execute("SELECT * FROM credential;")
creds = cursor.fetchall()
for c in creds:
    print(c)

conn.close()
