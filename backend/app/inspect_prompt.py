import sqlite3
import json

db_path = '/app/app/database.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get the target chatflow
cursor.execute("SELECT flowData FROM chat_flow WHERE id = '7f5e8b09-0d49-4af1-bf25-966f611692ec';")
row = cursor.fetchone()
if row:
    flow = json.loads(row[0])
    nodes = flow.get('nodes', [])
    for node in nodes:
        name = node.get('data', {}).get('name')
        if name == 'chatPromptTemplate':
            print("=== SYSTEM MESSAGE ===")
            print(node['data']['inputs'].get('systemMessage'))

conn.close()
