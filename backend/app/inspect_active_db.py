import sqlite3
import json

db_path = '/app/app/active_database.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check model in chatflow
cursor.execute("SELECT flowData FROM chat_flow WHERE id = '7f5e8b09-0d49-4af1-bf25-966f611692ec';")
row = cursor.fetchone()
if row:
    flow = json.loads(row[0])
    nodes = flow.get('nodes', [])
    for node in nodes:
        name = node.get('data', {}).get('name')
        if name == 'groqChat':
            inputs = node.get('data', {}).get('inputs', {})
            print("Groq model:", inputs.get('modelName'))

# Check buscar_pregunta_frecuente tool
cursor.execute("SELECT name, func, schema FROM tool WHERE name = 'buscar_pregunta_frecuente';")
tool = cursor.fetchone()
if tool:
    print("\nTool:", tool[0])
    print("Code:")
    print(tool[1])
    print("Schema:", tool[2])

conn.close()
