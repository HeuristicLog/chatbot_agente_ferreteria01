import sqlite3
import json

try:
    conn = sqlite3.connect('/app/flowise-data/database.sqlite')
    cursor = conn.cursor()
    row = cursor.execute("SELECT flowData FROM chat_flow WHERE id = '7f5e8b09-0d49-4af1-bf25-966f611692ec'").fetchone()
    if row:
        flow_data = json.loads(row[0])
        with open('/app/data/flow_data.json', 'w', encoding='utf-8') as f:
            json.dump(flow_data, f, indent=2, ensure_ascii=False)
        print("flow_data.json exported successfully.")
except Exception as e:
    print("Error:", e)
finally:
    if 'conn' in locals():
        conn.close()
