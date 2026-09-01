import httpx
import json

token = 'EAAObD3p141wBSRkwpsURXRMgyESJuCfVdSjez36YYfnwgiP18OQZBxuWjtiCS2zq5yZB1ZADjK7sCvpDYebprJ4ikxLEQkeMb9OrGARY7HFAiejZCkquIXI2JOVO3DH45Dd6NUZB5AacW12ZCVYY3XS28PkgAgnWqqQvMAjSoDIcbUPNB06sLTozkT9aqZCGnAckzM0zcuynZAwt1UikeqmoxkhWKnH7OBBrSgSpBX4gXnx1AupGEKqZB1MkDeYaa0nUKjPEhz73k9qFM9p2Jf5kG'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

variations = [
    {
        'name': 'v3 with screen and data',
        'params': {
            'flow_message_version': '3',
            'flow_token': 'token_01',
            'flow_id': '4420144268227761',
            'flow_cta': 'Ver Catálogo',
            'flow_action': 'navigate',
            'flow_action_payload': {'screen': 'CATALOG_SCREEN', 'data': {}}
        }
    },
    {
        'name': 'v3 without payload',
        'params': {
            'flow_message_version': '3',
            'flow_token': 'token_01',
            'flow_id': '4420144268227761',
            'flow_cta': 'Ver Catálogo',
            'flow_action': 'navigate'
        }
    },
    {
        'name': 'v3 screen only',
        'params': {
            'flow_message_version': '3',
            'flow_token': 'token_01',
            'flow_id': '4420144268227761',
            'flow_cta': 'Ver Catálogo',
            'flow_action': 'navigate',
            'flow_action_payload': {'screen': 'CATALOG_SCREEN'}
        }
    },
    {
        'name': 'mode published',
        'params': {
            'mode': 'published',
            'flow_message_version': '3',
            'flow_token': 'token_01',
            'flow_id': '4420144268227761',
            'flow_cta': 'Ver Catálogo',
            'flow_action': 'navigate',
            'flow_action_payload': {'screen': 'CATALOG_SCREEN'}
        }
    },
    {
        'name': 'mode draft',
        'params': {
            'mode': 'draft',
            'flow_message_version': '3',
            'flow_token': 'token_01',
            'flow_id': '4420144268227761',
            'flow_cta': 'Ver Catálogo',
            'flow_action': 'navigate',
            'flow_action_payload': {'screen': 'CATALOG_SCREEN'}
        }
    }
]

for v in variations:
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': '593984407038',
        'type': 'interactive',
        'interactive': {
            'type': 'flow',
            'header': {'type': 'text', 'text': '🛠️ Ferretería Castor'},
            'body': {'text': 'Explora el catálogo interactivo de Ferretería Castor:'},
            'footer': {'text': 'Tienda Oficial'},
            'action': {
                'name': 'flow',
                'parameters': v['params']
            }
        }
    }
    r = httpx.post('https://graph.facebook.com/v20.0/1209791012207064/messages', json=payload, headers=headers)
    print(f"{v['name']}: status={r.status_code}, resp={r.text}")
