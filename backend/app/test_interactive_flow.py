"""Test the full interactive WhatsApp flow end-to-end."""
import asyncio
import httpx
import json

BACKEND = "http://backend:8080"
GATEWAY = "http://whatsapp-gateway:8090"
API_KEY = "change_me"
PHONE = "593987654321"

headers = {"X-Internal-API-Key": API_KEY, "Content-Type": "application/json"}

async def send_message(message: str, interactive_id: str = ""):
    metadata = {}
    if interactive_id:
        metadata["interactive_id"] = interactive_id
        metadata["is_interactive"] = True
        metadata["provider"] = "meta"
    else:
        metadata["provider"] = "meta"
    
    payload = {
        "phone": PHONE,
        "message": message,
        "message_id": f"msg_{abs(hash(message + interactive_id))}",
        "metadata": metadata
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND}/webhooks/whatsapp", json=payload, headers=headers, timeout=30)
        return resp.status_code, resp.json()

async def check_gateway_buttons():
    """Test the /send/buttons gateway endpoint directly."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GATEWAY}/send/buttons",
            json={
                "phone": PHONE,
                "body": "Prueba de botones interactivos",
                "buttons": [
                    {"id": "btn1", "title": "Opción 1"},
                    {"id": "btn2", "title": "Opción 2"},
                    {"id": "btn3", "title": "Opción 3"},
                ],
                "header": "🧪 Test",
                "footer": "Ferretería Castor"
            },
            headers=headers,
            timeout=10
        )
        return resp.status_code, resp.json()

async def check_gateway_list():
    """Test the /send/list gateway endpoint directly."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GATEWAY}/send/list",
            json={
                "phone": PHONE,
                "body": "Selecciona una categoría",
                "button_text": "Ver opciones",
                "sections": [
                    {"title": "Categorías", "rows": [
                        {"id": "c1", "title": "Envíos", "description": "Políticas de envío"},
                        {"id": "c2", "title": "Garantía", "description": "Garantías y devoluciones"},
                    ]}
                ],
                "header": "❓ FAQ",
            },
            headers=headers,
            timeout=10
        )
        return resp.status_code, resp.json()

async def main():
    print("=" * 60)
    print("TEST: Interactive WhatsApp Flow")
    print("=" * 60)

    # Test 1: Gateway /send/buttons
    print("\n1. Gateway /send/buttons endpoint...")
    status, resp = await check_gateway_buttons()
    print(f"   Status: {status} | Response: {resp}")

    # Test 2: Gateway /send/list
    print("\n2. Gateway /send/list endpoint...")
    status, resp = await check_gateway_list()
    print(f"   Status: {status} | Response: {resp}")

    # Test 3: Greeting → Welcome Menu
    print("\n3. Sending 'Hola' → should return welcome menu...")
    status, resp = await send_message("Hola")
    print(f"   Status: {status} | {resp}")

    await asyncio.sleep(2)

    # Test 4: Button click → FAQ list
    print("\n4. Clicking 'flow_faq' button → should return FAQ list...")
    status, resp = await send_message("❓ Preguntas frecuentes", interactive_id="flow_faq")
    print(f"   Status: {status} | {resp}")

    await asyncio.sleep(1)

    # Test 5: FAQ item click → specific answer
    print("\n5. Clicking 'faq_envios' → should return shipping info...")
    status, resp = await send_message("🚚 Envíos y entregas", interactive_id="faq_envios")
    print(f"   Status: {status} | {resp}")

    await asyncio.sleep(1)

    # Test 6: Order status flow
    print("\n6. Clicking 'flow_pedido' → should ask for order ID...")
    status, resp = await send_message("📦 Mi pedido", interactive_id="flow_pedido")
    print(f"   Status: {status} | {resp}")

    await asyncio.sleep(1)

    # Test 7: Enter order ID
    print("\n7. Sending order ID '1' → should show order status...")
    status, resp = await send_message("1")
    print(f"   Status: {status} | {resp}")

    await asyncio.sleep(1)

    # Test 8: Free-text AI question
    print("\n8. Free-text question → should respond with AI + nav buttons...")
    status, resp = await send_message("cual es el horario de atencion")
    print(f"   Status: {status} | {resp}")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
