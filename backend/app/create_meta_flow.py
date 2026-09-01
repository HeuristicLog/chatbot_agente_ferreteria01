import httpx
import json

token = 'EAATsX7XPiBgBSfOZByNBbXNV2hvO7e8SC6MWdkPSLYz5ei3umbmwYwPT0YSZCH9Oo2AM9n5regE0Y1wUTZBzdR0CqFVtPMYiW0mu3me8CFr0mKgy3TAC7AhgQCaKhFvckRbXcIr9jyQVBe61WDlVTvUbdpLdViLxat3n0QzgLris7ABfLMPm3ggGoDoHhm1jcmZCFohZCJFT4pZCxBcbzMyxYoIXI9QSj8HIrY4xRd9UzCS6coeT10kDXukuAsGC5BFaDxZAlMX7ogjiZAdnWFMh'
waba_id = '980422014478629'
phone_number_id = '1163688356822125'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# 1. Crear Flow
create_payload = {
    "name": "Catalogo Castor 01",
    "categories": ["SHOP_BROWSE_AND_ORDER"]
}

r = httpx.post(f'https://graph.facebook.com/v20.0/{waba_id}/flows', json=create_payload, headers=headers)
print('Create flow result:', r.status_code, r.text)

if r.status_code != 200:
    # Try categories OTHER
    create_payload["categories"] = ["OTHER"]
    r = httpx.post(f'https://graph.facebook.com/v20.0/{waba_id}/flows', json=create_payload, headers=headers)
    print('Create flow (OTHER) result:', r.status_code, r.text)

if r.status_code == 200:
    flow_id = r.json().get('id')
    print(f'Flow created with ID: {flow_id}')
    
    # 2. Upload Flow JSON
    with open('app/flows/castor_catalog_flow.json', 'r', encoding='utf-8') as f:
        flow_json_content = f.read()
    
    files = {
        'file': ('flow.json', flow_json_content, 'application/json')
    }
    data = {
        'name': 'flow.json',
        'asset_type': 'FLOW_JSON'
    }
    upload_headers = {'Authorization': f'Bearer {token}'}
    r_upload = httpx.post(f'https://graph.facebook.com/v20.0/{flow_id}/assets', data=data, files=files, headers=upload_headers)
    print('Upload asset result:', r_upload.status_code, r_upload.text)
    
    # 3. Publish Flow
    r_pub = httpx.post(f'https://graph.facebook.com/v20.0/{flow_id}/publish', headers=headers)
    print('Publish result:', r_pub.status_code, r_pub.text)
    
    # 4. Test Send Flow to 593984407038
    send_payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': '593984407038',
        'type': 'interactive',
        'interactive': {
            'type': 'flow',
            'header': {'type': 'text', 'text': '🛠️ Ferretería Castor'},
            'body': {'text': '¡Bienvenido a Ferretería Castor! 🦫\n\nToca el botón abajo para abrir la tienda interactiva dentro de WhatsApp.'},
            'footer': {'text': 'Tienda Oficial'},
            'action': {
                'name': 'flow',
                'parameters': {
                    'flow_message_version': '3',
                    'flow_token': 'token_01',
                    'flow_id': str(flow_id),
                    'flow_cta': 'Ver Catálogo 🛍️',
                    'flow_action': 'navigate',
                    'flow_action_payload': {
                        'screen': 'CATALOG_SCREEN'
                    }
                }
            }
        }
    }
    r_send = httpx.post(f'https://graph.facebook.com/v20.0/{phone_number_id}/messages', json=send_payload, headers=headers)
    print('Send Flow Test result:', r_send.status_code, r_send.text)
