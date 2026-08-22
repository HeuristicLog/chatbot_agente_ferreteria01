import sqlite3

db_path = '/app/app/database.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tools
cursor.execute("SELECT id, name, func FROM tool;")
tools = cursor.fetchall()

print("--- Removing node-fetch require from all tools ---")
for t_id, name, func in tools:
    if "require('node-fetch')" in func or 'require("node-fetch")' in func:
        print(f"Modifying tool: {name}")
        # Strip the require('node-fetch') line
        new_func = func.replace("const fetch = require('node-fetch');", "")
        new_func = new_func.replace('const fetch = require("node-fetch");', "")
        cursor.execute("UPDATE tool SET func = ? WHERE id = ?;", (new_func, t_id))
        print(f"  Tool {name} updated (removed node-fetch requirement).")

conn.commit()
conn.close()
print("\nTools updated successfully.")
