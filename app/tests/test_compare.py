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


@pytest.fixture(autouse=True)
def reset_rate_limit():
    try:
        chat_app.app.state.limiter.reset()
    except Exception:
        chat_app.app.state.limiter._storage = None
    yield
    try:
        chat_app.app.state.limiter.reset()
    except Exception:
        pass


@pytest.fixture
def client():
    return TestClient(chat_app.app, headers={"User-Agent": "pytest/1.0"})


@pytest.fixture
def auth_client(client):
    """Client con JWT en el header."""
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if r.status_code != 200:
        from auth import ensure_users_file
        ensure_users_file()
        chat_app.app.state.limiter._storage = None
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    token = r.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def test_compare_requires_auth(client):
    """/api/chat/compare sin Authorization devuelve 401."""
    r = client.post("/api/chat/compare", json={"message": "hola"})
    assert r.status_code == 401


def test_compare_rejects_empty_message(auth_client):
    """Mensaje vacio -> 422 (Pydantic)."""
    r = auth_client.post("/api/chat/compare", json={"message": ""})
    assert r.status_code == 422


def test_compare_rejects_oversized(auth_client):
    """Mensaje > 2000 chars rechazado."""
    r = auth_client.post("/api/chat/compare", json={"message": "x" * 3000})
    assert r.status_code == 422


def test_compare_scanner_blocked(auth_client):
    """UA de scanner bloqueado (incluso con JWT)."""
    r = auth_client.post(
        "/api/chat/compare",
        json={"message": "hola"},
        headers={"User-Agent": "sqlmap/1.5"},
    )
    assert r.status_code == 403
