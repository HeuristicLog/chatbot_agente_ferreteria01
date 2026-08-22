import httpx
import uuid

def main():
    session_id = f"test_session_{uuid.uuid4()}"
    
    # 1. Login request
    print(f"--- Sending Login Request (Session: {session_id}) ---")
    payload1 = {
        "message": "quiero iniciar sesion. mi correo es gbailey@example.net y mi contraseña es |]|{+-",
        "session_id": session_id
    }
    r1 = httpx.post("http://localhost:8080/api/v1/admin/test-chat", json=payload1, timeout=120.0)
    print(f"Reply 1: {r1.json().get('reply')}\n")
    
    # 2. Tickets query
    print("--- Sending Tickets Query ---")
    payload2 = {
        "message": "¿cuáles son mis tickets?",
        "session_id": session_id
    }
    r2 = httpx.post("http://localhost:8080/api/v1/admin/test-chat", json=payload2, timeout=120.0)
    print(f"Reply 2: {r2.json().get('reply')}\n")

if __name__ == "__main__":
    main()
