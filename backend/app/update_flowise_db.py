import sqlite3
import json
import os

db_path = '/app/app/database.sqlite'
if not os.path.exists(db_path):
    print(f"Error: {db_path} does not exist!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Modify the Tools JavaScript code and schemas
cursor.execute("SELECT id, name, func, schema FROM tool;")
tools = cursor.fetchall()

modified_tools = [
    'buscar_pregunta_frecuente',
    'consultar_motivos_novedad',
    'consultar_operacion_logistica_por_id',
    'consultar_ticket_por_id',
    'transferir_a_asesor'
]

print("--- Modifying Tools ---")
for t_id, name, func, schema_str in tools:
    if name in modified_tools:
        print(f"Modifying tool: {name}")
        
        # A. Modify JS function code
        new_func = func
        # Add session_id resolution if not present
        if "const session_id =" not in new_func:
            # Insert at the beginning after const fetch or imports
            lines = new_func.split('\n')
            inserted = False
            for idx, line in enumerate(lines):
                if "const fetch =" in line or "require(" in line:
                    lines.insert(idx + 1, 'const session_id = $flow.chatId || "sess_default";')
                    inserted = True
                    break
            if not inserted:
                lines.insert(0, 'const session_id = $flow.chatId || "sess_default";')
            new_func = '\n'.join(lines)
            
        # Replace $session_id with session_id
        new_func = new_func.replace('encodeURIComponent($session_id)', 'encodeURIComponent(session_id)')
        new_func = new_func.replace('session_id: $session_id', 'session_id: session_id')
        new_func = new_func.replace('$session_id', 'session_id')
        
        # B. Modify Schema parameters (remove session_id)
        try:
            schema = json.loads(schema_str)
            new_schema = [param for param in schema if param.get('property') != 'session_id']
            new_schema_str = json.dumps(new_schema)
        except Exception as e:
            print(f"  Error parsing schema for {name}: {str(e)}")
            new_schema_str = schema_str
            
        # C. Update tool in SQLite
        cursor.execute("UPDATE tool SET func = ?, schema = ? WHERE id = ?;", (new_func, new_schema_str, t_id))
        print(f"  Tool {name} updated.")

# 2. Modify the Chatflow model configuration to llama-3.3-70b-versatile
cursor.execute("SELECT flowData FROM chat_flow WHERE id = '7f5e8b09-0d49-4af1-bf25-966f611692ec';")
cf_row = cursor.fetchone()
if cf_row:
    print("\n--- Modifying Chatflow ---")
    try:
        # FlowData in DB is a JSON string representing the dict
        flow_inner = json.loads(cf_row[0])
        
        nodes = flow_inner.get('nodes', [])
        modified_model = False
        for node in nodes:
            name = node.get('data', {}).get('name')
            if name == 'groqChat':
                print(f"Found Groq node: {node.get('id')}")
                inputs = node.get('data', {}).get('inputs', {})
                current_model = inputs.get('modelName')
                print(f"  Current model: {current_model}")
                # Change to llama-3.3-70b-versatile
                inputs['modelName'] = 'llama-3.3-70b-versatile'
                print("  Updated model to: llama-3.3-70b-versatile")
                modified_model = True
                
        if modified_model:
            new_flow_str = json.dumps(flow_inner)
            cursor.execute("UPDATE chat_flow SET flowData = ? WHERE id = '7f5e8b09-0d49-4af1-bf25-966f611692ec';", (new_flow_str,))
            print("Chatflow database record updated successfully.")
        else:
            print("No Groq model node found to modify.")
            
    except Exception as e:
        print("Error modifying chatflow:", str(e))
else:
    print("Main chatflow 7f5e8b09-0d49-4af1-bf25-966f611692ec not found in DB.")

conn.commit()
conn.close()
print("\nDatabase modifications saved.")
