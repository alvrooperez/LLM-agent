"""
Observability layer: envuelve el agent loop y registra cada paso a JSONL.

Uso:
  from obs import instrumented_run_agent
  result = instrumented_run_agent("Dime el estado de la GPU")

Cada llamada produce un evento JSONL en data/obs/events.jsonl con:
  - request_id, timestamp, query, model
  - tool_calls[]: nombre, args, duration_ms, result_size, status
  - iterations, total_duration_ms, answer_size
  - gpu_vram_before/after (MB)

Thread-safety: usa contextvars (PEP 567) en lugar de variables globales
para que múltiples requests concurrentes no mezclen sus tool_events.

Pensado para:
  - Phase 5/D: feed de métricas para load testing
  - Debugging: ver qué tools se llaman y cuánto tardan
  - Visualización: generar gráficos con pandas + matplotlib
"""
import os
import sys
import json
import time
import uuid
import datetime
import contextvars
import threading
import subprocess
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Path global
OBS_DIR = Path(os.environ.get("OBS_DIR", "data/obs"))
OBS_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_FILE = OBS_DIR / "events.jsonl"

# Lock para escritura concurrente
_write_lock = threading.Lock()

# ContextVar para thread-safety: cada request concurrente tiene su propia
# lista de tool_events. contextvars se propagan correctamente con asyncio
# y son thread-local cuando se accede desde threads diferentes.
_current_tool_events: contextvars.ContextVar = contextvars.ContextVar(
    "current_tool_events", default=None
)


def get_gpu_vram_mb() -> Optional[int]:
    """Lee VRAM usada en MB via nvidia-smi. None si falla."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            timeout=2, stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        return int(out.split()[0])
    except Exception:
        return None


def write_event(event: dict):
    """Append evento a events.jsonl (thread-safe)."""
    with _write_lock:
        with EVENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def instrumented_run_agent(user_query: str, model: str = "qwen2.5-rag-ft", verbose: bool = False):
    """Wrapper sobre run_agent() que registra cada paso a JSONL.

    Thread-safe: usa contextvars para que multiples requests concurrentes
    no se pisen al registrar tool_calls.
    """
    # Import lazy para evitar circular imports
    sys.path.insert(0, str(Path(__file__).parent))
    from agent.run import run_agent, ollama_chat, execute_tool_call, parse_tool_calls, normalize_tool_call, TOOL_REGISTRY

    request_id = str(uuid.uuid4())[:8]
    t_start = time.time()
    vram_before = get_gpu_vram_mb()

    # Inicializar lista de eventos en el contextvar (thread-local)
    tool_events: list = []
    token = _current_tool_events.set(tool_events)

    total_iterations = 0
    final_answer = ""
    error = None

    # ── Hook: instrumentar execute_tool_call ─────────────────────
    # Solo se patchea si no esta ya patcheado (evita doble-wrapping)
    import agent.run
    if not getattr(agent.run.execute_tool_call, "_is_instrumented", False):
        original_execute = execute_tool_call

        def instrumented_execute(tc: dict) -> str:
            name = tc.get("name", "")
            args = tc.get("arguments", {})
            t0 = time.time()
            status = "ok"
            result = ""
            try:
                result = original_execute(tc)
                if isinstance(result, str) and result.startswith("[ERROR]"):
                    status = "error"
            except Exception as e:
                result = f"[EXCEPTION] {e}"
                status = "exception"
            duration_ms = int((time.time() - t0) * 1000)
            # Leer del contextvar (thread-local)
            events = _current_tool_events.get()
            if events is not None:
                events.append({
                    "name": name,
                    "args": args,
                    "duration_ms": duration_ms,
                    "result_size": len(result),
                    "status": status,
                    "result": result,
                    "result_preview": result[:200],
                })
            return result

        instrumented_execute._is_instrumented = True  # marker
        agent.run.execute_tool_call = instrumented_execute
        patched = True
    else:
        patched = False  # ya estaba patcheado por otra request

    try:
        result = run_agent(user_query, model=model, verbose=verbose)
        final_answer = result["answer"]
        total_iterations = result["iterations"]
    except Exception as e:
        error = str(e)
        final_answer = f"[ERROR] {e}"
    finally:
        # Restaurar solo si fuimos nosotros quienes patcheamos
        if patched:
            agent.run.execute_tool_call = original_execute
        # Limpiar contextvar
        _current_tool_events.reset(token)

    total_duration_ms = int((time.time() - t_start) * 1000)
    vram_after = get_gpu_vram_mb()

    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "request_id": request_id,
        "query": user_query[:500],
        "query_size": len(user_query),
        "model": model,
        "iterations": total_iterations,
        "total_duration_ms": total_duration_ms,
        "answer_size": len(final_answer),
        "answer_preview": final_answer[:200],
        "tool_calls": tool_events,
        "tool_call_count": len(tool_events),
        "error": error,
        "gpu_vram_before_mb": vram_before,
        "gpu_vram_after_mb": vram_after,
    }
    write_event(event)

    return {
        "answer": final_answer,
        "iterations": total_iterations,
        "tool_calls": tool_events,
        "total_duration_ms": total_duration_ms,
        "request_id": request_id,
    }


def summarize_recent(n: int = 10):
    """Lee los últimos n eventos y muestra un resumen."""
    if not EVENTS_FILE.exists():
        print("No events yet")
        return
    lines = EVENTS_FILE.read_text(encoding="utf-8").strip().split("\n")
    events = [json.loads(l) for l in lines[-n:]]

    print(f"\n=== Últimos {len(events)} eventos ===\n")
    for e in events:
        print(f"[{e['timestamp'][:19]}] {e['request_id']} · {e['total_duration_ms']}ms · "
              f"{e['tool_call_count']} tools · {e['iterations']} iter · "
              f"VRAM {e['gpu_vram_before_mb']}→{e['gpu_vram_after_mb']}MB")
        for tc in e.get("tool_calls", []):
            print(f"   └ {tc['name']} · {tc['duration_ms']}ms · {tc['status']}")


if __name__ == "__main__":
    summarize_recent()