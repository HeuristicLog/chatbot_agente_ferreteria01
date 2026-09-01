import asyncio
import httpx
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_suite")

BACKEND_URL = "http://backend:8080"
GATEWAY_URL = "http://whatsapp-gateway:8090"
TEST_PHONE = "593984407038"

async def run_full_system_test():
    print("\n=======================================================")
    print("🚀 INICIANDO TEST COMPLETO DEL SISTEMA FERRETERÍA CASTOR")
    print("=======================================================\n")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Healthcheck Backend
        print("1️⃣ Verificando Healthcheck del Backend...")
        r_health = await client.get(f"{BACKEND_URL}/health")
        print(f"   Status: {r_health.status_code} | Response: {r_health.json()}")
        assert r_health.status_code == 200, "Backend health check falló"

        # 2. Healthcheck WhatsApp Gateway
        print("\n2️⃣ Verificando Healthcheck del WhatsApp Gateway...")
        r_gw = await client.get(f"{GATEWAY_URL}/health")
        print(f"   Status: {r_gw.status_code} | Response: {r_gw.json()}")
        assert r_gw.status_code == 200, "Gateway health check falló"

        # 3. Consulta de Catálogo y Categorías
        print("\n3️⃣ Verificando API de Catálogo de Productos...")
        r_cats = await client.get(f"{BACKEND_URL}/api/catalog/categories")
        print(f"   Categorías ({r_cats.status_code}): {[c['name'] for c in r_cats.json().get('data', [])]}")
        
        r_prods = await client.get(f"{BACKEND_URL}/api/catalog/products?sucursal=Centro")
        prods = r_prods.json().get("data", [])
        print(f"   Productos activos encontrados: {len(prods)}")
        assert len(prods) > 0, "No se encontraron productos en catálogo"
        p1 = prods[0]
        p2 = prods[1]
        print(f"   Producto muestra 1: {p1['name']} (${p1['price']:.2f}) [Stock Centro: {p1['sucursal_stocks'].get('Centro', 0)}]")
        print(f"   Producto muestra 2: {p2['name']} (${p2['price']:.2f}) [Stock Centro: {p2['sucursal_stocks'].get('Centro', 0)}]")

        # 4. Creación de Pedido y Descuento de Inventario
        print("\n4️⃣ Simulando creación de Pedido desde el Carrito Webview...")
        order_payload = {
            "customer_name": "Kevin Test Suite",
            "customer_phone": TEST_PHONE,
            "delivery_type": "pickup",
            "sucursal": "Centro",
            "payment_method": "efectivo",
            "items": [
                {"product_id": p1["id"], "quantity": 1},
                {"product_id": p2["id"], "quantity": 2}
            ]
        }
        r_order = await client.post(f"{BACKEND_URL}/api/catalog/orders", json=order_payload)
        assert r_order.status_code == 200, f"Error creando orden: {r_order.text}"
        order_data = r_order.json()["data"]
        order_number = order_data["order_number"]
        total_order = order_data["total"]
        print(f"   ✅ Pedido Creado con éxito: {order_number} | Total: ${total_order:.2f}")

        # 5. Consulta de Estado de Pedido
        print(f"\n5️⃣ Consultando estado del pedido {order_number}...")
        r_status = await client.get(f"{BACKEND_URL}/api/catalog/orders/{order_number}")
        assert r_status.status_code == 200, "Error consultando estado del pedido"
        status_info = r_status.json()["data"]
        print(f"   Estado: {status_info['status_display']} | Cliente: {status_info['customer_name']} | Items: {len(status_info['items'])}")

        from app.config import settings
        headers = {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

        # 6. Webhook WhatsApp: Mensaje 'hola' -> Menú de Bienvenida
        print("\n6️⃣ Simulando Webhook WhatsApp: Cliente envía 'hola'...")
        incoming_hola = {
            "phone": TEST_PHONE,
            "message": "hola",
            "message_id": "wamid.test_hola_001",
            "timestamp": "2026-09-01T15:00:00Z",
            "metadata": {
                "display_phone_number": "15556724304",
                "phone_number_id": "1209791012207064",
                "interactive_id": ""
            }
        }
        r_wh_hola = await client.post(f"{BACKEND_URL}/webhooks/whatsapp", json=incoming_hola, headers=headers)
        print(f"   Webhook 'hola' status: {r_wh_hola.status_code} | Resp: {r_wh_hola.json()}")

        # 7. Webhook WhatsApp: Click 'flow_catalogo' -> Tarjeta con Link
        print("\n7️⃣ Simulando Webhook WhatsApp: Cliente presiona '🛍️ Catálogo y Carrito'...")
        incoming_cat = {
            "phone": TEST_PHONE,
            "message": "🛍️ Catálogo y Carrito",
            "message_id": "wamid.test_cat_002",
            "timestamp": "2026-09-01T15:00:10Z",
            "metadata": {
                "display_phone_number": "15556724304",
                "phone_number_id": "1209791012207064",
                "interactive_id": "flow_catalogo"
            }
        }
        r_wh_cat = await client.post(f"{BACKEND_URL}/webhooks/whatsapp", json=incoming_cat, headers=headers)
        print(f"   Webhook 'flow_catalogo' status: {r_wh_cat.status_code} | Resp: {r_wh_cat.json()}")

        # 8. Webhook WhatsApp: Consulta directa de pedido escribiendo el código
        print(f"\n8️⃣ Simulando Webhook WhatsApp: Cliente escribe '{order_number}'...")
        incoming_order_query = {
            "phone": TEST_PHONE,
            "message": order_number,
            "message_id": "wamid.test_order_query_003",
            "timestamp": "2026-09-01T15:00:20Z",
            "metadata": {
                "display_phone_number": "15556724304",
                "phone_number_id": "1209791012207064",
                "interactive_id": ""
            }
        }
        r_wh_order = await client.post(f"{BACKEND_URL}/webhooks/whatsapp", json=incoming_order_query, headers=headers)
        print(f"   Webhook consulta orden status: {r_wh_order.status_code} | Resp: {r_wh_order.json()}")

        # 9. Verificación de la Webview HTML
        print("\n9️⃣ Verificando renderizado de la Webview Móvil (/catalogo)...")
        r_webview = await client.get(f"{BACKEND_URL}/catalogo?phone={TEST_PHONE}&sucursal=Centro")
        assert r_webview.status_code == 200, "Error cargando HTML de la Webview"
        print(f"   Webview HTML status: {r_webview.status_code} | Tamaño: {len(r_webview.text)} bytes")

    print("\n=======================================================")
    print("🎉 ¡TODAS LAS PRUEBAS DEL SISTEMA COMPLETADAS CON ÉXITO!")
    print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_full_system_test())
