import time
import socket
import sys

def wait_for_port(host: str, port: int, service_name: str, timeout: int = 60):
    start_time = time.time()
    print(f"Waiting for {service_name} at {host}:{port}...")
    while True:
        try:
            with socket.create_connection((host, port), timeout=2.0):
                print(f"{service_name} is ready!")
                return True
        except (socket.timeout, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                print(f"Timeout waiting for {service_name} after {timeout} seconds.")
                sys.exit(1)
            time.sleep(2.0)

if __name__ == "__main__":
    # Wait for PostgreSQL (postgres:5432)
    wait_for_port("postgres", 5432, "PostgreSQL")
    # Wait for Redis (redis:6379)
    wait_for_port("redis", 6379, "Redis")
    # Wait for Qdrant (qdrant:6333)
    wait_for_port("qdrant", 6333, "Qdrant")
