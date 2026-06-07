"""
Tests del endpoint /api/chat/compare.
Solo verifica la forma de la respuesta, no ejecuta Ollama real.
"""
import sys
import json
import pytest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from fastapi.testclient import TestClient
import chat_app


@pytest.fixture
def client():
    chat_app.app.state.limiter._storage = None
    return TestClient(chat_app.app, headers={"User-Agent": "pytest/1.0"})


def test_compare_endpoint_exists(client):
    """/api/chat/compare existe y rechaza input invalido."""
    # Mensaje vacio
    r = client.post("/api/chat/compare", json={"message": ""})
    assert r.status_code == 422


def test_compare_rejects_oversized(client):
    """Mensaje > 2000 chars rechazado."""
    r = client.post("/api/chat/compare", json={"message": "x" * 3000})
    assert r.status_code == 422


def test_compare_auth_required_when_enabled(client, monkeypatch):
    """Si CHAT_API_KEY activo, requiere header."""
    monkeypatch.setattr(chat_app, "CHAT_API_KEY", "secret-123")
    r = client.post("/api/chat/compare", json={"message": "hola"})
    assert r.status_code == 401


def test_compare_scanner_blocked(client):
    """UA de scanner bloqueado."""
    r = client.post(
        "/api/chat/compare",
        json={"message": "hola"},
        headers={"User-Agent": "sqlmap/1.5"},
    )
    assert r.status_code == 403
