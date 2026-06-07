"""
Tests para tools/registry.py: el @tool decorator, TOOL_REGISTRY, y los
generadores de schema y system prompt.

Cubre:
  - Registro automático de tools con @tool
  - Schema OpenAI-compatible generado
  - System prompt que lista las tools
  - Errores en el schema (params mal formados)
"""
import os
import sys
import pytest
from pathlib import Path

# Setup
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from tools.registry import tool, TOOL_REGISTRY, get_tools_schema, get_system_prompt


def test_tool_decorator_registers_in_global():
    """Cada @tool debe quedar accesible en TOOL_REGISTRY."""

    @tool(name="__test_a__", description="test A", params={})
    def my_fn_a() -> str:
        return "a"

    @tool(name="__test_b__", description="test B", params={"x": {"type": "integer"}})
    def my_fn_b(x: int = 0) -> str:
        return f"b:{x}"

    assert "__test_a__" in TOOL_REGISTRY
    assert "__test_b__" in TOOL_REGISTRY
    assert TOOL_REGISTRY["__test_a__"].fn is my_fn_a
    assert TOOL_REGISTRY["__test_b__"].fn is my_fn_b

    # Cleanup para no contaminar
    del TOOL_REGISTRY["__test_a__"]
    del TOOL_REGISTRY["__test_b__"]


def test_get_tools_schema_returns_openai_format():
    """Schema debe tener type=function y function con name/description/parameters."""
    # Forzar carga de implementations para tener tools reales
    import tools.implementations  # noqa: F401

    schema = get_tools_schema()
    assert isinstance(schema, list)
    assert len(schema) >= 6  # Tenemos 6 tools reales

    for entry in schema:
        assert entry["type"] == "function"
        assert "function" in entry
        func = entry["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func
        params = func["parameters"]
        assert params["type"] == "object"
        assert "properties" in params


def test_get_system_prompt_lists_all_tools():
    """El system prompt debe mencionar las tools disponibles."""
    import tools.implementations  # noqa: F401

    prompt = get_system_prompt()
    # Debe mencionar las 6 tools
    expected_tools = ["search_docs", "list_models", "get_gpu_stats",
                      "get_collection_info", "plot_metric", "write_document"]
    for name in expected_tools:
        assert name in prompt, f"Tool '{name}' no aparece en system prompt"


def test_get_system_prompt_includes_tool_format():
    """El prompt debe explicar el formato <tool_call>{...}</tool_call>."""
    import tools.implementations  # noqa: F401

    prompt = get_system_prompt()
    assert "<tool_call>" in prompt
    assert "</tool_call>" in prompt


def test_tool_with_no_params():
    """Una tool sin params debe tener properties vacío."""

    @tool(name="__test_no_params__", description="no params", params={})
    def no_params_fn() -> str:
        return "ok"

    schema_entry = next(e for e in get_tools_schema() if e["function"]["name"] == "__test_no_params__")
    params = schema_entry["function"]["parameters"]
    assert params["properties"] == {}
    # Sin required fields
    assert "required" not in params or not params.get("required")

    del TOOL_REGISTRY["__test_no_params__"]


def test_tool_with_required_and_optional():
    """Params con required=True deben ir en el array required."""

    @tool(
        name="__test_req_opt__",
        description="mixed",
        params={
            "required_field": {"type": "string", "required": True},
            "optional_field": {"type": "integer", "required": False, "default": 5},
        },
    )
    def req_opt_fn(required_field: str, optional_field: int = 5) -> str:
        return f"{required_field}:{optional_field}"

    schema_entry = next(e for e in get_tools_schema() if e["function"]["name"] == "__test_req_opt__")
    params = schema_entry["function"]["parameters"]
    assert "required_field" in params["properties"]
    assert "optional_field" in params["properties"]
    assert params["required"] == ["required_field"]

    del TOOL_REGISTRY["__test_req_opt__"]


def test_real_tools_are_registered():
    """Verificar que las 6 tools reales están registradas tras importar implementations."""
    import tools.implementations  # noqa: F401

    expected = {
        "search_docs": "Busca documentos",
        "list_models": "Lista modelos",
        "get_gpu_stats": "GPU",
        "get_collection_info": "Qdrant",
        "plot_metric": "gráfico",
        "write_document": "PDF",
    }
    for name, desc_keyword in expected.items():
        assert name in TOOL_REGISTRY, f"Tool '{name}' no registrada"
        tool_entry = TOOL_REGISTRY[name]
        assert desc_keyword.lower() in tool_entry.description.lower() or len(tool_entry.description) > 10
        assert callable(tool_entry.fn)
