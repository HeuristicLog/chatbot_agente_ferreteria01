import os
import asyncio
import httpx
import json

CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "https://app.chatwoot.com")
ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "193795")
API_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "mMJycxtZ3GBmQhNBS3VaJgXC")

HEADERS = {
    "api_access_token": API_TOKEN,
    "Content-Type": "application/json"
}

KEYWORDS = {
    "construccion": [
        "cemento", "varilla", "adelca", "holcim", "selvalegre", "arena", "ripio", 
        "bloque", "ladrillo", "obra", "hierro", "viga", "malla", "alambre", 
        "estribo", "hormigon", "construccion", "construcción", "titan", "materiales"
    ],
    "herramientas": [
        "herramienta", "herramientas", "taladro", "amoladora", "makita", "dewalt", 
        "stanley", "truper", "bosch", "sierra", "pulidora", "rotomartillo", "disco", 
        "destornillador", "llave", "alicate", "martillo", "inversora", "soldadora"
    ],
    "electricidad": [
        "cable", "cables", "breaker", "tomacorriente", "enchufe", "indeco", "schneider", 
        "electricidad", "electrico", "eléctrico", "foco", "led", "panel", "interruptor", 
        "voltaje", "caja termica", "canaleta", "tubo conduit"
    ],
    "plomeria": [
        "tubo", "tubos", "pvc", "plastigama", "griferia", "grifería", "plomeria", 
        "plomería", "briggs", "codo", "desague", "desagüe", "valvula", "bomba", 
        "tanque", "llave de paso", "fregadero", "inodoro"
    ],
    "pinturas": [
        "pintura", "pinturas", "esmalte", "latex", "látex", "vinilac", "condor", 
        "brocha", "rodillo", "thinner", "sellador", "fondo", "laca", "barniz"
    ],
    "pedido-web": [
        "pedido", "orden", "cast-", "so-", "op-", "carrito", "catalogo", "catálogo", 
        "comprar", "cotizacion", "cotización", "precio", "cuanto cuesta", "cuánto cuesta",
        "factura", "transferencia", "pago", "despacho", "entrega", "cuenta", "local", "entregar"
    ],
    "asesor-humano": [
        "asesor", "asesora", "humano", "agente", "atencion", "atención", "persona", 
        "vendedor", "llamar", "hablar con alguien", "compañera", "ayuda", "favor me ayuda", "buenas"
    ]
}

async def analyze_and_tag_conversations():
    async with httpx.AsyncClient(timeout=25.0) as client:
        print("🔍 Consultando lista de conversaciones en Chatwoot...")
        url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations"
        resp = await client.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print(f"❌ Error al consultar conversaciones: {resp.status_code} {resp.text}")
            return

        conversations = resp.json().get("data", {}).get("payload", [])
        print(f"📊 Total de conversaciones encontradas: {len(conversations)}\n")

        classification_summary = {}

        for conv in conversations:
            conv_id = conv.get("id")
            sender = conv.get("meta", {}).get("sender", {}).get("name", "Desconocido")
            current_labels = conv.get("labels", [])
            
            # Obtener mensajes de la conversación
            msg_url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{conv_id}/messages"
            msg_resp = await client.get(msg_url, headers=HEADERS)
            if msg_resp.status_code != 200:
                print(f"⚠️ Error obteniendo mensajes de Conv #{conv_id}")
                continue

            messages = msg_resp.json().get("payload", [])
            all_text = " ".join([m.get("content", "") for m in messages if m.get("content")]).lower()

            # Detectar etiquetas aplicables
            detected_labels = set(current_labels)

            for category, kw_list in KEYWORDS.items():
                if any(kw in all_text for kw in kw_list):
                    detected_labels.add(category)

            # Si no hubo coincidencia temática específica, clasificar como asesor-humano o pedido-web según contexto
            if not detected_labels:
                if any(k in all_text for k in ["gracias", "hola", "buen", "saludos", "ok"]):
                    detected_labels.add("asesor-humano")
                else:
                    detected_labels.add("pedido-web")

            labels_to_apply = list(detected_labels)

            # Actualizar en Chatwoot
            tag_url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{conv_id}/labels"
            tag_resp = await client.post(tag_url, json={"labels": labels_to_apply}, headers=HEADERS)

            status_icon = "✅" if tag_resp.status_code in [200, 201] else "❌"
            print(f"{status_icon} Conv #{conv_id} | Cliente: {sender} | Etiquetas: {labels_to_apply}")

            for lbl in labels_to_apply:
                classification_summary[lbl] = classification_summary.get(lbl, 0) + 1

        print("\n=======================================================")
        print("📈 RESUMEN DEL ANÁLISIS DE ETIQUETAS EN CHATWOOT:")
        print("=======================================================")
        for lbl, count in sorted(classification_summary.items(), key=lambda x: x[1], reverse=True):
            print(f"🏷️  Etiqueta '{lbl}': {count} conversaciones")
        print("=======================================================")
        print("✨ ¡Métricas de etiquetas actualizadas con éxito en Chatwoot!")

if __name__ == "__main__":
    asyncio.run(analyze_and_tag_conversations())
