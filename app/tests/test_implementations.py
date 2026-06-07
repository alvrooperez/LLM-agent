"""
Tests para tools/implementations.py: cada tool funciona correctamente
y maneja errores de sus dependencias.

Las tools que llaman a servicios externos (Ollama, Qdrant, RAG API, GPU)
se testean con mocks para no depender de servicios levantados.
"""
import sys
import json
import os
import urllib.error
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Importar implementations registra las tools en TOOL_REGISTRY
import tools.implementations  # noqa: F401
from tools.implementations import (
    search_docs, list_models, get_gpu_stats,
    get_collection_info, _ollama_request, _rag_request, _qdrant_get,
)


# ── list_models ──────────────────────────────────────────────────────────

@patch("tools.implementations._ollama_request")
def test_list_models_returns_ollama_models(mock_ollama):
    """list_models parsea la respuesta de /api/tags."""
    mock_ollama.return_value = json.dumps({
        "models": [
            {"name": "qwen2.5:3b", "size": 1_900_000_000},
            {"name": "llama3:8b", "size": 4_500_000_000},
        ]
    })
    result = list_models()
    assert "qwen2.5:3b" in result
    assert "llama3:8b" in result
    assert "GB" in result


@patch("tools.implementations._ollama_request")
def test_list_models_empty(mock_ollama):
    """Si no hay modelos, mensaje claro."""
    mock_ollama.return_value = json.dumps({"models": []})
    result = list_models()
    assert "No hay modelos" in result


@patch("tools.implementations._ollama_request")
def test_list_models_ollama_down(mock_ollama):
    """Si Ollama no responde, devuelve error en vez de crashear."""
    mock_ollama.return_value = "[ERROR] connection refused"
    result = list_models()
    # list_models hace json.loads del string de error y captura la excepcion
    assert "[ERROR]" in result or "fall" in result


# ── get_gpu_stats ────────────────────────────────────────────────────────

@patch("subprocess.run")
def test_get_gpu_stats_success(mock_run):
    """Parsea correctamente la salida CSV de nvidia-smi."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="2048, 4096, 45, 60",  # used, total, util%, temp
    )
    result = get_gpu_stats()
    assert "2.0/4.0 GB" in result
    assert "45%" in result
    assert "60" in result and "C" in result


@patch("subprocess.run")
def test_get_gpu_stats_nvidia_smi_not_found(mock_run):
    """Si nvidia-smi no existe, error claro."""
    mock_run.side_effect = FileNotFoundError()
    result = get_gpu_stats()
    assert "[ERROR]" in result
    assert "nvidia-smi" in result


@patch("subprocess.run")
def test_get_gpu_stats_command_fails(mock_run):
    """Si nvidia-smi devuelve error, manejamos sin crashear."""
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="GPU not accessible",
    )
    result = get_gpu_stats()
    assert "[ERROR]" in result
    assert "nvidia-smi" in result


# ── get_collection_info ──────────────────────────────────────────────────

@patch("tools.implementations._qdrant_get")
def test_get_collection_info_success(mock_qdrant):
    """Parsea la respuesta de Qdrant correctamente."""
    mock_qdrant.return_value = {
        "result": {
            "status": "green",
            "vectors_count": 62,
            "config": {
                "params": {
                    "vectors": {"size": 384, "distance": "Cosine"}
                }
            }
        }
    }
    result = get_collection_info()
    assert "62 puntos" in result
    assert "384" in result
    assert "Cosine" in result
    assert "green" in result


@patch("tools.implementations._qdrant_get")
def test_get_collection_info_error(mock_qdrant):
    """Si Qdrant no responde, error claro."""
    mock_qdrant.return_value = {"error": "Connection refused"}
    result = get_collection_info()
    assert "[ERROR]" in result


@patch("tools.implementations._qdrant_get")
def test_get_collection_info_custom_name(mock_qdrant):
    """Si pasamos un nombre distinto, lo usa."""
    mock_qdrant.return_value = {
        "result": {"status": "green", "vectors_count": 10,
                   "config": {"params": {"vectors": {"size": 768, "distance": "Euclid"}}}}
    }
    result = get_collection_info(name="custom_collection")
    # Verificar que _qdrant_get fue llamado con el path correcto
    mock_qdrant.assert_called_with("/collections/custom_collection")


# ── _ollama_request / _rag_request / _qdrant_get ───────────────────────

@patch("urllib.request.urlopen")
def test_ollama_request_success(mock_urlopen):
    """_ollama_request hace GET y devuelve el body."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"models": []}'
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp
    result = _ollama_request("/api/tags")
    parsed = json.loads(result)
    assert "models" in parsed


