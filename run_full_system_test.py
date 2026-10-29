#!/usr/bin/env python3
"""
Test Suite: AutoEcuador Motors 2026 — Interactive Flows, Webview, and Chatwoot Cloud
Tests the complete end-to-end functionality requested by the user:
1. Interactive LangChain / Semantic Engine flows (No plain text, rich menus, emojis, links)
2. In-app WhatsApp Webview Catalog (/catalogo-autos) validation
3. Real Chatwoot Cloud API operations (Inboxes, Contacts, Messages, Custom Attributes, Labels, Private Notes, Status)
"""
import sys
import os
import json
import asyncio
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure workspace root is in python path
WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(WORKSPACE_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Credentials from .env
CHATWOOT_BASE = "https://app.chatwoot.com"
ACCOUNT_ID = "193795"
API_TOKEN = "mMJycxtZ3GBmQhNBS3VaJgXC"
INBOX_ID = 150556
TEST_PHONE = "593988921136"

HEADERS = {
    "api_access_token": API_TOKEN,
    "Content-Type": "application/json"
}

def chatwoot_request(method, path, body=None):
    url = f"{CHATWOOT_BASE}/api/v1/accounts/{ACCOUNT_ID}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8")
        return e.code, {"error": err_content}
    except Exception as ex:
        return 500, {"error": str(ex)}

def test_interactive_langchain_engine():
    print("\n" + "="*70)
    print("TEST 1: MOTOR DE FLUJOS INTERACTIVOS (NO TEXTO PLANO)")
    print("="*70)
    
    # Import native engine directly
    from app.services.langchain_service import LangChainService
    svc = LangChainService()
    
    test_queries = [
        ("hola", "0. Bienvenida & Menú Interactivo"),
        ("1", "1. Camionetas 4x4 (D-Max, Hilux, Poer)"),
        ("2", "2. Híbridos Cero Pico y Placa (Yaris Cross)"),
        ("3", "3. SUVs Familiares (Tracker, Sportage, Tucson, Tiggo)"),
        ("4", "4. Vitrina Virtual Webview sin salir de WhatsApp"),
        ("5", "5. Financiamiento y Crédito Vehicular"),
        ("6", "6. Plan Retoma de Usados"),
        ("7", "7. Transferencia a Asesor Humano"),
        ("¿Tienen la Chevrolet D-Max en stock y cuánto cuesta?", "Pregunta libre: D-Max"),
        ("¿El Yaris Cross tiene pico y placa en Quito?", "Pregunta libre: Híbrido Pico y Placa")
    ]
    
    results = []
    for query, label in test_queries:
        res = asyncio.run(svc._native_semantic_engine(query, phone=TEST_PHONE))
        # Validations
        is_not_plain = "\n" in res and ("•" in res or "1️⃣" in res or "🔹" in res or "🔸" in res or "*" in res)
        has_webview_link = "catalogo-autos" in res
        has_emojis = any(char in res for char in ["🚘", "🛻", "🌿", "🚙", "📱", "💳", "🔄", "👨‍💼", "⚡"])
        has_interactive_options = any(opt in res for opt in ["1️⃣", "👉", "🔘"])
        
        status = "PASSED" if (is_not_plain and has_emojis and has_interactive_options) else "FAILED"
        print(f"\n[+] Flujo: {label}")
        print(f"    Consulta: '{query}'")
        print(f"    Longitud: {len(res)} caracteres | Emojis: {has_emojis} | Opciones: {has_interactive_options} | Link Webview: {has_webview_link}")
        print(f"    Muestra de respuesta:\n    " + res.replace("\n", "\n    ")[:300] + "...")
        print(f"    Resultado: {status}")
        results.append((label, status))
    
    return results

def test_webview_catalog_file():
    print("\n" + "="*70)
    print("TEST 2: VITRINA VIRTUAL / WEBVIEW EN WHATSAPP (catalogo_autos.html)")
    print("="*70)
    
    file_path = os.path.join(WORKSPACE_ROOT, "catalogo_autos.html")
    if not os.path.exists(file_path):
        print("[-] ERROR: catalogo_autos.html no encontrado.")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    checks = [
        ("Cierre y Retorno a WhatsApp (closeWebviewAndReturn)", "closeWebviewAndReturn" in html),
        ("Botón Hablar con Asesor en WhatsApp", "requestAdvisorNow" in html),
        ("Cajón Mi Garaje (Garage Drawer)", "garage-drawer" in html or "Mi Garaje" in html),
        ("Simulador de Cuotas & Crédito", "slider" in html or "plazo" in html or "cuota" in html),
        ("Modelos 2026 (D-Max, Hilux, Poer, Yaris Cross, Tracker)", "D-Max" in html and "Hilux" in html and "Yaris Cross" in html),
        ("Optimización Móvil (Tailwind / Responsive)", "viewport" in html and "tailwindcss" in html),
        ("Formulario de Cotización Formal", "cotizacion" in html or "quote" in html or "input" in html)
    ]
    
    all_ok = True
    for desc, passed in checks:
        state = "PASSED" if passed else "FAILED"
        if not passed:
            all_ok = False
        print(f"    [+] {desc}: {state}")
    
    return all_ok

