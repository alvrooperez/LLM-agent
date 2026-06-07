"""
Tests para agent/run.py — funciones puras (sin red):
  - normalize_tool_call: convierte formato Ollama a formato interno
  - parse_tool_calls: extrae bloques <tool_call>{...}</tool_call> de texto
  - format_response: limpia markers de tool calls
  - execute_tool_call: maneja tools desconocidas y argumentos invalidos
"""
import sys
import pytest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from agent.run import normalize_tool_call, parse_tool_calls, format_response, execute_tool_call


# ── normalize_tool_call ──────────────────────────────────────────────────

def test_normalize_ollama_format():
    """Ollama devuelve tool_call.function.{name, arguments}."""
    tc = {
        "id": "call_abc",
        "type": "function",
        "function": {
            "name": "get_gpu_stats",
            "arguments": {},
        },
    }
    result = normalize_tool_call(tc)
    assert result == {"name": "get_gpu_stats", "arguments": {}}
    assert "id" not in result
    assert "type" not in result


def test_normalize_already_normalized():
    """Si ya viene en formato {name, arguments}, lo deja igual."""
    tc = {"name": "list_models", "arguments": {}}
    result = normalize_tool_call(tc)
    assert result == {"name": "list_models", "arguments": {}}


def test_normalize_with_args():
    """Arguments pueden ser un dict, deben pasarse tal cual."""
    tc = {
        "function": {
            "name": "write_document",
            "arguments": {"template": "project_report", "fields": {"title": "Test"}},
        },
    }
    result = normalize_tool_call(tc)
    assert result["name"] == "write_document"
    assert result["arguments"]["template"] == "project_report"
    assert result["arguments"]["fields"]["title"] == "Test"


def test_normalize_missing_function():
    """Si no hay 'function', devuelve el dict tal cual (defensivo)."""
    tc = {"name": "test", "arguments": {}}
    result = normalize_tool_call(tc)
    assert result == tc


# ── parse_tool_calls ─────────────────────────────────────────────────────

def test_parse_single_tool_call():
    """Extrae un bloque <tool_call> valido."""
    text = 'Pensando... <tool_call>{"name": "get_gpu_stats", "arguments": {}}</tool_call> Respuesta.'
    result = parse_tool_calls(text)
    assert len(result) == 1
    assert result[0]["name"] == "get_gpu_stats"


def test_parse_multiple_tool_calls():
    """Extrae multiples tool calls en orden."""
    text = ('<tool_call>{"name": "list_models", "arguments": {}}</tool_call>\n'
            'mas texto\n'
            '<tool_call>{"name": "get_gpu_stats", "arguments": {}}</tool_call>')
    result = parse_tool_calls(text)
    assert len(result) == 2
    assert result[0]["name"] == "list_models"
    assert result[1]["name"] == "get_gpu_stats"


def test_parse_multiline_json():
    """JSON multilinea debe parsearse correctamente."""
    text = '<tool_call>{\n  "name": "search_docs",\n  "arguments": {\n    "query": "fine-tuning"\n  }\n}</tool_call>'
    result = parse_tool_calls(text)
    assert len(result) == 1
    assert result[0]["name"] == "search_docs"
    assert result[0]["arguments"]["query"] == "fine-tuning"


def test_parse_no_tool_calls():
    """Si no hay tool calls, devuelve lista vacia."""
    text = "Solo texto normal sin bloques tool_call."
    result = parse_tool_calls(text)
    assert result == []


def test_parse_malformed_json():
    """JSON invalido se ignora silenciosamente."""
    text = '<tool_call>{invalid json}</tool_call>'
    result = parse_tool_calls(text)
    assert result == []


def test_parse_mixed_valid_and_invalid():
    """Bloques validos se extraen aunque haya invalidos entre ellos."""
    text = ('<tool_call>{"name": "a", "arguments": {}}</tool_call>\n'
            '<tool_call>{bad}</tool_call>\n'
            '<tool_call>{"name": "b", "arguments": {}}</tool_call>')
    result = parse_tool_calls(text)
    assert len(result) == 2
    assert result[0]["name"] == "a"
    assert result[1]["name"] == "b"


