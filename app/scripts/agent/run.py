"""
Agent loop — el cerebro del agente Phase 4.

Flujo:
  1. Recibe query del usuario
  2. Construye mensajes con system prompt (tools) + historial + query
  3. Envía a Ollama con tools schema
  4. Si la respuesta contiene <tool_call>...</tool_call> → ejecuta la tool
  5. Añade el resultado de la tool como mensaje "tool" al historial
  6. Vuelve a llamar al modelo
  7. Loop hasta que no haya tool calls o se alcance max_iter
  8. Devuelve la respuesta final (debe terminar en [TAREA_COMPLETADA])

Uso:
  python -u scripts/agent/run.py "Busca cómo configurar Qdrant para hacer RAG"
  python -u scripts/agent/run.py --interactive
"""
import os
import sys
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Boot ──────────────────────────────────────────────────────────────────────

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ── Import tools (esto registra todo en TOOL_REGISTRY) ─────────────────────────
import tools.implementations  # noqa: F401
from tools.registry import TOOL_REGISTRY, get_tools_schema, get_system_prompt

MAX_ITER = int(os.environ.get("MAX_ITER", "5"))


# ── Ollama helpers ──────────────────────────────────────────────────────────────

def ollama_chat(messages: list, tools: list, model: str = "qwen2.5:3b") -> dict:
    """Envía un chat request a Ollama (no-streaming) y devuelve la respuesta raw."""
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 512},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def ollama_chat_streaming(messages: list, model: str = "qwen2.5:3b"):
    """Generador que yield (token, done_dict) tuples desde Ollama en streaming.
    Usa urllib (no async) para evitar añadir dependencias. Adecuado para
    iteraciones finales del agent loop (sin tools) donde queremos latencia baja.

    Args:
        messages: lista de mensajes Ollama format
        model: nombre del modelo

    Yields:
        tuple (token_str, is_done, raw_dict)
        - token_str: el chunk de texto (puede ser vacio si es evento de tool call o done)
        - is_done: True si es el ultimo evento (tambien lleva el dict completo)
        - raw_dict: el dict completo del chunk (para extraer tool_calls si los hay)
    """
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "tools": [],  # streaming + tool calls es complejo; lo deshabilitamos aqui
        "stream": True,
        "options": {"temperature": 0.7, "num_predict": 512},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            line = line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            token = chunk.get("message", {}).get("content", "")
            is_done = chunk.get("done", False)
            yield (token, is_done, chunk)


def normalize_tool_call(tc: dict) -> dict:
    """Normaliza el formato de tool call al que espera execute_tool_call.

    Ollama: {"id": "call_xxx", "function": {"name": "...", "arguments": {...}}}
    Nosotros: {"name": "...", "arguments": {...}}
    """
    if "function" in tc:
        return {
            "name": tc["function"].get("name", ""),
            "arguments": tc["function"].get("arguments", {}),
        }
    return tc


def parse_tool_calls(text: str) -> list:
    """Extrae todos los bloques <tool_call>{...}</tool_call> de un texto.
    Devuelve solo los tool calls que tengan un campo 'name' no vacío.
    Si el JSON es invalido, intenta repararlo quitando caracteres del final
    (util cuando el modelo emite JSON truncado por max_predict).
    """
    pattern = r"<tool_call>\s*(\{.*?\})\s*</tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)
    results = []
    for m in matches:
        obj = None
        try:
            obj = json.loads(m)
        except json.JSONDecodeError:
            # Intentar reparar JSON truncado: buscar substring parseable
            for end in range(len(m), 0, -1):
                try:
                    obj = json.loads(m[:end] + "}")
                    break
                except Exception:
                    pass
        # Solo aceptar tool calls con 'name' (descarta '{}' vacios y reparacion fallida)
        if obj and isinstance(obj, dict) and obj.get("name"):
            results.append(obj)
    return results


