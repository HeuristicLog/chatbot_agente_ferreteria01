import httpx
import json

url = "http://flowise:3000/api/v1/prediction/7f5e8b09-0d49-4af1-bf25-966f611692ec"
headers = {
    "Authorization": "Bearer AbIlSQHbL25uNlQ--mhjxDgxs_8MqMW6asszKbDapw4",
    "Content-Type": "application/json"
}
payload = {
    "question": "quiero hablar con un asesor",
    "overrideConfig": {
        "sessionId": "sess_test_direct"
    }
}

try:
    resp = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    print("Status:", resp.status_code)
    print("Raw Response:", json.dumps(resp.json(), indent=2))
except Exception as e:
    print("Error:", str(e))
