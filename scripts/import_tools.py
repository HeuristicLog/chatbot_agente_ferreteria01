import os
import json
import httpx
import asyncio

FLOWISE_URL = "http://host.docker.internal:3000/api/v1/tools"
API_KEY = "AbIlSQHbL25uNlQ--mhjxDgxs_8MqMW6asszKbDapw4"
WORKSPACE_ID = "902c50d0-ce33-4380-b2e5-d13eb0c393f8"

async def import_tools():
    tools_dir = "flowise/tools"
    files = [f for f in os.listdir(tools_dir) if f.endswith(".json")]
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, let's query existing tools to see if any are already imported
        try:
            get_resp = await client.get(FLOWISE_URL, headers=headers)
            existing_tools = get_resp.json()
            existing_names = {t["name"] for t in existing_tools} if isinstance(existing_tools, list) else set()
            print(f"Found {len(existing_names)} existing tools in Flowise.")
        except Exception as e:
            print(f"Error querying existing tools: {e}")
            existing_names = set()
            
        for file in files:
            file_path = os.path.join(tools_dir, file)
            with open(file_path, "r", encoding="utf-8") as f:
                tool_data = json.load(f)
                
            # Skip if already exists
            if tool_data["name"] in existing_names:
                print(f"Tool '{tool_data['name']}' already exists. Skipping.")
                continue
                
            # Associate workspace ID
            tool_data["workspaceId"] = WORKSPACE_ID
            
            try:
                resp = await client.post(FLOWISE_URL, json=tool_data, headers=headers)
                if resp.status_code in (200, 201):
                    print(f"Successfully imported tool: {tool_data['name']}")
                else:
                    print(f"Failed to import tool '{tool_data['name']}': {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"Exception importing tool '{tool_data['name']}': {e}")

if __name__ == "__main__":
    asyncio.run(import_tools())
