"""
Tool registry — sistema de registro ligero para herramientas del agente.

Decoradores:
  @tool(name, description, params) — registra una función como tool

Uso:
  from tools.registry import tool, TOOL_REGISTRY, get_tools_schema

  @tool(name="get_weather", description="Get current weather for a city", params={
      "city": {"type": "string", "description": "City name"}
  })
  def get_weather(city: str) -> str:
      return f"Weather in {city}: sunny"

  TOOL_REGISTRY["get_weather"].fn(city="Madrid")
"""

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class ToolParam:
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str = ""
    default: Any = None
    required: bool = False


@dataclass
class ToolDef:
    name: str
    description: str
    params_schema: Dict[str, ToolParam]
    fn: Callable
    examples: list = field(default_factory=list)


# Global registry
TOOL_REGISTRY: Dict[str, ToolDef] = {}


def tool(name: str, description: str, params: Dict[str, dict], examples: list = None):
    """
    Decorador que registra una función como tool del agente.

    params: dict de { param_name: { "type": str, "description": str, "default": any, "required": bool } }
    examples: lista de ejemplos de uso (opcional)
    """
    def decorator(fn: Callable) -> Callable:
        schema = {}
        for pname, pattr in params.items():
            schema[pname] = ToolParam(
                type=pattr.get("type", "string"),
                description=pattr.get("description", ""),
                default=pattr.get("default"),
                required=pattr.get("required", False),
            )

        TOOL_REGISTRY[name] = ToolDef(
            name=name,
            description=description,
            params_schema=schema,
            fn=fn,
            examples=examples or [],
        )
        return fn
    return decorator


def get_tools_schema() -> list:
    """Devuelve el schema OpenAI-compatible de todas las tools registradas."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        pname: {
                            "type": p.type,
                            "description": p.description,
                            **({} if p.default is None else {"default": p.default}),
                        }
                        for pname, p in t.params_schema.items()
                    },
                    "required": [pname for pname, p in t.params_schema.items() if p.required],
                },
            },
        }
        for t in TOOL_REGISTRY.values()
    ]


def get_system_prompt() -> str:
    """Genera el system prompt del agente con las tools disponibles."""
    tool_list = []
    for t in TOOL_REGISTRY.values():
        params = []
        for pname, p in t.params_schema.items():
            default_str = f" = {repr(p.default)}" if p.default is not None else ""
            params.append(f"    {pname}: {p.type}{default_str} — {p.description}")
        tool_list.append(
            f"{t.name}({', '.join(pname for pname in t.params_schema.keys())}) — {t.description}\n"
            + "\n".join(params)
        )

    return f"""Eres un agente AI con acceso a herramientas (tools). Tu trabajo es responder al usuario usando las herramientas cuando las necesites y PARANDO en cuanto tengas suficiente información.

# Herramientas disponibles

{chr(10).join(f"{i+1}. {t}" for i, t in enumerate(tool_list))}

# Formato de tool call

Para llamar a una herramienta, usa EXACTAMENTE este bloque:
<tool_call>
{{"name": "nombre_tool", "arguments": {{"arg1": "valor1"}}}}
</tool_call>

# Reglas

1. Si necesitas información que solo una tool puede darte, llámala UNA VEZ.
2. Tras recibir el resultado de una tool, evalúa: ¿tienes lo suficiente para responder?
3. Si SÍ tienes lo suficiente, da la respuesta final SIN llamar más tools. Caso típico: search_docs ya te devolvió texto relevante → responde directamente, no vuelvas a buscar.
4. NO llames la misma tool dos veces con la misma query. Si ya la llamaste, usa el resultado.
5. NO encadenes más de 2 tools. Una búsqueda + un plot, vale. Tres búsquedas, NO.
6. SIEMPRE termina tu última respuesta (la final) con la marca [TAREA_COMPLETADA] en una línea nueva.
7. Si la pregunta no requiere ninguna tool (matemáticas, conocimiento general, conversación casual), responde directamente y termina con [TAREA_COMPLETADA].
8. Si la pregunta es off-topic, insegura, o inapropiada, recházala educadamente y termina con [TAREA_COMPLETADA].
9. NUNCA inventes el resultado de una tool. Si dudas, usa otra tool para verificar.

# Ejemplo — cuándo PARAR

Usuario: "¿Qué es Qdrant?"
Tú: <tool_call>{{"name": "search_docs", "arguments": {{"query": "qdrant"}}}}</tool_call>
[recibes resultados]
Tú: "Qdrant es una base de datos vectorial... [TAREA_COMPLETADA]"
NO hagas otra búsqueda. NO listes modelos. NO consultes la GPU. Responde y para.

# Ejemplo — cuándo NO usar tools

Usuario: "¿Cuánto es 2+2?"
Tú: "4. [TAREA_COMPLETADA]"

Usuario: "Hola"
Tú: "¡Hola! ¿En qué te ayudo? [TAREA_COMPLETADA]"
"""