def execute_tool_call(tool_call: dict) -> str:
    """Ejecuta una tool y devuelve el resultado como string.

    Validaciones defensivas:
      - tool_call debe ser dict
      - 'name' debe ser string no vacio
      - 'arguments' debe ser dict (no str, no list, no None)
      - name debe estar en TOOL_REGISTRY
    """
    # Validar tipo del tool_call
    if not isinstance(tool_call, dict):
        return f"[ERROR] tool_call debe ser dict, recibí {type(tool_call).__name__}"

    name = tool_call.get("name", "")
    args = tool_call.get("arguments", {})

    # Validar name
    if not name or not isinstance(name, str):
        return f"[ERROR] tool_call.name inválido: {name!r}"

    if name not in TOOL_REGISTRY:
        available = sorted(TOOL_REGISTRY.keys())
        return f"[ERROR] Tool '{name}' no encontrada. Disponibles: {available}"

    # Validar arguments (puede ser None, str, list por bugs del modelo)
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return f"[ERROR] arguments de '{name}' debe ser dict, recibí {type(args).__name__}: {str(args)[:100]}"

    try:
        fn = TOOL_REGISTRY[name].fn
        result = fn(**args)
        return str(result)
    except TypeError as e:
        # Argumentos no encajan con la firma
        return f"[ERROR] Argumentos inválidos para '{name}': {e}. Args recibidos: {list(args.keys())}"
    except Exception as e:
        return f"[ERROR] Ejecución de '{name}' falló ({type(e).__name__}): {e}"


def format_response(text: str) -> str:
    """Limpia el texto de la respuesta del modelo (tool markers, etc)."""
    # Quitar bloques de tool call del texto visible
    cleaned = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL).strip()
    return cleaned


def run_agent(user_query: str, model: str = "qwen2.5:3b", verbose: bool = True) -> dict:
    """Ejecuta el agent loop y devuelve {answer, tool_calls, iterations}."""
    tools_schema = get_tools_schema()
    system_prompt = get_system_prompt()

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    # Añadir query como mensaje de usuario
    messages.append({"role": "user", "content": user_query})

    if verbose:
        print(f"\n🔍 Query: {user_query[:80]}...")

    iterations = 0
    tool_calls_made = []

    while iterations < MAX_ITER:
        iterations += 1

        if verbose:
            print(f"\n  → Iteración {iterations}: enviando a Ollama...")

        response = ollama_chat(messages, tools_schema, model=model)

        if "error" in response:
            return {
                "answer": f"[ERROR] Ollama no responde: {response['error']}",
                "tool_calls": tool_calls_made,
                "iterations": iterations,
            }

        # El modelo puede responder de dos formas:
        # 1. Con content (respuesta de texto)
        # 2. Con tool_calls (pide ejecutar herramientas)

        msg_data = response.get("message", {})
        content = msg_data.get("content", "")
        tool_calls_response = msg_data.get("tool_calls", [])

        # Normalize Ollama format to our format
        tool_calls_response = [normalize_tool_call(tc) for tc in tool_calls_response]

        # Si no hay tool_calls en la respuesta, puede estar en el content como texto
        if not tool_calls_response:
            tool_calls_response = parse_tool_calls(content)

        if tool_calls_response:
            # Filtrar tool calls con name válida
            valid_tcs = [tc for tc in tool_calls_response if tc.get("name")]
            if not valid_tcs:
                # No había tool calls reales, procesar como respuesta final
                messages.append({"role": "assistant", "content": content})
                answer = format_response(content)
                return {"answer": answer, "tool_calls": tool_calls_made, "iterations": iterations}

            # Registrar en historial
            messages.append({"role": "assistant", "content": content})

            if verbose:
                print(f"  → Tool calls detectados: {[tc.get('name') for tc in valid_tcs]}")

            for tc in valid_tcs:
                result = execute_tool_call(tc)
                if verbose:
                    print(f"    └ {tc['name']} → {result[:100]}...")
                # Guardar tool call con su resultado (para UI)
                tool_calls_made.append({**tc, "result": result})
                # Añadir resultado como mensaje tool
                messages.append({
                    "role": "tool",
                    "name": tc["name"],
                    "content": result,
                })
            # Continuar el loop
        else:
            # No más tool calls — respuesta final
            messages.append({"role": "assistant", "content": content})
            answer = format_response(content)
            return {
                "answer": answer,
                "tool_calls": tool_calls_made,
                "iterations": iterations,
            }

    # Se alcanzó MAX_ITER
    return {
        "answer": "[AVISO] Se alcanzó el límite de iteraciones sin completar. " +
                  (messages[-1]["content"] if messages else ""),
        "tool_calls": tool_calls_made,
        "iterations": iterations,
    }


