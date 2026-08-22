import httpx
import sys

# Get message from argument or default
message = sys.argv[1] if len(sys.argv) > 1 else "cuales son sus politicas"

url = "http://localhost:8080/webhooks/whatsapp"
headers = {"X-Internal-API-Key": "change_me", "Content-Type": "application/json"}
payload = {
    "phone": "593984407038",
    "message": message,
    "message_id": "msg-" + str(hash(message)),
    "metadata": {"provider": "mock"}
}
try:
    resp = httpx.post(url, json=payload, headers=headers, timeout=20.0)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
except Exception as e:
    print("Error:", str(e))
