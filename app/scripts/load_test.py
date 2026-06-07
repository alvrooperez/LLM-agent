"""
Phase 5D — Load test para el chat endpoint.

Ejecuta N requests concurrentes contra /api/chat, mide latencia y reporta:
  - p50 / p95 / p99 latencia
  - throughput (req/s)
  - tasa de éxito
  - tool call rate
  - VRAM antes/después

Uso:
  python scripts/load_test.py --concurrent 3 --total 12
  python scripts/load_test.py --concurrent 5 --total 20
  python scripts/load_test.py --concurrent 10 --total 30

Las queries son fixed para reproducibilidad, una de cada tipo:
  - RAG (búsqueda en docs)
  - Tool call (estado GPU)
  - Sin tool (conversación simple)
"""
import os
import sys
import json
import time
import statistics
import subprocess
import threading
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

BASE_URL = os.environ.get("CHAT_URL", "http://localhost:8090")
CHAT_URL = f"{BASE_URL}/api/chat"

QUERIES = [
    {
        "id": "rag",
        "message": "Busca en los docs cómo configurar RAG con vectores",
        "model": "qwen2.5-rag-ft",
        "expect_tools": True,
    },
    {
        "id": "gpu",
        "message": "Dime el estado de la GPU",
        "model": "qwen2.5-rag-ft",
        "expect_tools": True,
    },
    {
        "id": "chat",
        "message": "¿Cuál es tu color favorito?",
        "model": "qwen2.5-rag-ft",
        "expect_tools": False,
    },
    {
        "id": "models",
        "message": "Lista los modelos disponibles en Ollama",
        "model": "qwen2.5-rag-ft",
        "expect_tools": True,
    },
    {
        "id": "qdrant",
        "message": "¿Cuántos puntos hay en la colección de Qdrant?",
        "model": "qwen2.5-rag-ft",
        "expect_tools": True,
    },
    {
        "id": "base_chat",
        "message": "Explícame qué es un vector de embeddings",
        "model": "qwen2.5:3b",
        "expect_tools": False,
    },
]


@dataclass
class RequestResult:
    query_id: str
    wall_ms: float
    server_ms: float
    status: int
    iterations: int
    tool_calls: int
    success: bool
    error: str = ""
    vram_before: Optional[int] = None
    vram_after: Optional[int] = None


def get_vram_mb() -> Optional[int]:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            timeout=3, stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        return int(out.split()[0])
    except Exception:
        return None


def send_request(payload: dict) -> RequestResult:
    query_id = payload["id"]
    vram_before = get_vram_mb()
    t0 = time.perf_counter()
    status = 0
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            CHAT_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
        wall_ms = (time.perf_counter() - t0) * 1000
        server_ms = body.get("elapsed_sec", 0) * 1000
        success = status == 200 and len(body.get("answer", "")) > 0
        result = RequestResult(
            query_id=query_id,
            wall_ms=wall_ms,
            server_ms=server_ms,
            status=status,
            iterations=body.get("iterations", 0),
            tool_calls=len(body.get("tool_calls", [])),
            success=success,
            vram_before=vram_before,
            vram_after=get_vram_mb(),
        )
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        wall_ms = (time.perf_counter() - t0) * 1000
        result = RequestResult(
            query_id=query_id, wall_ms=wall_ms, server_ms=0,
            status=e.code, iterations=0, tool_calls=0, success=False,
            error=f"HTTP {e.code}: {body[:200]}",
            vram_before=vram_before, vram_after=get_vram_mb(),
        )
    except Exception as e:
        wall_ms = (time.perf_counter() - t0) * 1000
        result = RequestResult(
            query_id=query_id, wall_ms=wall_ms, server_ms=0,
            status=0, iterations=0, tool_calls=0, success=False,
            error=str(e)[:200],
            vram_before=vram_before, vram_after=get_vram_mb(),
        )
    return result


