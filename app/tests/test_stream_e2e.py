"""
Test E2E del endpoint /api/chat/stream con Ollama real.
Solo se ejecuta si el server esta vivo.
"""
import socket
import json
import time
import urllib.request
import urllib.error
import pytest

HOST = "localhost"
PORT = 8090

pytestmark = pytest.mark.e2e


def server_alive() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((HOST, PORT))
        s.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not server_alive(), reason="chat server not running on :8090")
def test_stream_endpoint_emits_tokens():
    """El endpoint /api/chat/stream emite eventos SSE de Ollama."""
    data = json.dumps({
        "message": "ok",
        "model": "qwen2.5-rag-ft",
    }).encode()
    req = urllib.request.Request(
        f"http://{HOST}:{PORT}/api/chat/stream",
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "stream-test/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        assert r.status == 200
        assert r.headers.get("Content-Type", "").startswith("text/event-stream")
        # Leer chunks hasta cierre
        body = b""
        while True:
            chunk = r.read(4096)
            if not chunk:
                break
            body += chunk
    text = body.decode("utf-8", errors="replace")

    # Debe tener al menos un evento
    assert "event:" in text, f"No SSE events in response: {text[:200]}"
