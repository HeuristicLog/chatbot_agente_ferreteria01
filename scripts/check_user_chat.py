import httpx

headers = {'api_access_token': 'mMJycxtZ3GBmQhNBS3VaJgXC'}
r = httpx.get('https://app.chatwoot.com/api/v1/accounts/193795/contacts/search?q=593984407038', headers=headers)
print('Search contact status:', r.status_code)
if r.status_code == 200:
    contacts = r.json().get('payload', [])
    print(f'Total contacts: {len(contacts)}')
    for c in contacts:
        cid = c.get('id')
        name = c.get('name')
        phone = c.get('phone_number')
        print(f'Contact ID: {cid} | Name: {name} | Phone: {phone}')
        r_conv = httpx.get(f'https://app.chatwoot.com/api/v1/accounts/193795/contacts/{cid}/conversations', headers=headers)
        if r_conv.status_code == 200:
            for cv in r_conv.json().get('payload', []):
                cvid = cv.get('id')
                status = cv.get('status')
                inbox = cv.get('inbox_id')
                print(f'   -> Conv #{cvid} | Inbox: {inbox} | Status: {status}')
                r_msg = httpx.get(f'https://app.chatwoot.com/api/v1/accounts/193795/conversations/{cvid}/messages', headers=headers)
                if r_msg.status_code == 200:
                    for m in r_msg.json().get('payload', [])[-5:]:
                        m_type = 'IN' if m.get('message_type') == 0 else ('OUT' if m.get('message_type') == 1 else 'NOTE')
                        content = (m.get('content') or '')[:70]
                        created_at = m.get('created_at')
                        print(f'      [{m_type}] {created_at}: {content}')
