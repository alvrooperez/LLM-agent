"""
Test del AbortController: cliente cancela la request a mitad del stream.
El backend (FastAPI) debe cerrar la conexion limpiamente.
"""
import urllib.request, json, socket, time, threading

HOST = "localhost"
PORT = 8090

# Iniciar una request lenta
data = json.dumps({'message': 'Busca en los docs cómo configurar RAG con vectores y dame el estado de la GPU y lista los modelos', 'model': 'qwen2.5-rag-ft'}).encode()

print("Starting streaming request...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(30)
s.connect((HOST, PORT))

req = (
    b"POST /api/chat/stream HTTP/1.1\r\n"
    b"Host: localhost:8090\r\n"
    b"Content-Type: application/json\r\n"
    b"User-Agent: abort-test/1.0\r\n"
    b"Content-Length: " + str(len(data)).encode() + b"\r\n"
    b"\r\n" + data
)
s.send(req)
print("Request sent, reading first chunk...")

buf = b""
s.settimeout(2)
try:
    chunk = s.recv(4096)
    if chunk:
        buf += chunk
        print(f"Got {len(chunk)} bytes")
        # Mostrar las primeras lineas
        first_lines = chunk.decode('utf-8', errors='replace').split('\n')[:5]
        for line in first_lines:
            print(f"  {line[:100]}")
except socket.timeout:
    print("Initial recv timeout (server still processing)")

# Esperar un poco y luego abortar
print("\nWaiting 3s then aborting...")
time.sleep(3)

print("Closing socket (simulates client abort)...")
s.close()

# Dar tiempo al server para que limpie
time.sleep(2)

# Verificar que el server sigue respondiendo a otras requests
print("\nVerifying server still healthy...")
s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s2.settimeout(3)
s2.connect((HOST, PORT))
s2.send(b"GET /api/health HTTP/1.1\r\nHost: localhost\r\nUser-Agent: abort-test/1.0\r\n\r\n")
try:
    resp = s2.recv(4096).decode('utf-8', errors='replace')
    status_line = resp.split('\r\n')[0]
    print(f"  {status_line}")
    print("  OK: server recovered from abort")
except Exception as e:
    print(f"  ERR: {e}")
s2.close()
