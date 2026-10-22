"""
Comprehensive End-to-End Test Suite for AutoEcuador Motors WhatsApp Sales Bot
Customer Phone: 593988921136
"""
import asyncio
import httpx
import json
import uuid

BASE_URL = "http://localhost:8080"
INTERNAL_KEY = "change_me"
HEADERS = {"X-Internal-API-Key": INTERNAL_KEY, "Content-Type": "application/json"}
CUSTOMER_PHONE = "593988921136"

async def test_all_scenarios():
    print("=" * 70)
    print("🚀 INICIANDO BATERÍA DE PRUEBAS INTEGRALES — AUTOECUADOR MOTORS 🇪🇨")
    print(f"📱 Teléfono de prueba del cliente: +{CUSTOMER_PHONE}")
    print("=" * 70)

    results = []

    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=15.0) as client:
        
        run_id = uuid.uuid4().hex[:6]
        # ── Test 1: Saludo Inicial ("Hola") ──
        print("\n[1] Probando saludo inicial del cliente ('Hola')...")
        payload = {"phone": CUSTOMER_PHONE, "message": "Hola", "message_id": f"MSG-HOLA-{run_id}"}
        res = await client.post("/webhooks/whatsapp", json=payload)
        assert res.status_code == 200, f"Error {res.status_code}: {res.text}"
        data = res.json()
        print(f"  -> Resultado: HTTP {res.status_code} | Status: {data.get('status')}")
        results.append(("Saludo Inicial ('Hola')", res.status_code == 200))

        # ── Test 2: Consulta Camionetas 4x4 ──
        print("\n[2] Probando consulta comercial de Camionetas 4x4...")
        payload = {"phone": CUSTOMER_PHONE, "message": "Qué camionetas 4x4 tienen y qué precios tienen?", "message_id": f"MSG-4X4-{run_id}"}
        res = await client.post("/webhooks/whatsapp", json=payload)
        assert res.status_code == 200
        print(f"  -> Resultado: HTTP {res.status_code} | Status: {res.json().get('status')}")
        results.append(("Consulta Camionetas 4x4", res.status_code == 200))

        # ── Test 3: Consulta Autos Híbridos / Pico y Placa ──
        print("\n[3] Probando consulta de Autos Híbridos / Pico y Placa...")
        payload = {"phone": CUSTOMER_PHONE, "message": "Quiero un carro híbrido para no tener pico y placa en Quito", "message_id": f"MSG-HEV-{run_id}"}
        res = await client.post("/webhooks/whatsapp", json=payload)
        assert res.status_code == 200
        print(f"  -> Resultado: HTTP {res.status_code} | Status: {res.json().get('status')}")
        results.append(("Consulta Híbridos / Pico y Placa", res.status_code == 200))

        # ── Test 4: Consulta Plan Retoma (Auto Usado) ──
        print("\n[4] Probando consulta de Plan Retoma (Auto usado como parte de pago)...")
        payload = {"phone": CUSTOMER_PHONE, "message": "Tengo un auto usado para dar como parte de pago", "message_id": f"MSG-RETOMA-{run_id}"}
        res = await client.post("/webhooks/whatsapp", json=payload)
        assert res.status_code == 200
        print(f"  -> Resultado: HTTP {res.status_code} | Status: {res.json().get('status')}")
        results.append(("Consulta Plan Retoma", res.status_code == 200))

        # ── Test 5: Consulta SUVs Familiares ──
        print("\n[5] Probando consulta de SUVs Familiares...")
        payload = {"phone": CUSTOMER_PHONE, "message": "Qué SUVs familiares me recomiendan?", "message_id": f"MSG-SUV-{run_id}"}
        res = await client.post("/webhooks/whatsapp", json=payload)
        assert res.status_code == 200
        print(f"  -> Resultado: HTTP {res.status_code} | Status: {res.json().get('status')}")
        results.append(("Consulta SUVs Familiares", res.status_code == 200))

        # ── Test 6: Consulta por Presupuesto de Entrada ──
        print("\n[6] Probando consulta por presupuesto de entrada ($5,000)...")
        payload = {"phone": CUSTOMER_PHONE, "message": "Tengo 5000 de entrada qué auto me alcanza?", "message_id": f"MSG-PRESUPUESTO-{run_id}"}
        res = await client.post("/webhooks/whatsapp", json=payload)
        assert res.status_code == 200
        print(f"  -> Resultado: HTTP {res.status_code} | Status: {res.json().get('status')}")
        results.append(("Consulta por Presupuesto de Entrada", res.status_code == 200))

        # ── Test 7: Consulta de Test Drive ──
        print("\n[7] Probando consulta de Test Drive...")
        payload = {"phone": CUSTOMER_PHONE, "message": "Cómo agendo una prueba de manejo o test drive?", "message_id": f"MSG-TESTDRIVE-{run_id}"}
        res = await client.post("/webhooks/whatsapp", json=payload)
        assert res.status_code == 200
        print(f"  -> Resultado: HTTP {res.status_code} | Status: {res.json().get('status')}")
        results.append(("Consulta Test Drive", res.status_code == 200))

        # ── Test 8: Webhook entrante con formato nativo de Evolution API v2 ──
        print("\n[8] Probando webhook con formato nativo de Evolution API (messages.upsert)...")
        evolution_payload = {
            "event": "messages.upsert",
            "instance": "sucursal_centro",
            "data": {
                "key": {
                    "remoteJid": f"{CUSTOMER_PHONE}@s.whatsapp.net",
                    "fromMe": False,
                    "id": f"EVO-TEST-MSG-{run_id}"
                },
                "pushName": "Kevin WhatsApp",
                "message": {
                    "conversation": "Hola Alex, quiero ver el catálogo"
                },
                "messageType": "conversation"
            }
        }
        res = await client.post("/webhooks/whatsapp", json=evolution_payload, headers={"apikey": "ferreteria_evolution_key_2026"})
        assert res.status_code == 200, f"Error: {res.text}"
        print(f"  -> Resultado: HTTP {res.status_code} | Status: {res.json().get('status')}")
        results.append(("Webhook Nativo Evolution API", res.status_code == 200))

        # ── Test 9: Webview In-App Browser — Guardar en 'Mi Garaje' (Persistencia PostgreSQL) ──
        print("\n[9] Probando guardado en 'Mi Garaje' desde Webview...")
        res_veh = await client.get("/api/v1/vehicles")
        assert res_veh.status_code == 200
        vehicles = res_veh.json().get("data", [])
        assert len(vehicles) > 0, "No hay vehículos cargados en BD"
        chosen_veh = vehicles[0]
        
        cart_payload = {
            "customer_phone": CUSTOMER_PHONE,
            "vehicle_code": chosen_veh["code"],
            "down_payment_percent": 20,
            "down_payment_amount": chosen_veh["min_down_payment"],
            "term_months": 60,
            "estimated_monthly_fee": chosen_veh["estimated_monthly_fee"]
        }
        res_cart = await client.post("/api/v1/vehicles/cart", json=cart_payload)
        assert res_cart.status_code == 200, f"Error: {res_cart.text}"
        cart_data = res_cart.json()
        print(f"  -> Guardado en Garaje: Status '{cart_data.get('status')}' para {chosen_veh['brand']} {chosen_veh['model']}")
        print(f"  -> Mensaje: {cart_data.get('message')}")
        results.append(("Persistencia Mi Garaje (vehicle_cart_items)", res_cart.status_code == 200))

        # ── Test 10: Webview In-App Browser — Generar Cotización Formal (Persistencia PostgreSQL) ──
        print("\n[10] Probando generación de Cotización Formal...")
        quote_payload = {
            "customer_phone": CUSTOMER_PHONE,
            "customer_name": "Kevin Cliente",
            "city": "Quito",
            "vehicle_code": chosen_veh["code"],
            "down_payment_percent": 20,
            "down_payment_amount": chosen_veh["min_down_payment"],
            "term_months": 60,
            "monthly_fee": chosen_veh["estimated_monthly_fee"],
            "insurance_included": True,
            "trade_in_used_car": True,
            "used_car_details": "Chevrolet Aveo 2018 con 85.000 km"
        }
        res_quote = await client.post("/api/v1/vehicles/quote", json=quote_payload)
        assert res_quote.status_code == 200, f"Error: {res_quote.text}"
        quote_data = res_quote.json()
        quote_num = quote_data.get("quote_code")
        print(f"  -> Cotización Generada con éxito: {quote_num}")
        print(f"  -> Mensaje: {quote_data.get('message')}")
        results.append(("Persistencia Cotización Formal (vehicle_quotes)", res_quote.status_code == 200))

        # ── Test 11: Webview In-App Browser — Registrar Lead de Test Drive ──
        print("\n[11] Probando registro de Lead / Test Drive...")
        lead_payload = {
            "customer_phone": CUSTOMER_PHONE,
            "customer_name": "Kevin Cliente",
            "city": "Quito Norte",
            "vehicle_code": chosen_veh["code"],
            "quote_type": "credito",
            "down_payment_offered": chosen_veh["min_down_payment"],
            "term_months": 60,
            "test_drive_requested": True,
            "notes": "Desea probar el vehículo el sábado en la mañana a domicilio"
        }
        res_lead = await client.post("/api/v1/vehicles/lead", json=lead_payload)
        assert res_lead.status_code == 200, f"Error: {res_lead.text}"
        lead_data = res_lead.json()
        print(f"  -> Lead Registrado: {lead_data.get('lead_code')}")
        results.append(("Persistencia Lead / Test Drive (vehicle_leads)", res_lead.status_code == 200))

    print("\n" + "=" * 70)
    print("📊 RESUMEN DE PRUEBAS AUTOMATIZADAS:")
    print("=" * 70)
    all_passed = True
    for name, ok in results:
        status_icon = "✅ PASÓ" if ok else "❌ FALLÓ"
        print(f"  {status_icon} | {name}")
        if not ok:
            all_passed = False
    print("=" * 70)
    if all_passed:
        print("🎉 TODAS LAS PRUEBAS (11/11) FUERON EXITOSAS SIN NINGÚN ERROR.")
    else:
        print("⚠️ ALGUNAS PRUEBAS FALLARON.")

if __name__ == "__main__":
    asyncio.run(test_all_scenarios())
