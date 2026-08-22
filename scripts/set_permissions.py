import sqlite3
import json

permissions_list = [
    "chatflows:view", "chatflows:create", "chatflows:update", "chatflows:duplicate", "chatflows:delete", 
    "chatflows:export", "chatflows:import", "chatflows:config", "chatflows:domains", 
    "agentflows:view", "agentflows:create", "agentflows:update", "agentflows:duplicate", "agentflows:delete", 
    "agentflows:export", "agentflows:import", "agentflows:config", "agentflows:domains", 
    "tools:view", "tools:create", "tools:update", "tools:delete", "tools:export", 
    "assistants:view", "assistants:create", "assistants:update", "assistants:delete", 
    "credentials:view", "credentials:create", "credentials:update", "credentials:delete", "credentials:share", 
    "variables:view", "variables:create", "variables:update", "variables:delete", 
    "apikeys:view", "apikeys:create", "apikeys:update", "apikeys:delete", "apikeys:import", 
    "documentStores:view", "documentStores:create", "documentStores:update", "documentStores:delete", 
    "documentStores:add-loader", "documentStores:delete-loader", "documentStores:preview-process", "documentStores:upsert-config", 
    "datasets:view", "datasets:create", "datasets:update", "datasets:delete", 
    "evaluators:view", "evaluators:create", "evaluators:update", "evaluators:delete", 
    "evaluations:view", "evaluations:create", "evaluations:update", "evaluations:delete", "evaluations:run", 
    "templates:marketplace", "templates:custom", "templates:custom-delete", "templates:toolexport", 
    "templates:flowexport", "templates:custom-share", 
    "workspace:export", "workspace:import", 
    "executions:view", "executions:delete"
]

try:
    conn = sqlite3.connect('/app/flowise-data/database.sqlite')
    cursor = conn.cursor()
    permissions_str = json.dumps(permissions_list)
    cursor.execute(
        "UPDATE apikey SET permissions = ? WHERE keyName = 'Castor Bot'",
        (permissions_str,)
    )
    conn.commit()
    print("API Key permissions updated successfully.")
except Exception as e:
    print("Error:", e)
finally:
    if 'conn' in locals():
        conn.close()
