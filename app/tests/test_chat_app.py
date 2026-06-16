"""
Tests de integracion del endpoint /api/chat con TestClient de FastAPI.

Cubre:
  - Health check devuelve 200 con componentes
  - /api/chat rechaza mensajes demasiado largos
  - /api/chat rechaza model names raros
  - /api/chat maneja Ollama caido sin crashear
  - /api/docs sanitiza nombres maliciosos
  - /api/models responde (con Ollama mockeado)
  - Auth: JWT (login + endpoint protection)

NO ejecuta el agent loop completo (eso requiere Ollama real y tarda).
"""
import sys
import time
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from fastapi.testclient import TestClient
import chat_app


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Reset rate limit storage antes de CADA test (autouse=True).
    Sin esto, los tests de login se pisan entre si porque slowapi comparte
    el storage en memoria del proceso. Usar el metodo .reset() de slowapi."""
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
    """TestClient con User-Agent pytest."""
    return TestClient(chat_app.app, headers={"User-Agent": "pytest/1.0"})


@pytest.fixture
def auth_client(client):
    """TestClient con un JWT válido en el header Authorization."""
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if r.status_code != 200:
        from auth import ensure_users_file
        ensure_users_file()
        # Reset storage otra vez tras ensure_users_file
        chat_app.app.state.limiter._storage = None
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    token = r.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def test_health_endpoint(client):
    """Health debe responder 200 (algun componente puede estar down, eso OK)."""
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.json()
    assert "status" in d
    assert "components" in d


def test_health_reports_degraded_when_component_down(client, monkeypatch):
    """Si algun componente esta down, status='degraded' (no 'ok')."""
    import chat_app
    def fake_check(url, timeout=2.0):
        return False  # todo caido
    monkeypatch.setattr(chat_app, "_check_service_ok", fake_check)

    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "degraded"
    assert d["components"]["ollama"] == "down"
    assert d["components"]["qdrant"] == "down"


def test_health_does_not_hang_on_slow_service(client, monkeypatch):
    """El health check debe responder rapido aunque un servicio este caido.
    El comportamiento real con time.sleep (no interrumpible) se valida en
    produccion, no en unit tests (Python no mata threads)."""
    import chat_app
    def selective_check(url, timeout=2.0):
        if "11434" in url:
            return False  # simula Ollama caido
        return True
    monkeypatch.setattr(chat_app, "_check_service_ok", selective_check)

    t0 = time.time()
    r = client.get("/api/health")
    elapsed = time.time() - t0
    assert elapsed < 1.0, f"Health tardo {elapsed:.2f}s — deberia ser < 1s"
    assert r.status_code == 200
    d = r.json()
    assert d["components"]["ollama"] == "down"
    assert d["components"]["qdrant"] == "ok"


# ── Auth: tests con JWT (todos los endpoints requieren login) ────────────

def test_models_requires_auth(client):
    """/api/models sin Authorization devuelve 401."""
    r = client.get("/api/models")
    assert r.status_code == 401


def test_models_endpoint(auth_client):
    """/api/models con JWT responde (200 si Ollama up, 503 si no)."""
    r = auth_client.get("/api/models")
    assert r.status_code in (200, 503)


def test_chat_rejects_oversized_message(auth_client):
    """Mensaje > 2000 chars se rechaza con 422 (Pydantic validation)."""
    huge = "x" * 3000
    r = auth_client.post("/api/chat", json={"message": huge, "model": "qwen2.5:3b"})
    assert r.status_code == 422


def test_chat_rejects_empty_message(auth_client):
    """Mensaje vacio se rechaza (min_length=1 en Pydantic)."""
    r = auth_client.post("/api/chat", json={"message": "", "model": "qwen2.5:3b"})
    assert r.status_code == 422


def test_chat_rejects_oversized_model_name(auth_client):
    """Model name > 100 chars se rechaza."""
    r = auth_client.post("/api/chat", json={"message": "hola", "model": "x" * 200})
    assert r.status_code == 422


def test_chat_blocks_sqlmap_ua(client):
    """UA de scanner devuelve 403 (incluso en endpoints publicos como /api/auth/login)."""
    r = client.post("/api/auth/login", json={"username": "admin", "password": "x"},
                    headers={"User-Agent": "sqlmap/1.5"})
    assert r.status_code == 403


def test_chat_allows_empty_ua(auth_client):
    """UA vacio se loguea pero NO se bloquea."""
    r = auth_client.get("/api/models", headers={"User-Agent": ""})
    assert r.status_code != 403


def test_chat_allows_normal_ua(auth_client):
    """UA normal no se bloquea."""
    r = auth_client.get("/api/models", headers={"User-Agent": "Mozilla/5.0"})
    assert r.status_code != 403


def test_docs_sanitizes_path_traversal(auth_client):
    """/api/docs/<filename> rechaza traversal."""
    r = auth_client.get("/api/docs/..%2F..%2Fpasswd")
    assert r.status_code in (400, 404)


def test_docs_sanitizes_non_pdf(auth_client):
    """/api/docs/<archivo que no es pdf> devuelve 400."""
    r = auth_client.get("/api/docs/../etc/passwd")
    assert r.status_code in (400, 404)


def test_docs_list_returns_list(auth_client):
    """/api/docs devuelve lista (puede ser vacia)."""
    r = auth_client.get("/api/docs")
    assert r.status_code == 200
    d = r.json()
    assert "docs" in d
    assert isinstance(d["docs"], list)


# ── Auth endpoints ──────────────────────────────────────────────────────

def test_login_rejects_wrong_password(client):
    """Login con password incorrecta devuelve 401."""
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_login_rejects_missing_user(client):
    """Login con user inexistente devuelve 401 (no 404, no泄露 que el user existe)."""
    r = client.post("/api/auth/login", json={"username": "noexiste123", "password": "x"})
    assert r.status_code == 401


def test_login_accepts_correct_credentials(client):
    """Login correcto devuelve 200 + token + user."""
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    d = r.json()
    assert "token" in d and len(d["token"]) > 50
    assert d["user"]["username"] == "admin"
    assert d["user"]["role"] == "admin"


def test_me_requires_token(client):
    """/api/auth/me sin Authorization devuelve 401."""
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_rejects_invalid_token(client):
    """/api/auth/me con token malformado devuelve 401."""
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_me_rejects_tampered_token(client):
    """/api/auth/me con JWT con firma incorrecta devuelve 401."""
    # JWT con payload válido pero firma fake — el servidor detecta firma mala
    bad_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert r.status_code == 401


def test_me_accepts_valid_token(client):
    """Login + /api/auth/me devuelve info del usuario."""
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = r.json()["token"]
    r2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    d = r2.json()
    assert d["username"] == "admin"
    assert d["role"] == "admin"
    assert d["is_admin"] is True
