import httpx
import sys
import json

def test_conversation(message: str, phone: str = "593999999999"):
    url = "http://localhost:8080/test/messages"
    headers = {
        "Content-Type": "application/json",
        "X-Internal-API-Key": "change_me"
    }
    payload = {
        "phone": phone,
        "message": message
    }
    
    print(f"Enviando mensaje: '{message}' desde teléfono: {phone}")
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=35.0)
        if response.status_code == 200:
            data = response.json()
            print("\n--- RESPUESTA DE CASTOR ---")
            print(data.get("reply"))
            print("---------------------------\n")
            print(f"Duración: {data.get('duration_ms')} ms")
            print(f"ID de Sesión: {data.get('session_id')}")
        else:
            print(f"Fallo en la petición: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error conectando con chatbot-api: {str(e)}")

if __name__ == "__main__":
    msg = "Quiero consultar el ticket 12"
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    test_conversation(msg)
