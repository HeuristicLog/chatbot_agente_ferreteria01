import urllib.request
import json

def check_chatwoot():
    print("=== CHATWOOT INBOXES ===")
    req = urllib.request.Request(
        'https://app.chatwoot.com/api/v1/accounts/193795/inboxes',
        headers={'api_access_token': 'mMJycxtZ3GBmQhNBS3VaJgXC', 'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode('utf-8'))
    for ib in data.get('payload', []):
        print(f"ID: {ib.get('id')} | Name: {ib.get('name')} | Channel: {ib.get('channel_type')}")

    print("\n=== RECENT CHATWOOT CONVERSATIONS / CONTACTS ===")
    req2 = urllib.request.Request(
        'https://app.chatwoot.com/api/v1/accounts/193795/conversations',
        headers={'api_access_token': 'mMJycxtZ3GBmQhNBS3VaJgXC', 'Content-Type': 'application/json'}
    )
    resp2 = urllib.request.urlopen(req2)
    data2 = json.loads(resp2.read().decode('utf-8'))
    convs = data2.get('data', {}).get('payload', [])
    print(f"Total conversaciones: {len(convs)}")
    for c in convs[:5]:
        sender = c.get('meta', {}).get('sender', {})
        print(f"Conv #{c.get('id')} | Contact: {sender.get('name')} ({sender.get('phone_number')}) | Inbox ID: {c.get('inbox_id')} | Status: {c.get('status')}")

def check_evolution():
    print("\n=== EVOLUTION API INSTANCES ===")
    req = urllib.request.Request(
        'http://localhost:8082/instance/fetchInstances',
        headers={'apikey': 'ferreteria_evolution_key_2026', 'Content-Type': 'application/json'}
    )
    try:
        resp = urllib.request.urlopen(req)
        instances = json.loads(resp.read().decode('utf-8'))
        for inst in instances:
            print(f"Name: {inst.get('name')} | Status: {inst.get('connectionStatus')} | Owner: {inst.get('ownerJid')}")
    except Exception as e:
        print(f"Error fetching Evolution instances: {e}")

if __name__ == '__main__':
    check_evolution()
    check_chatwoot()
