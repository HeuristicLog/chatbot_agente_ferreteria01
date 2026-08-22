import json

try:
    with open('/app/app/flowise_tools.json', 'r', encoding='utf-16') as f:
        tools = json.load(f)
    print("Tools loaded successfully. Count:", len(tools))
    for t in tools:
        print(f"\n========================================\nName: {t.get('name')}\nDescription: {t.get('description')}\nSchema: {t.get('schema')}")
except Exception as e:
    print("Error:", str(e))