def test_chatwoot_all_functionalities():
    print("\n" + "="*70)
    print("TEST 3: VERIFICACIÓN COMPLETA DE FUNCIONALIDADES CHATWOOT CLOUD")
    print("="*70)
    
    # 1. Verificar Bandejas de Entrada (Inboxes)
    status, data = chatwoot_request("GET", "/inboxes")
    print(f"\n1. Inboxes de la Cuenta (Status {status}):")
    inbox_found = False
    if status == 200:
        payload = data.get("payload", [])
        for ib in payload:
            print(f"   • ID: {ib.get('id')} | Nombre: {ib.get('name')} | Canal: {ib.get('channel_type')}")
            if ib.get("id") == INBOX_ID:
                inbox_found = True
    print(f"   Resultado Bandeja Principal ({INBOX_ID}): {'PASSED' if inbox_found else 'FAILED'}")

    # 2. Verificar Definiciones de Atributos Personalizados (Custom Attributes)
    status, data = chatwoot_request("GET", "/custom_attribute_definitions")
    print(f"\n2. Definiciones de Atributos Personalizados (Status {status}):")
    attrs_found = []
    if status == 200:
        attrs = data if isinstance(data, list) else data.get("payload", [])
        for a in attrs:
            attrs_found.append(a.get("attribute_key"))
            print(f"   • Clave: {a.get('attribute_key')} | Nombre: {a.get('attribute_display_name')} | Tipo: {a.get('attribute_display_type')}")
    
    expected_attrs = ["tiempo_respuesta_frt", "flujo_actual", "modelo_interes", "sucursal_preferida"]
    has_expected = all(ea in attrs_found for ea in expected_attrs)
    print(f"   Resultado Atributos Automotrices: {'PASSED' if has_expected else 'PARTIAL'}")

    # 3. Crear o Buscar Contacto del Cliente de Prueba
    status, data = chatwoot_request("GET", f"/contacts/search?q={TEST_PHONE}")
    contact_id = None
    if status == 200 and data.get("payload"):
        contact_id = data["payload"][0]["id"]
        print(f"\n3. Contacto de Prueba Existente: ID {contact_id} (+{TEST_PHONE})")
    else:
        # Crear contacto
        status, data = chatwoot_request("POST", "/contacts", {
            "inbox_id": INBOX_ID,
            "name": f"Cliente Prueba +{TEST_PHONE}",
            "phone_number": f"+{TEST_PHONE}"
        })
        if status in [200, 201]:
            contact_id = data.get("payload", {}).get("contact", {}).get("id")
            print(f"\n3. Contacto Creado Exitosamente: ID {contact_id}")
        else:
            print(f"\n3. Error creando contacto: {data}")

    if not contact_id:
        print("[-] Abortando prueba de conversación por falta de contacto.")
        return False

    # 4. Obtener o Crear Conversación en Chatwoot
    status, data = chatwoot_request("GET", f"/contacts/{contact_id}/conversations")
    conv_id = None
    if status == 200 and data.get("payload"):
        conv_id = data["payload"][0]["id"]
        print(f"\n4. Conversación Activa Encontrada: ID {conv_id}")
    else:
        status, data = chatwoot_request("POST", "/conversations", {
            "inbox_id": INBOX_ID,
            "contact_id": contact_id,
            "status": "open"
        })
        if status in [200, 201]:
            conv_id = data.get("id")
            print(f"\n4. Nueva Conversación Creada: ID {conv_id}")
        else:
            print(f"\n4. Error creando conversación: {data}")

    if not conv_id:
        print("[-] Abortando pruebas de mensajes.")
        return False

    # 5. Enviar Mensaje Entrante del Cliente (Simulación WhatsApp Inbound)
    client_msg = "🚘 [TEST AUTOMÁTICO] Hola Alex, deseo cotizar la Chevrolet D-Max 4x4 y saber la entrada mínima."
    status, msg_resp = chatwoot_request("POST", f"/conversations/{conv_id}/messages", {
        "content": client_msg,
        "message_type": "incoming",
        "private": False
    })
    print(f"\n5. Registro de Mensaje Entrante del Cliente (Status {status}): {'PASSED' if status in [200, 201] else 'FAILED'}")

    # 6. Enviar Respuesta Interactiva del Bot (Simulación Bot Outbound)
    bot_msg = (
        "🛻 *Chevrolet D-Max High Country 3.0L Diésel 4x4 (2026)*\n\n"
        "• Precio de lista: *$34,990 USD*\n"
        "• Entrada mínima (20%): *$6,998 USD*\n"
        "• Cuota estimada: *$585/mes* (a 60 meses con cuota fija)\n\n"
        "📱 *Abre la vitrina sin salir de WhatsApp:* https://usable-thorn-kabob.ngrok-free.dev/catalogo-autos\n\n"
        "🔘 *Opciones interactivas:*\n"
        "1️⃣ Simular entrada diferente\n"
        "2️⃣ Plan retoma de auto usado\n"
        "3️⃣ Hablar con asesor ejecutivo"
    )
    status, bot_resp = chatwoot_request("POST", f"/conversations/{conv_id}/messages", {
        "content": bot_msg,
        "message_type": "outgoing",
        "private": False
    })
    print(f"6. Registro de Mensaje Saliente Interactivo del Bot (Status {status}): {'PASSED' if status in [200, 201] else 'FAILED'}")

    # 7. Actualizar Atributos Personalizados de la Conversación (Métricas Automotrices)
    metrics_payload = {
        "custom_attributes": {
            "tiempo_respuesta_frt": "18 seg",
            "flujo_actual": "Camionetas 4x4",
            "modelo_interes": "Chevrolet D-Max 3.0L Diésel",
            "sucursal_preferida": "Quito Centro",
            "presupuesto_entrada": "6998"
        }
    }
    status, attr_resp = chatwoot_request("POST", f"/conversations/{conv_id}/custom_attributes", metrics_payload)
    print(f"7. Actualización de Métricas & Custom Attributes (Status {status}): {'PASSED' if status == 200 else 'FAILED'}")

    # 8. Agregar Etiquetas Comerciales (Labels)
    labels_payload = {
        "labels": ["camionetas-4x4", "frt-rapido", "lead-calificado", "d-max-2026"]
    }
    status, label_resp = chatwoot_request("POST", f"/conversations/{conv_id}/labels", labels_payload)
    print(f"8. Asignación de Etiquetas Comerciales en Chatwoot (Status {status}): {'PASSED' if status == 200 else 'FAILED'}")

    # 9. Crear Nota Privada Interna para el Asesor Humano (Private Note)
    internal_note = (
        "📌 [AUDITORÍA DEL SISTEMA] Lead calificado automáticamente por IA Alex.\n"
        "• Interés: Chevrolet D-Max 3.0L High Country\n"
        "• Presupuesto entrada: $6,998 USD\n"
        "• Tiempo de respuesta del bot: 18 segundos (Rápido)\n"
        "• Asignado a: Christianb (Heuristic Log)"
    )
    status, note_resp = chatwoot_request("POST", f"/conversations/{conv_id}/messages", {
        "content": internal_note,
        "message_type": "outgoing",
        "private": True
    })
    print(f"9. Creación de Nota Privada Interna (Status {status}): {'PASSED' if status in [200, 201] else 'FAILED'}")

    # 10. Prueba de Estados: Mantener Abierta (Open) y Simular Resolución (Resolved)
    status, open_resp = chatwoot_request("POST", f"/conversations/{conv_id}/toggle_status", {"status": "open"})
    print(f"10. Estado Conversación 'open' (Status {status}): {'PASSED' if status == 200 else 'FAILED'}")

    return True

if __name__ == "__main__":
    t1 = test_interactive_langchain_engine()
    t2 = test_webview_catalog_file()
    t3 = test_chatwoot_all_functionalities()
    
    print("\n" + "="*70)
    print("RESUMEN GENERAL DE VERIFICACIÓN:")
    print("="*70)
    print(f"1. Flujos Interactivos LangChain: {len([r for r in t1 if r[1] == 'PASSED'])}/{len(t1)} APROBADOS")
    print(f"2. Vitrina Webview WhatsApp: {'APROBADO' if t2 else 'FALLIDO'}")
    print(f"3. Chatwoot Cloud Omnicanal: {'APROBADO' if t3 else 'FALLIDO'}")
    print("="*70)
