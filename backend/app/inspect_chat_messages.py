import sqlite3
import json

db_path = '/app/app/active_database.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get recent chat messages
cursor.execute("SELECT id, role, content, chatflowid, createdDate FROM chat_message ORDER BY createdDate DESC LIMIT 10;")
messages = cursor.fetchall()
print("--- CHAT MESSAGES ---")
for m in messages:
    print(f"Role: {m[1]}, Content: {m[2][:200]}..., Date: {m[4]}")
    
conn.close()
