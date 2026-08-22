import sqlite3

db_path = '/app/app/database.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tools
cursor.execute("SELECT id, name, func FROM tool;")
tools = cursor.fetchall()

print("--- Modifying Tool Hostnames ---")
for t_id, name, func in tools:
    if "chatbot-api:8080" in func:
        print(f"Modifying hostname in tool: {name}")
        new_func = func.replace("chatbot-api:8080", "backend:8080")
        cursor.execute("UPDATE tool SET func = ? WHERE id = ?;", (new_func, t_id))
        print(f"  Hostname updated in tool {name}.")

conn.commit()
conn.close()
print("\nTool hostnames updated.")