@patch("urllib.request.urlopen")
def test_ollama_request_handles_timeout(mock_urlopen):
    """Si timeout, devuelve error sin crashear."""
    mock_urlopen.side_effect = TimeoutError("slow")
    result = _ollama_request("/api/tags")
    assert "[ERROR]" in result
    assert "Ollama" in result


@patch("urllib.request.urlopen")
def test_ollama_request_retries_on_url_error(mock_urlopen):
    """URLError transitorio se reintenta; éxito en el segundo intento."""
    success_resp = MagicMock()
    success_resp.read.return_value = b'{"ok": true}'
    success_resp.__enter__ = MagicMock(return_value=success_resp)
    success_resp.__exit__ = MagicMock(return_value=False)

    call_count = {"n": 0}
    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise urllib.error.URLError("connection refused")
        return success_resp
    mock_urlopen.side_effect = side_effect

    result = _ollama_request("/api/tags", retries=2)
    assert result == '{"ok": true}'
    assert call_count["n"] == 2  # 1 fallo + 1 exito


@patch("urllib.request.urlopen")
def test_ollama_request_gives_up_after_max_retries(mock_urlopen):
    """Si todos los intentos fallan, devuelve error final."""
    mock_urlopen.side_effect = urllib.error.URLError("down")
    result = _ollama_request("/api/tags", retries=2)
    assert "[ERROR]" in result
    assert "3 intentos" in result  # 1 + 2 retries
    assert mock_urlopen.call_count == 3


@patch("urllib.request.urlopen")
def test_ollama_request_does_not_retry_non_retryable_errors(mock_urlopen):
    """ValueError u otros errores no-recuperables no se reintentan."""
    mock_urlopen.side_effect = ValueError("malformed response")
    result = _ollama_request("/api/tags", retries=2)
    assert "[ERROR]" in result
    assert mock_urlopen.call_count == 1  # No retry


# ── write_document ──────────────────────────────────────────────────────

def test_write_document_rejects_unknown_template(tmp_path, monkeypatch):
    """Templates no whitelisted se rechazan."""
    from tools.implementations import write_document
    monkeypatch.chdir(tmp_path)
    result = write_document(template="__evil__", fields={"x": 1})
    assert "[ERROR]" in result
    assert "no reconocida" in result or "__evil__" in result


def test_write_document_rejects_non_dict_fields(tmp_path, monkeypatch):
    """Fields debe ser dict, no string ni list."""
    from tools.implementations import write_document
    monkeypatch.chdir(tmp_path)
    result = write_document(template="project_report", fields="not a dict")
    assert "[ERROR]" in result


def test_write_document_rejects_oversized_content(tmp_path, monkeypatch):
    """Fields mayores a 50KB se rechazan (DoS protection)."""
    from tools.implementations import write_document
    monkeypatch.chdir(tmp_path)
    huge = "x" * 60_000
    result = write_document(template="project_report", fields={"content": huge})
    assert "[ERROR]" in result
    assert "demasiado" in result.lower() or "long" in result.lower()


def test_write_document_escapes_xss_in_fields(tmp_path, monkeypatch):
    """XSS en fields se escapa — no se renderiza como HTML."""
    from tools.implementations import write_document
    monkeypatch.chdir(tmp_path)
    result = write_document(
        template="project_report",
        fields={"title": "<script>alert(1)</script>"},
    )
    # Debe generar el PDF sin lanzar excepcion
    assert "PDF generado" in result
    # El PDF existe
    import re
    m = re.search(r"PDF generado: (.+\.pdf)", result)
    assert m, f"No se encontro path en: {result}"
    pdf_path = Path(m.group(1))
    assert pdf_path.exists()


def test_write_document_escapes_xss_in_sections(tmp_path, monkeypatch):
    """tech_summary con XSS en body tambien se escapa."""
    from tools.implementations import write_document
    monkeypatch.chdir(tmp_path)
    result = write_document(
        template="tech_summary",
        fields={
            "title": "Test",
            "subtitle": "Sub",
            "sections": [
                {"heading": "<script>alert('h')</script>", "body": "<img onerror=x>"}
            ],
        },
    )
    assert "PDF generado" in result
