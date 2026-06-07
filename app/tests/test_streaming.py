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
    """Sin tool calls: yield 'thinking' + tokens + 'done'."""
    # Mock: primera llamada devuelve respuesta sin tool calls
    mock_ollama.return_value = {
        "message": {"content": "", "tool_calls": []},
    }
    # Mock streaming: 3 tokens
    with patch("agent.run.ollama_chat_streaming") as mock_stream:
        mock_stream.return_value = [
            ("La ", False, {}),
            ("respuesta ", False, {}),
            ("final", True, {}),
        ]
        events = list(run_agent_streaming("hola", model="qwen2.5:3b"))

    # Eventos esperados: thinking, then tokens, then done
    types = [e["type"] for e in events]
    assert "thinking" in types
    assert types.count("token") == 3
    assert types[-1] == "done"

    # done event tiene el answer completo
    done = events[-1]
    assert done["type"] == "done"
    assert done["answer"] == "La respuesta final"
    assert done["iterations"] == 1


@patch("agent.run.ollama_chat")
def test_run_agent_streaming_with_tool_call(mock_ollama):
    """Con tool calls: yield thinking, tool_call, then streaming done."""
    # Primera iteracion: tool call (get_gpu_stats)
    # Segunda iteracion: respuesta sin tool calls (entra a streaming)
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
            "message": {"content": "", "tool_calls": []},  # no more tool calls
        },
    ]
    # Mock streaming para la respuesta final
    with patch("agent.run.ollama_chat_streaming") as mock_stream:
        mock_stream.return_value = [
            ("GPU: 4GB", True, {}),
        ]
        events = list(run_agent_streaming("estado GPU", model="qwen2.5:3b"))

    # ollama_chat llamado 2 veces (1 tool call + 1 final check antes de streaming)
    assert mock_ollama.call_count == 2
    # ollama_chat_streaming llamado 1 vez (respuesta final)
    assert mock_stream.call_count == 1

    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "token" in types
    assert types[-1] == "done"

    tool_call_event = next(e for e in events if e["type"] == "tool_call")
    assert tool_call_event["name"] == "get_gpu_stats"
    assert "result" in tool_call_event
    assert "duration_ms" in tool_call_event


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
    """Si se alcanza MAX_ITER, yield done con aviso."""
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
    assert "Limite" in events[-1]["answer"] or "iteraciones" in events[-1]["answer"]
