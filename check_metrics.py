import urllib.request
import json

def get_attrs():
    req = urllib.request.Request(
        'https://app.chatwoot.com/api/v1/accounts/193795/custom_attribute_definitions',
        headers={'api_access_token': 'mMJycxtZ3GBmQhNBS3VaJgXC', 'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode('utf-8'))
    print("=== CHATWOOT CUSTOM ATTRIBUTES ===")
    for a in data:
        print(f"Key: {a.get('attribute_key')} | Name: {a.get('attribute_display_name')} | Type: {a.get('attribute_display_type')} | Model: {a.get('attribute_model')}")

if __name__ == '__main__':
    get_attrs()
