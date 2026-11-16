import httpx
import json

token = "mMJycxtZ3GBmQhNBS3VaJgXC"
account_id = "193795"
headers = {"api_access_token": token, "Content-Type": "application/json"}

# 1. Inboxes
r_inboxes = httpx.get(f"https://app.chatwoot.com/api/v1/accounts/{account_id}/inboxes", headers=headers)
print("=== INBOXES EN CHATWOOT ===")
if r_inboxes.status_code == 200:
    for ib in r_inboxes.json().get("payload", []):
        print(f"ID: {ib.get('id')} | Nombre: {ib.get('name')} | Canal: {ib.get('channel_type')}")
else:
    print(f"Error inboxes: {r_inboxes.status_code} {r_inboxes.text}")

# 2. Webhooks
r_webhooks = httpx.get(f"https://app.chatwoot.com/api/v1/accounts/{account_id}/webhooks", headers=headers)
print("\n=== WEBHOOKS CONFIGURADOS EN CHATWOOT ===")
if r_webhooks.status_code == 200:
    for wh in r_webhooks.json().get("payload", []):
        print(f"ID: {wh.get('id')} | URL: {wh.get('url')} | Subscriptions: {wh.get('subscriptions')}")
else:
    print(f"Error webhooks: {r_webhooks.status_code} {r_webhooks.text}")

# 3. Ultimas 5 conversaciones de cada bandeja
for ib_id in [150556, 151924]:
    print(f"\n=== ULTIMAS CONVERSACIONES BANDEJA {ib_id} ===")
    r_c = httpx.get(f"https://app.chatwoot.com/api/v1/accounts/{account_id}/conversations?inbox_id={ib_id}", headers=headers)
    if r_c.status_code == 200:
        convs = r_c.json().get("data", {}).get("payload", [])[:3]
        for c in convs:
            cid = c.get("id")
            c_sender = c.get("meta", {}).get("sender", {}).get("name")
            c_phone = c.get("meta", {}).get("sender", {}).get("phone_number")
            c_status = c.get("status")
            print(f"Chat #{cid} | Contacto: {c_sender} ({c_phone}) | Estado: {c_status} | Labels: {c.get('labels')}")
    else:
        print(f"Error convs: {r_c.status_code}")
