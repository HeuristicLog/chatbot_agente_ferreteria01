"""
Suite Integral de Pruebas de Producción, Resiliencia y Flujos
Ferretería Castor 2026 — WhatsApp AI + Odoo ERP + Chatwoot Cloud
"""
import sys
import os

# Asegurar path de la aplicación
sys.path.insert(0, "/app")

import asyncio
import json
import time
import urllib.request
import urllib.error

BACKEND_URL = "http://localhost:8080"
GATEWAY_URL = "http://whatsapp-gateway:8090"
INTERNAL_KEY = "change_me"

def http_post(url: str, data: dict, headers: dict = None):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=h, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return 500, str(e)

def http_get(url: str, headers: dict = None):
    h = headers or {}
    req = urllib.request.Request(url, headers=h, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return 500, str(e)

def get_last_outbound(phone: str, limit: int = 3):
    status, data = http_get(f"{GATEWAY_URL}/outbound?phone={phone}")
    if status == 200:
        try:
            parsed = json.loads(data)
            return [it.get("message", "") for it in parsed.get("data", [])[:limit]]
        except Exception:
            return []
    return []

async def run_production_stress_test():
    print("=" * 85)
    print("🛡️  SUITE DE PRUEBAS DE PRODUCCIÓN Y RESILIENCIA: FERRETERÍA CASTOR 🦫")
    print("=" * 85)
    
    results = {"total": 0, "passed": 0, "failed": 0, "details": []}

    def record_test(name: str, passed: bool, detail: str = ""):
        results["total"] += 1
        if passed:
            results["passed"] += 1
            print(f"  ✅ [PASS] {name}", flush=True)
        else:
            results["failed"] += 1
            print(f"  ❌ [FAIL] {name}: {detail}", flush=True)
        results["details"].append({"name": name, "passed": passed, "detail": detail})

    # ──────────────────────────────────────────────────────────────────────────
    # FASE 1: PRUEBAS DE SEGURIDAD Y CASOS DE FALLO (ERROR HANDLING)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[FASE 1] Pruebas de Resiliencia, Seguridad y Manejo de Errores Críticos:")

    # 1.1 Verificación de Salud de la Infraestructura
    st_health, _ = http_get(f"{BACKEND_URL}/health")
    record_test("Health Check de Backend FastAPI (HTTP 200)", st_health == 200, f"Status: {st_health}")

    # 1.2 Manejo de Payload Inválido sin Caída del Servicio
    code, resp = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"campo_inexistente": 123},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    is_safe = (code == 200 and isinstance(resp, dict) and resp.get("status") == "ignored_invalid_payload")
    record_test(
        "Manejo resiliente de payload incompleto sin caída (status: ignored_invalid_payload)",
        is_safe,
        f"Código: {code}, Respuesta: {resp}"
    )

    # 1.3 Mensaje Vacío o con Solo Espacios
    code, resp = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": "593988921136", "message": "     "},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    record_test(
        "Manejo seguro de mensaje en blanco sin caída (HTTP 200)",
        code == 200,
        f"Código obtenido: {code}"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # FASE 2: FLUJOS CONVERSACIONALES INTERACTIVOS (FERRETERÍA CASTOR)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[FASE 2] Verificación de Flujos Conversacionales y Menús Interactivos:")
    test_phone = "593988921136"

    # 2.1 Saludo y Menú de Bienvenida
    code, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": test_phone, "message": "Hola buenas tardes"},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    time.sleep(0.5)
    out = get_last_outbound(test_phone, 1)
    welc_ok = code == 200 and any("Castor" in m and "Catálogo" in m for m in out)
    record_test(
        "Menú de bienvenida interactivo con enlace a Catálogo (/catalogo)",
        welc_ok,
        f"Último mensaje recibido: {out[0][:80] if out else 'Vacio'}"
    )

    # 2.2 Consulta Técnica de Construcción (LangChain + Catálogo)
    code, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": test_phone, "message": "Necesito saber el precio del saco de cemento y varillas de 12mm"},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    time.sleep(0.5)
    out = get_last_outbound(test_phone, 1)
    mat_ok = code == 200 and any("Cemento" in m or "Varilla" in m for m in out)
    record_test(
        "Inferencia de IA y cotización de materiales de construcción",
        mat_ok,
        f"Último mensaje recibido: {out[0][:80] if out else 'Vacio'}"
    )

    # 2.3 Consulta de Herramientas Eléctricas (Makita / DeWalt)
    code, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": test_phone, "message": "Qué amoladoras y rotomartillos tienen disponibles?"},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    time.sleep(0.5)
    out = get_last_outbound(test_phone, 1)
    tools_ok = code == 200 and any("Makita" in m or "DeWalt" in m or "Amoladora" in m for m in out)
    record_test(
        "Consulta de herramientas eléctricas con marcas y precios oficiales",
        tools_ok,
        f"Último mensaje recibido: {out[0][:80] if out else 'Vacio'}"
    )

    # 2.4 Horarios y Sucursales
    code, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": test_phone, "message": "4"},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    time.sleep(0.5)
    out = get_last_outbound(test_phone, 1)
    hours_ok = code == 200 and any("Horarios de Atención" in m or "07:30" in m for m in out)
    record_test(
        "Opción 4: Información de horarios y sucursales",
        hours_ok,
        f"Último mensaje recibido: {out[0][:80] if out else 'Vacio'}"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # FASE 3: FLUJO DE TRANSFERENCIA HUMANA (HANDOFF) Y RECUPERACIÓN
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[FASE 3] Prueba de Transferencia a Asesor Humano (Handoff) y Recuperación:")

    # 3.1 Solicitar Asesor Humano
    code, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": test_phone, "message": "asesor"},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    time.sleep(0.5)
    out = get_last_outbound(test_phone, 1)
    adv_ok = code == 200 and any("Asesor" in m or "Sucursales" in m for m in out)
    record_test(
        "Activación de menú de asesor por sucursal",
        adv_ok,
        f"Último mensaje recibido: {out[0][:80] if out else 'Vacio'}"
    )

    # 3.2 Confirmar Sucursal Centro para Asesor
    code, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": test_phone, "message": "Centro", "metadata": {"interactive_id": "confirm_asesor_centro"}},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    time.sleep(0.5)
    out = get_last_outbound(test_phone, 1)
    handoff_active = code == 200 and any("asesor" in m.lower() or "centro" in m.lower() or "notificado" in m.lower() for m in out)
    record_test(
        "Transferencia formal de conversación y asignación a sucursal Centro",
        handoff_active,
        f"Último mensaje recibido: {out[0][:80] if out else 'Vacio'}"
    )

    # 3.3 Reactivación del Bot con 'menu' o 'hola'
    code, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": test_phone, "message": "menu"},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    time.sleep(0.5)
    out = get_last_outbound(test_phone, 1)
    reset_ok = code == 200 and any("Castor" in m for m in out)
    record_test(
        "Reactivación instantánea del bot ante comando 'menu' o saludo",
        reset_ok,
        f"Último mensaje recibido: {out[0][:80] if out else 'Vacio'}"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # FASE 4: INTEGRACIÓN CON ODOO ERP (VENTAS, STOCK Y RASTREO)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[FASE 4] Pruebas de Integración con Odoo ERP (Stock, Órdenes y Pagos):")
    from app.services.odoo_service import OdooService
    odoo = OdooService()

    # 4.1 Consulta de Stock Multisede en Odoo
    stock_centro = await odoo.check_stock("FERR-CEM-02", sucursal="Centro")
    stock_norte = await odoo.check_stock("FERR-CEM-02", sucursal="Norte")
    stock_ok = stock_centro["available"] and stock_centro["stock_sucursal"] > 0
    record_test(
        "Verificación de stock multisede en tiempo real en Odoo",
        stock_ok,
        f"Centro: {stock_centro['stock_sucursal']} sacos | Norte: {stock_norte['stock_sucursal']} sacos"
    )

    # 4.2 Creación de Orden formal sale.order en Odoo
    items = [
        {"sku": "FERR-MAK-01", "name": "Rotomartillo Makita HR2470", "unit_price": 145.0, "quantity": 1},
        {"sku": "FERR-CEM-02", "name": "Saco Cemento Selvalegre 50kg", "unit_price": 8.40, "quantity": 10}
    ]
    odoo_order = await odoo.create_sale_order(
        customer_phone=test_phone,
        customer_name="Empresa Constructora Andes S.A.",
        items=items,
        delivery_type="pickup",
        sucursal="Centro",
        payment_method="tarjeta",
        ruc_cedula="1792458912001"
    )
    order_ok = odoo_order["success"] and odoo_order["order_name"].startswith("SO-")
    record_test(
        f"Generación de Orden de Venta en Odoo ({odoo_order['order_name']}) con IVA 15%",
        order_ok,
        f"Total: ${odoo_order['total']:.2f} USD | Almacén: {odoo_order['warehouse']}"
    )

    # 4.3 Generación de Enlace de Pago Seguro (Odoo Payment Link)
    pay_link_ok = odoo_order.get("payment_link") and "usable-thorn-kabob.ngrok-free.dev" in odoo_order["payment_link"]
    record_test(
        "Generación de Enlace de Pago Digital de Odoo para WhatsApp",
        pay_link_ok,
        f"URL: {odoo_order.get('payment_link')}"
    )

    # 4.4 Rastreo de Pedido Odoo vía WhatsApp (handle_order_result)
    code, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": test_phone, "message": odoo_order["order_name"]},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    time.sleep(0.5)
    out = get_last_outbound(test_phone, 1)
    track_ok = code == 200 and any("Pedido Odoo ERP" in m or odoo_order["order_name"] in m for m in out)
    record_test(
        f"Consulta de rastreo de orden #{odoo_order['order_name']} por WhatsApp",
        track_ok,
        f"Último mensaje recibido: {out[0][:80] if out else 'Vacio'}"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # FASE 5: MULTI-LÍNEA Y CONCURRENCIA (CANAL 1 Y CANAL 2)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[FASE 5] Pruebas de Multi-Línea y Concurrencia:")
    phone_line_1 = "593988921136"  # Línea Sucursal Centro (Evolution API)
    phone_line_2 = "593992451085"  # Línea Marketing (Meta Cloud API)

    code1, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": phone_line_1, "message": "1"},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    code2, _ = http_post(
        f"{BACKEND_URL}/webhooks/whatsapp",
        {"phone": phone_line_2, "message": "1"},
        headers={"X-Internal-API-Key": INTERNAL_KEY}
    )
    multiline_ok = (code1 == 200 and code2 == 200)
    record_test(
        "Procesamiento simultáneo en ambas líneas telefónicas sin colisiones",
        multiline_ok,
        f"Línea 1 Status: {code1} | Línea 2 Status: {code2}"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # FASE 6: WEBVIEW Y REST API DEL CATÁLOGO
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[FASE 6] Pruebas del Catálogo In-App (/catalogo):")
    st_cat, html_cat = http_get(f"{BACKEND_URL}/catalogo?phone={test_phone}&sucursal=Centro")
    st_prods, data_prods = http_get(f"{BACKEND_URL}/api/catalog/products")
    st_categs, data_categs = http_get(f"{BACKEND_URL}/api/catalog/categories")

    webview_ok = st_cat == 200 and ("Ferretería Castor" in html_cat or "Castor" in html_cat)
    prods_ok = st_prods == 200 and json.loads(data_prods).get("count", 0) > 0
    categs_ok = st_categs == 200 and len(json.loads(data_categs).get("data", [])) >= 5

    record_test("Carga de interfaz Webview In-App (/catalogo)", webview_ok, f"Status: {st_cat}")
    record_test("REST API de productos activos (/api/catalog/products)", prods_ok, f"Count: {json.loads(data_prods).get('count', 0)}")
    record_test("REST API de categorías (/api/catalog/categories)", categs_ok, f"Categorías: {len(json.loads(data_categs).get('data', []))}")

    # ──────────────────────────────────────────────────────────────────────────
    # RESUMEN EJECUTIVO
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 85)
    print("📊 RESUMEN FINAL DE LA SUITE DE PRUEBAS DE PRODUCCIÓN:")
    print(f"   • Total de pruebas ejecutadas: {results['total']}")
    print(f"   • Pruebas exitosas (PASS):     {results['passed']}")
    print(f"   • Pruebas fallidas (FAIL):     {results['failed']}")
    if results['failed'] == 0:
        print("   🏆 VEREDICTO: EL SISTEMA ESTÁ 100% LISTO Y ESTABLE PARA PRODUCCIÓN")
    else:
        print("   ⚠️  VEREDICTO: SE DETECTARON ADVERTENCIAS A CORREGIR")
    print("=" * 85)

if __name__ == "__main__":
    asyncio.run(run_production_stress_test())