# ── format_response ──────────────────────────────────────────────────────

def test_format_response_removes_tool_call_blocks():
    """format_response quita los marcadores tool_call del texto visible."""
    raw = 'Voy a llamar <tool_call>{"name": "x", "arguments": {}}</tool_call> ahora.'
    clean = format_response(raw)
    assert "<tool_call>" not in clean
    assert "Voy a llamar" in clean
    assert "ahora." in clean


def test_format_response_returns_empty_for_tool_only():
    """Si el texto es solo un tool call, devuelve string vacio."""
    raw = '<tool_call>{"name": "x", "arguments": {}}</tool_call>'
    clean = format_response(raw)
    assert clean == ""


def test_format_response_preserves_normal_text():
    """Texto sin tool calls pasa tal cual."""
    raw = "Respuesta normal sin tools."
    clean = format_response(raw)
    assert clean == "Respuesta normal sin tools."


# ── execute_tool_call ───────────────────────────────────────────────────

def test_execute_tool_call_unknown_name():
    """Tool call con nombre desconocido devuelve error, no excepcion."""
    result = execute_tool_call({"name": "__nonexistent_tool__", "arguments": {}})
    assert "[ERROR]" in result
    assert "__nonexistent_tool__" in result


def test_execute_tool_call_invalid_arguments():
    """Argumentos invalidos devuelven error, no crashean."""
    import tools.implementations  # noqa: F401
    result = execute_tool_call({"name": "get_gpu_stats", "arguments": {"unexpected": 1}})
    assert "[ERROR]" in result or "argument" in result.lower()


def test_execute_tool_call_none_arguments():
    """Arguments=None se trata como {} (no crashea)."""
    import tools.implementations  # noqa: F401
    result = execute_tool_call({"name": "get_gpu_stats", "arguments": None})
    # get_gpu_stats no requiere args, debe ejecutarse OK
    assert "[ERROR]" not in result
    assert "GPU" in result or "VRAM" in result or "nvidia-smi" in result


def test_execute_tool_call_string_arguments():
    """Arguments como string (bug del modelo) devuelve error claro."""
    result = execute_tool_call({"name": "get_gpu_stats", "arguments": "no es dict"})
    assert "[ERROR]" in result
    assert "dict" in result or "str" in result


def test_execute_tool_call_list_arguments():
    """Arguments como list devuelve error claro."""
    result = execute_tool_call({"name": "get_gpu_stats", "arguments": [1, 2, 3]})
    assert "[ERROR]" in result
    assert "list" in result or "dict" in result


def test_execute_tool_call_empty_name():
    """name vacio devuelve error."""
    result = execute_tool_call({"name": "", "arguments": {}})
    assert "[ERROR]" in result
    assert "inv" in result or "vac" in result or "''" in result


def test_execute_tool_call_missing_name():
    """Sin campo 'name' devuelve error."""
    result = execute_tool_call({"arguments": {}})
    assert "[ERROR]" in result


def test_execute_tool_call_not_dict():
    """tool_call no-dict devuelve error."""
    result = execute_tool_call("no es dict")
    assert "[ERROR]" in result
    assert "dict" in result or "str" in result


def test_execute_tool_call_typeerror_in_args():
    """Si los args no encajan, devuelve mensaje claro con type de error."""
    import tools.implementations  # noqa: F401
    # search_docs espera query:str, k:int. Pasamos k="no es int"
    result = execute_tool_call({"name": "search_docs", "arguments": {"query": "x", "k": "no es int"}})
    assert "[ERROR]" in result


def test_execute_tool_call_exception_during_exec():
    """Si la tool lanza una excepcion, se captura y devuelve error."""
    import tools.implementations  # noqa: F401
    # write_document con template invalido
    result = execute_tool_call({"name": "write_document", "arguments": {"template": "__evil__", "fields": {}}})
    assert "[ERROR]" in result
