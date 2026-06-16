"""
Tests para run_agent_streaming y ollama_chat_streaming.
Solo verifica la forma del generador (no requiere Ollama real,
mockeamos ollama_chat y ollama_chat_streaming).
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import tools.implementations  # noqa: F401
from agent.run import (
    run_agent, run_agent_streaming, ollama_chat, ollama_chat_streaming,
    MAX_ITER
)


# ── ollama_chat_streaming ────────────────────────────────────────────────

@patch("urllib.request.urlopen")
def test_ollama_chat_streaming_yields_tokens(mock_urlopen):
    """ollama_chat_streaming yield cada token del stream."""
    # Simular respuesta NDJSON de Ollama
    lines = [
        b'{"message": {"content": "Hola"}, "done": false}\n',
        b'{"message": {"content": " mundo"}, "done": false}\n',
        b'{"message": {"content": "!"}, "done": true}\n',
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__ = MagicMock(return_value=iter(lines))
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    chunks = list(ollama_chat_streaming(
        messages=[{"role": "user", "content": "test"}],
        model="qwen2.5:3b"
    ))

    # Yield 3 tokens
    assert len(chunks) == 3
    assert chunks[0] == ("Hola", False, {"message": {"content": "Hola"}, "done": False})
    assert chunks[1] == (" mundo", False, {"message": {"content": " mundo"}, "done": False})
    assert chunks[2] == ("!", True, {"message": {"content": "!"}, "done": True})


@patch("urllib.request.urlopen")
def test_ollama_chat_streaming_handles_empty_lines(mock_urlopen):
    """Lineas vacias se ignoran silenciosamente."""
    lines = [
        b'{"message": {"content": "Hi"}, "done": false}\n',
        b'\n',  # vacia
        b'{"message": {"content": "!"}, "done": true}\n',
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__ = MagicMock(return_value=iter(lines))
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    chunks = list(ollama_chat_streaming(messages=[{"role": "user", "content": "x"}]))
    assert len(chunks) == 2
    assert chunks[0][0] == "Hi"
    assert chunks[1][0] == "!"


# ── run_agent_streaming ──────────────────────────────────────────────────

@patch("agent.run.ollama_chat")
def test_run_agent_streaming_simple_response(mock_ollama):
    """Sin tool calls: yield 'thinking' + tokens (reusando respuesta) + 'done'.
    Ya NO se hace segunda llamada a Ollama — reusamos el content de ollama_chat
    y lo emitimos en chunks para simular streaming (optimizacion de latencia)."""
    # Mock: primera llamada devuelve respuesta sin tool calls
    mock_ollama.return_value = {
        "message": {"content": "La respuesta final", "tool_calls": []},
    }
    events = list(run_agent_streaming("hola", model="qwen2.5:3b"))

    # ollama_chat llamado 1 sola vez (no hay segunda llamada a streaming)
    assert mock_ollama.call_count == 1

    # Eventos: thinking, then tokens (chunks de 4 chars), then done
    types = [e["type"] for e in events]
    assert "thinking" in types
    # "La respuesta final" (19 chars) con chunk_size=4 → 5 chunks
    assert types.count("token") == 5
    assert types[-1] == "done"

    # done event tiene el answer completo
    done = events[-1]
    assert done["type"] == "done"
    assert done["answer"] == "La respuesta final"
    assert done["iterations"] == 1


@patch("agent.run.ollama_chat")
def test_run_agent_streaming_with_tool_call(mock_ollama):
    """Con tool calls: yield thinking, tool_call, then reusamos content de
    la siguiente ollama_chat (sin segunda llamada a ollama_chat_streaming)."""
    # Primera iteracion: tool call (get_gpu_stats)
    # Segunda iteracion: respuesta sin tool calls (se reusa el content)
    mock_ollama.side_effect = [
        {
            "message": {
                "content": "",
                "tool_calls": [
                    {"function": {"name": "get_gpu_stats", "arguments": {}}}
                ],
            },
        },
        {
            "message": {"content": "GPU: 4GB", "tool_calls": []},  # final
        },
    ]
    events = list(run_agent_streaming("estado GPU", model="qwen2.5:3b"))

    # ollama_chat llamado 2 veces (1 tool call + 1 final), NO se llama streaming
    assert mock_ollama.call_count == 2

    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "token" in types
    assert types[-1] == "done"

    tool_call_event = next(e for e in events if e["type"] == "tool_call")
    assert tool_call_event["name"] == "get_gpu_stats"
    assert "result" in tool_call_event
    assert "duration_ms" in tool_call_event

    # La respuesta final incluye el texto reusado
    done = events[-1]
    assert done["answer"] == "GPU: 4GB"


@patch("agent.run.ollama_chat")
def test_run_agent_streaming_ollama_error(mock_ollama):
    """Si Ollama falla, yield error event."""
    mock_ollama.return_value = {"error": "connection refused"}

    events = list(run_agent_streaming("hola"))
    types = [e["type"] for e in events]
    assert "error" in types
    error_event = next(e for e in events if e["type"] == "error")
    assert "connection refused" in error_event["message"]


@patch("agent.run.ollama_chat")
def test_run_agent_streaming_max_iter(mock_ollama):
    """Si el modelo entra en loop (mismas tools 2 iter seguidas), early-stop
    yield done con aviso (en vez de esperar MAX_ITER)."""
    # Siempre devuelve tool calls
    mock_ollama.return_value = {
        "message": {
            "content": "",
            "tool_calls": [
                {"function": {"name": "get_gpu_stats", "arguments": {}}}
            ],
        },
    }
    events = list(run_agent_streaming("loop infinito"))
    types = [e["type"] for e in events]
    assert types[-1] == "done"
    # Early-stop message (preferred) o el MAX_ITER message
    answer = events[-1]["answer"]
    assert ("Paré" in answer and "dos veces seguidas" in answer) or \
           ("Limite" in answer or "iteraciones" in answer)
