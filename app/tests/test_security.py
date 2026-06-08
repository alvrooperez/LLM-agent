"""
Test end-to-end de seguridad + agente.

Requiere el server corriendo en :8090. Si no, skip todos.
"""
import socket
import urllib.request
import urllib.error
import json
import time
import pytest

BASE = "http://localhost:8090"
HOST = "localhost"
PORT = 8090

pytestmark = [pytest.mark.e2e]


def server_alive() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((HOST, PORT))
        s.close()
        return True
    except Exception:
        return False


def call(path, headers=None, method="GET", data=None, timeout=10):
    h = {"User-Agent": "sec-test/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:300]


@pytest.mark.skipif(not server_alive(), reason="chat server not running on :8090")
class TestSecurityE2E:
    def test_health_sin_auth(self):
        s, b = call("/api/health")
        assert s == 200

    def test_models_sin_auth_modo_open(self):
        s, b = call("/api/models")
        assert s == 200

    def test_scanner_sqlmap(self):
        s, b = call("/api/models", headers={"User-Agent": "sqlmap/1.5"})
        assert s == 403

    def test_path_traversal(self):
        s, b = call("/api/docs/..%2Fpasswd")
        assert s in (400, 404)

    def test_chat_rejects_oversized(self):
        huge = "x" * 5000
        s, b = call("/api/chat", method="POST", data=json.dumps({"message": huge}).encode(),
                     headers={"Content-Type": "application/json"})
        assert s == 422

    def test_chat_basic_works(self):
        """Sanity: el agente responde un mensaje simple."""
        s, b = call(
            "/api/chat",
            method="POST",
            data=json.dumps({"message": "Dime hola en una palabra", "model": "qwen2.5-rag-ft"}).encode(),
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        assert s == 200