def run_agent_streaming(user_query: str, model: str = "qwen2.5:3b", verbose: bool = False):
    """Igual que run_agent, pero yield los tokens de la respuesta final
    en streaming desde Ollama (no en bloque).

    Yields:
        dict con keys:
          - type: 'tool_call' | 'token' | 'done' | 'error' | 'thinking'
          - Para tool_call: {name, arguments, result, duration_ms}
          - Para token: {text}
          - Para done: {answer (final), tool_calls, iterations, elapsed_sec}
          - Para error: {message}
          - Para thinking: {iter} (indicador de fase de thinking)
    """
    tools_schema = get_tools_schema()
    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt},
               {"role": "user", "content": user_query}]

    iterations = 0
    tool_calls_made = []
    t_start = time.time()

    while iterations < MAX_ITER:
        iterations += 1
        yield {"type": "thinking", "iter": iterations}

        # Iteraciones con tools: NO streaming (porque el modelo puede o no
        # llamar tools, y queremos el dict completo para detectar tool_calls)
        response = ollama_chat(messages, tools_schema, model=model)
        if "error" in response:
            yield {"type": "error", "message": f"Ollama no responde: {response['error']}"}
            return

        msg_data = response.get("message", {})
        content = msg_data.get("content", "")
        tool_calls_response = [normalize_tool_call(tc) for tc in msg_data.get("tool_calls", [])]
        if not tool_calls_response:
            tool_calls_response = parse_tool_calls(content)

        if tool_calls_response:
            valid_tcs = [tc for tc in tool_calls_response if tc.get("name")]
            if not valid_tcs:
                # Texto sin tool calls validos -> respuesta final (no streaming)
                messages.append({"role": "assistant", "content": content})
                yield {"type": "done", "answer": format_response(content),
                       "tool_calls": tool_calls_made, "iterations": iterations,
                       "elapsed_sec": round(time.time() - t_start, 2)}
                return

            messages.append({"role": "assistant", "content": content})
            for tc in valid_tcs:
                t0 = time.time()
                result = execute_tool_call(tc)
                duration_ms = int((time.time() - t0) * 1000)
                tool_calls_made.append({**tc, "result": result, "duration_ms": duration_ms})
                yield {"type": "tool_call", "name": tc["name"],
                       "arguments": tc.get("arguments", {}),
                       "result": result, "duration_ms": duration_ms}
                messages.append({"role": "tool", "name": tc["name"], "content": result})
        else:
            # Respuesta final SIN tool calls -> STREAMING
            # Ya tenemos el contenido completo; re-llamamos a Ollama en streaming
            # para emitir token por token. Es un poco ineficiente (doble llamada)
            # pero garantiza que el modelo produce la misma respuesta.
            # NOTA: Ollama puede ser no-determinista con temperature>0, asi que
            # hacemos la llamada streaming directamente con el MISMO messages.
            full_text = ""
            for token, is_done, _ in ollama_chat_streaming(messages, model=model):
                if token:
                    full_text += token
                    yield {"type": "token", "text": token}
                if is_done:
                    break

            messages.append({"role": "assistant", "content": full_text})
            answer = format_response(full_text)
            yield {"type": "done", "answer": answer,
                   "tool_calls": tool_calls_made, "iterations": iterations,
                   "elapsed_sec": round(time.time() - t_start, 2)}
            return

    # MAX_ITER alcanzado
    yield {"type": "done", "answer": "[AVISO] Limite de iteraciones alcanzado.",
           "tool_calls": tool_calls_made, "iterations": iterations,
           "elapsed_sec": round(time.time() - t_start, 2)}


def interactive():
    """Modo interactivo: lee queries del stdin."""
    print("=== Agent interactivo ===")
    print("Escribe tu pregunta. Ctrl+C para salir.\n")
    while True:
        try:
            query = input("> ").strip()
            if not query:
                continue
            result = run_agent(query, verbose=True)
            print(f"\n📤 Respuesta:\n{result['answer']}\n")
            print(f"   Tools usadas: {len(result['tool_calls'])}, Iteraciones: {result['iterations']}")
        except KeyboardInterrupt:
            print("\nAdiós.")
            break


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent tool-calling con Ollama")
    parser.add_argument("query", nargs="?", help="Query a procesar")
    parser.add_argument("--interactive", "-i", action="store_true", help="Modo interactivo")
    parser.add_argument("--model", default="qwen2.5:3b", help="Modelo Ollama (default: qwen2.5:3b)")
    args = parser.parse_args()

    if args.interactive or not args.query:
        interactive()
    else:
        result = run_agent(args.query, model=args.model, verbose=True)
        print(f"\n{'='*60}")
        print(f"📤 Respuesta final:")
        print(result["answer"])
        print(f"\n   Tool calls: {[tc['name'] for tc in result['tool_calls']]}")
        print(f"   Iteraciones: {result['iterations']}/{MAX_ITER}")


if __name__ == "__main__":
    main()