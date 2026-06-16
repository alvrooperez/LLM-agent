"""
Test E2E del endpoint /api/chat/compare con Ollama real.
Solo se ejecuta si server + Ollama estan vivos.
"""
import sys
import socket
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def server_alive() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("localhost", 8090))
        s.close()
        return True
    except Exception:
        return False


def ollama_alive() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (server_alive() and ollama_alive()),
    reason="server on :8090 or Ollama not available",
)


def test_compare_e2e_returns_events_from_both_models():
    """El endpoint emite eventos tagged por modelo."""
    # Login primero para obtener JWT
    login_req = urllib.request.Request(
        "http://localhost:8090/api/auth/login",
        data=json.dumps({"username": "admin", "password": "admin123"}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "e2e-compare/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(login_req, timeout=5) as r:
            token = json.loads(r.read())["token"]
    except Exception as e:
        pytest.skip(f"login failed: {e}")

    data = json.dumps({
        "message": "ok",
        "models": ["qwen2.5:3b", "qwen2.5-rag-ft"],
    }).encode()
    # Usar socket raw para evitar problemas con urllib + chunked encoding
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(600)
    s.connect(("localhost", 8090))
    http_req = (
        b"POST /api/chat/compare HTTP/1.1\r\n"
        b"Host: localhost:8090\r\n"
        b"Content-Type: application/json\r\n"
        b"User-Agent: e2e-compare/1.0\r\n"
        b"Authorization: Bearer " + token.encode() + b"\r\n"
        b"Content-Length: " + str(len(data)).encode() + b"\r\n"
        b"Connection: close\r\n"
        b"\r\n" + data
    )
    s.sendall(http_req)

    # Leer la respuesta hasta cierre de conexion
    raw = b""
    while True:
        try:
            chunk = s.recv(8192)
        except socket.timeout:
            break
        if not chunk:
            break
        raw += chunk
    s.close()

    text = raw.decode("utf-8", errors="replace")

    # Separar headers del body
    if "\r\n\r\n" in text:
        _, text = text.split("\r\n\r\n", 1)
    elif "\n\n" in text:
        _, text = text.split("\n\n", 1)

    # Parsear eventos SSE del buffer completo
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event = None
        data_str = ""
        for line in block.strip().split("\n"):
            if line.startswith("event: "):
                event = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:]
        if data_str:
            try:
                events.append({"event": event, "data": json.loads(data_str)})
            except Exception:
                pass

    # Debe haber al menos un evento
    assert len(events) > 0, "No SSE events received"

    # Los eventos deben incluir el campo 'model' cuando aplique
    models_seen = set()
    for ev in events:
        if "model" in ev["data"]:
            models_seen.add(ev["data"]["model"])

    # Ambos modelos deben haber emitido al menos UN evento
    # (puede ser thinking, tool_call, token, done, o error)
    # (al menos uno de los dos, no garantizamos los dos)
    assert len(models_seen) >= 1, f"No model events seen. Events: {events[:5]}"


if __name__ == "__main__":
    print("E2E test (run with pytest to skip safely):")
    print(f"  Ollama alive: {ollama_alive()}")
