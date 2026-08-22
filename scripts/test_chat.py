import httpx

def main():
    try:
        import uuid
        r = httpx.post(
            "http://localhost:8080/api/v1/admin/test-chat",
            json={
                "message": "quiero iniciar sesion. mi correo es gbailey@example.net y mi contraseña es |]|{+-",
                "session_id": f"test_fresh_session_{uuid.uuid4()}"
            },
            timeout=30.0
        )
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