def run_load_test(concurrent: int, total: int, warmup: int = 2):
    print(f"\n{'='*60}")
    print(f"LOAD TEST — {concurrent} concurrentes, {total} requests totales")
    print(f"URL: {CHAT_URL}")
    print(f"{'='*60}\n")

    # ── Warmup ────────────────────────────────────────────────
    if warmup > 0:
        print(f"[Warmup] {warmup} requests...")
        with ThreadPoolExecutor(max_workers=warmup) as ex:
            futures = [
                ex.submit(send_request, {**QUERIES[i % len(QUERIES)], "model": "qwen2.5-rag-ft"})
                for i in range(warmup)
            ]
            for f in as_completed(futures):
                f.result()
        print("[Warmup] OK\n")

    # ── Run ─────────────────────────────────────────────────
    print(f"[Run] Enviando {total} requests ({concurrent} concurrentes)...")
    t_start = time.perf_counter()
    results: list[RequestResult] = []

    with ThreadPoolExecutor(max_workers=concurrent) as ex:
        futures = [
            ex.submit(send_request, QUERIES[i % len(QUERIES)])
            for i in range(total)
        ]
        for f in as_completed(futures):
            r = f.result()
            results.append(r)
            mark = "✓" if r.success else "✗"
            print(f"  {mark} [{r.query_id:10}] {r.wall_ms:6.0f}ms  "
                  f"srv={r.server_ms:6.0f}ms  tools={r.tool_calls}  "
                  f"{'ERR: ' + r.error[:50] if r.error else ''}")

    wall_total = time.perf_counter() - t_start

    # ── Report ───────────────────────────────────────────────
    successes = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    wall_times = [r.wall_ms for r in successes]
    server_times = [r.server_ms for r in successes]
    tool_rates = [r.tool_calls for r in successes]

    print(f"\n{'─'*60}")
    print(f"RESULTADOS ({len(successes)}/{total} exitosos)")
    print(f"{'─'*60}")
    print(f"  Duración total:    {wall_total:.1f}s")
    print(f"  Throughput:         {total/wall_total:.2f} req/s")
    print(f"  Throughput efectivo:{len(successes)/wall_total:.2f} req/s (exitosos)")
    print(f"")
    print(f"  Latencia (wall clock):")
    print(f"    p50:  {sorted(wall_times)[int(len(wall_times)*0.50)]:.0f}ms")
    print(f"    p95:  {sorted(wall_times)[int(len(wall_times)*0.95)]:.0f}ms")
    print(f"    p99:  {sorted(wall_times)[int(len(wall_times)*0.99)]:.0f}ms")
    print(f"    min:  {min(wall_times):.0f}ms")
    print(f"    max:  {max(wall_times):.0f}ms")
    print(f"    avg:  {statistics.mean(wall_times):.0f}ms")
    print(f"")
    print(f"  Latencia (server-side):")
    print(f"    p50:  {sorted(server_times)[int(len(server_times)*0.50)]:.0f}ms")
    print(f"    p95:  {sorted(server_times)[int(len(server_times)*0.95)]:.0f}ms")
    print(f"    avg:  {statistics.mean(server_times):.0f}ms")
    print(f"")
    print(f"  Tool calls:")
    print(f"    Tasa:         {statistics.mean(tool_rates):.2f} tools/req")
    print(f"    Reqs con ≥1:  {sum(1 for t in tool_rates if t > 0)}/{len(tool_rates)}")
    print(f"    Total:        {sum(tool_rates)}")
    print(f"")

    if failed:
        print(f"  FALLOS ({len(failed)}):")
        for r in failed:
            print(f"    [{r.query_id}] {r.error[:80]}")
    else:
        print(f"  Fallos: 0/{total}")

    # VRAM
    vram_vals = [(r.vram_before, r.vram_after) for r in results if r.vram_before is not None]
    if vram_vals:
        before = [v[0] for v in vram_vals]
        after = [v[1] for v in vram_vals]
        print(f"")
        print(f"  VRAM (nvidia-smi):")
        print(f"    Antes: {statistics.mean(before):.0f} MB (avg)")
        print(f"    Después: {statistics.mean(after):.0f} MB (avg)")
        print(f"    Delta: {statistics.mean(after) - statistics.mean(before):+.0f} MB")

    # ── Persist ─────────────────────────────────────────────
    out_path = Path("data/load_test_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({
            "config": {"concurrent": concurrent, "total": total, "warmup": warmup},
            "summary": {
                "success_rate": len(successes) / total,
                "wall_p50": sorted(wall_times)[int(len(wall_times)*0.50)] if wall_times else 0,
                "wall_p95": sorted(wall_times)[int(len(wall_times)*0.95)] if wall_times else 0,
                "throughput": total / wall_total if wall_total > 0 else 0,
                "tool_call_rate": statistics.mean(tool_rates) if tool_rates else 0,
            },
            "results": [asdict(r) for r in results],
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Guardado: {out_path}")


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Load test para AI Engineering Chat")
    parser.add_argument("--concurrent", "-c", type=int, default=3,
                        help="Usuarios concurrentes (default: 3)")
    parser.add_argument("--total", "-n", type=int, default=12,
                        help="Total de requests (default: 12)")
    parser.add_argument("--warmup", "-w", type=int, default=2,
                        help="Requests de warmup (default: 2)")
    args = parser.parse_args()

    run_load_test(args.concurrent, args.total, args.warmup)
