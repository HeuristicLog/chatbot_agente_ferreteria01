import os
import json

LOG_PATH = r"C:\Users\User\.gemini\antigravity\brain\dd2cd15a-072b-477d-880a-49b18eff382d\.system_generated\logs\transcript.jsonl"

def main():
    if not os.path.exists(LOG_PATH):
        print("Log not found.")
        return
        
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                step_idx = data.get("step_index", 0)
                if step_idx >= 1000:
                    continue
                content = data.get("content", "")
                if "8000" in content or "mock_logistics" in content or "logistica" in content.lower():
                    print(f"[{data.get('type')}] Index: {step_idx}")
                    print(content[:500])
                    print("-" * 50)
            except Exception as e:
                pass

if __name__ == "__main__":
    main()
