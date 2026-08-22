import sqlite3

db_path = '/app/app/database.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tools
cursor.execute("SELECT id, name, func FROM tool;")
tools = cursor.fetchall()

print("--- Restoring node-fetch require to all tools ---")
for t_id, name, func in tools:
    if "require('node-fetch')" not in func and 'require("node-fetch")' not in func:
        print(f"Modifying tool: {name}")
        # Prepend the require('node-fetch') line
        new_func = "const fetch = require('node-fetch');\n" + func
        cursor.execute("UPDATE tool SET func = ? WHERE id = ?;", (new_func, t_id))
        print(f"  Tool {name} updated (restored node-fetch requirement).")

conn.commit()
conn.close()
print("\nTools restored successfully.")
