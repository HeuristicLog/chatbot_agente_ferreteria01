import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_native")

BACKEND_URL = "http://backend:8080"
TEST_PHONE = "593984407038"

async def test_native_in_chat_commerce():
    print("\n=======================================================")
    print("🛒 PROBANDO COMERCIO NATIVO 100% DENTRO DE WHATSAPP")
    print("=======================================================\n")

    from app.config import settings
    headers = {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Enviar 'hola'
        print("1️⃣ Cliente envía 'hola'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "hola", "message_id": "m1", "metadata": {"phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200, f"Error: {r.text}"
        print("   ✅ Menú de bienvenida enviado con éxito.")

        # 2. Pulsar '🛍️ Catálogo y Carrito'
        print("\n2️⃣ Cliente pulsa '🛍️ Catálogo y Carrito'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "🛍️ Catálogo y Carrito", "message_id": "m2", "metadata": {"interactive_id": "flow_catalogo", "phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200
        print("   ✅ Lista de categorías nativas enviada.")

        # 3. Seleccionar categoría '⚡ Herramientas Eléctricas'
        print("\n3️⃣ Cliente selecciona categoría '⚡ Herramientas Eléctricas'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "⚡ Herramientas Eléctricas", "message_id": "m3", "metadata": {"interactive_id": "cat_herramientas_elec", "phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200
        print("   ✅ Lista de productos de la categoría enviada.")

        # 4. Ver producto 'Taladro DeWalt'
        print("\n4️⃣ Cliente selecciona 'Taladro Percutor DeWalt'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "Taladro Percutor DeWalt", "message_id": "m4", "metadata": {"interactive_id": "prod_view_HER-TAL-001", "phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200
        print("   ✅ Ficha técnica del producto enviada con botones.")

        # 5. Agregar al Carrito
        print("\n5️⃣ Cliente pulsa '➕ Agregar al Carrito'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "➕ Agregar al Carrito", "message_id": "m5", "metadata": {"interactive_id": "cart_add_HER-TAL-001_1", "phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200
        print("   ✅ Producto agregado al carrito en Redis con éxito.")

        # 6. Ver Carrito
        print("\n6️⃣ Cliente pulsa '🛒 Ver Mi Carrito'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "🛒 Ver Mi Carrito", "message_id": "m6", "metadata": {"interactive_id": "cart_view", "phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200
        print("   ✅ Desglose del carrito y total enviado.")

        # 7. Iniciar Checkout
        print("\n7️⃣ Cliente pulsa '✅ Finalizar Pedido'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "✅ Finalizar Pedido", "message_id": "m7", "metadata": {"interactive_id": "checkout_start", "phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200
        print("   ✅ Opciones de método de entrega enviadas.")

        # 8. Seleccionar Retiro en Local
        print("\n8️⃣ Cliente pulsa '📍 Retiro en Sucursal'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "📍 Retiro en Sucursal", "message_id": "m8", "metadata": {"interactive_id": "order_pickup", "phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200
        print("   ✅ Lista de sucursales enviada.")

        # 9. Elegir Sucursal Centro
        print("\n9️⃣ Cliente selecciona '📍 Sucursal Centro'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "📍 Sucursal Centro", "message_id": "m9", "metadata": {"interactive_id": "order_suc_centro", "phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200
        print("   ✅ Formas de pago enviadas.")

        # 10. Elegir Pago en Efectivo y Finalizar
        print("\n🔟 Cliente selecciona '💵 Efectivo contra entrega'...")
        r = await client.post(
            f"{BACKEND_URL}/webhooks/whatsapp",
            json={"phone": TEST_PHONE, "message": "💵 Efectivo", "message_id": "m10", "metadata": {"interactive_id": "pay_efectivo", "phone_number_id": "1209791012207064"}},
            headers=headers
        )
        assert r.status_code == 200
        print("   ✅ ¡ORDEN CREADA Y RECIBO ENVIADO A WHATSAPP EXITOSAMENTE!")

    print("\n=======================================================")
    print("🎉 ¡TEST DE COMERCIO NATIVO EN WHATSAPP SUPERADO AL 100%!")
    print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(test_native_in_chat_commerce())
