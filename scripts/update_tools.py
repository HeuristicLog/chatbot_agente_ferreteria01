import os
import json
import httpx
import asyncio

FLOWISE_BASE_URL = "http://flowise:3000/api/v1/tools"
# The API key is in the .env file as FLOWISE_API_KEY
API_KEY = "AbIlSQHbL25uNlQ--mhjxDgxs_8MqMW6asszKbDapw4"

async def update_tools():
    tools_dir = "flowise/tools"
    files = [f for f in os.listdir(tools_dir) if f.endswith(".json")]
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Query existing tools
        try:
            get_resp = await client.get(FLOWISE_BASE_URL, headers=headers)
            existing_tools = get_resp.json()
            existing_tool_map = {t["name"]: t["id"] for t in existing_tools} if isinstance(existing_tools, list) else {}
            print(f"Found {len(existing_tool_map)} existing tools in Flowise.")
        except Exception as e:
            print(f"Error querying existing tools: {e}")
            existing_tool_map = {}
            
        for file in files:
            file_path = os.path.join(tools_dir, file)
            with open(file_path, "r", encoding="utf-8") as f:
                tool_data = json.load(f)
                
            tool_name = tool_data["name"]
            
            # Check if it already exists
            if tool_name in existing_tool_map:
                tool_id = existing_tool_map[tool_name]
                print(f"Updating existing tool '{tool_name}' (ID: {tool_id})...")
                url = f"{FLOWISE_BASE_URL}/{tool_id}"
                try:
                    resp = await client.put(url, json=tool_data, headers=headers)
                    if resp.status_code in (200, 201):
                        print(f"Successfully updated tool: {tool_name}")
                    else:
                        print(f"Failed to update tool '{tool_name}': {resp.status_code} - {resp.text}")
                except Exception as e:
                    print(f"Exception updating tool '{tool_name}': {e}")
            else:
                print(f"Creating new tool '{tool_name}'...")
                try:
                    resp = await client.post(FLOWISE_BASE_URL, json=tool_data, headers=headers)
                    if resp.status_code in (200, 201):
                        print(f"Successfully created tool: {tool_name}")
                    else:
                        print(f"Failed to create tool '{tool_name}': {resp.status_code} - {resp.text}")
                except Exception as e:
                    print(f"Exception creating tool '{tool_name}': {e}")

if __name__ == "__main__":
    asyncio.run(update_tools())
