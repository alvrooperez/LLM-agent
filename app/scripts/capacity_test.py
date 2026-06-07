"""
Finds the maximum concurrent load the system can sustain.

Runs escalating rounds:
  Round 1: 1 concurrent
  Round 2: 2 concurrent
  Round 3: 4 concurrent
  ...
  Until failure rate > 10% OR wall latency > 60s

Reports:
  - Max sustainable concurrent users
  - Throughput at each level
  - Latency degradation curve
  - Where it breaks
"""
import os, sys, json, time, statistics, subprocess, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

sys.path.insert(0, str(Path(__file__).parent))
BASE_URL = os.environ.get("CHAT_URL", "http://localhost:8090")
CHAT_URL = f"{BASE_URL}/api/chat"

# Queries vary to avoid Ollama prompt caching giving unrealistic speedups
QUERIES = [
    {"id": "q1", "message": "Dame el estado de la GPU",          "model": "qwen2.5-rag-ft"},
    {"id": "q2", "message": "Lista los modelos de Ollama",      "model": "qwen2.5-rag-ft"},
    {"id": "q3", "message": "¿Cuántos puntos hay en Qdrant?",   "model": "qwen2.5-rag-ft"},
    {"id": "q4", "message": "¿Cuál es tu color favorito?",      "model": "qwen2.5:3b"},
    {"id": "q5", "message": "Explica qué es un vector de embeddings", "model": "qwen2.5:3b"},
]


def get_vram_mb():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            timeout=3, stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        return int(out.split()[0])
    except Exception:
        return None


@dataclass
class Result:
    ok: bool
    wall_ms: float
    srv_ms: float
    tools: int
    err: str = ""


def one_request(payload: dict) -> Result:
    t0 = time.perf_counter()
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            CHAT_URL, data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read())
            wall_ms = (time.perf_counter() - t0) * 1000
            return Result(
                ok=True,
                wall_ms=wall_ms,
                srv_ms=body.get("elapsed_sec", 0) * 1000,
                tools=len(body.get("tool_calls", [])),
            )
    except Exception as e:
        wall_ms = (time.perf_counter() - t0) * 1000
        return Result(ok=False, wall_ms=wall_ms, srv_ms=0, tools=0, err=str(e)[:100])


def run_round(concurrent: int, total: int, label: str) -> dict:
    """Ejecuta una ronda y devuelve métricas."""
    results = []
    t0 = time.perf_counter()
    vram_before = get_vram_mb()

    with ThreadPoolExecutor(max_workers=concurrent) as ex:
        futures = [
            ex.submit(one_request, QUERIES[i % len(QUERIES)])
            for i in range(total)
        ]
        for f in as_completed(futures):
            results.append(f.result())

    wall_total = time.perf_counter() - t0
    vram_after = get_vram_mb()
    ok = [r for r in results if r.ok]
    fail = [r for r in results if not r.ok]

    ok_wall = sorted([r.wall_ms for r in ok])
    ok_srv  = sorted([r.srv_ms  for r in ok])
    n = len(ok)

    def pct(lst, p):
        return lst[int(len(lst) * p)] if lst else 0

    fail_rate = len(fail) / len(results) if results else 1.0

    row = {
        "label": label,
        "concurrent": concurrent,
        "total": total,
        "ok": len(ok), "fail": len(fail),
        "fail_rate_pct": round(fail_rate * 100, 1),
        "wall_p50": round(pct(ok_wall, 0.50), 0),
        "wall_p95": round(pct(ok_wall, 0.95), 0),
        "wall_p99": round(pct(ok_wall, 0.99), 0),
        "wall_max": round(max(ok_wall), 0) if ok_wall else 0,
        "srv_p50":  round(pct(ok_srv,  0.50), 0),
        "srv_p95":  round(pct(ok_srv,  0.95), 0),
        "srv_avg":  round(statistics.mean(ok_srv), 0) if ok_srv else 0,
        "throughput_rps": round(len(ok) / wall_total, 2),
        "vram_before": vram_before,
        "vram_after": vram_after,
        "vram_delta": (vram_after or 0) - (vram_before or 0),
    }

    mark = "✓" if fail_rate == 0 else "⚠" if fail_rate < 0.1 else "✗"
    print(f"  {mark} [{label:8}] c={concurrent:2d}  "
          f"ok={len(ok):2d} fail={len(fail):2d}  "
          f"p50={row['wall_p50']:6.0f}ms  "
          f"p95={row['wall_p95']:6.0f}ms  "
          f"throughput={row['throughput_rps']:.2f}r/s  "
          f"fail={row['fail_rate_pct']:.0f}%")
    return row


def run_capacity_test():
    print(f"\n{'='*70}")
    print(f"CAPACITY TEST — buscando el límite máximo de concurrencia")
    print(f"URL: {CHAT_URL}")
    print(f"{'='*70}\n")

    print(f"{'RESULT':8} {'CONC':4} {'OK':3} {'FAIL':4} {'p50':>7} {'p95':>7} {'p99':>7} "
          f"{'max':>7} {'r/s':>6} {'fail%':>5}  {'vram Δ':>7}")
    print(f"{'─'*70}")

    levels = [1, 2, 3, 4, 5, 6, 8, 10]
    rows = []
    break_cause = None

    for i, conc in enumerate(levels):
        label = f"round_{i+1}"
        total = conc * 3  # 3 queries por concurrent user

        row = run_round(conc, total, label)
        rows.append(row)

        # Criteria to stop: >10% failures OR p50 wall > 60s OR p95 > 120s
        if row["fail_rate_pct"] > 10:
            break_cause = f"{row['fail_rate_pct']:.0f}% failure rate at {conc} concurrent"
            break
        if row["wall_p50"] > 60000:
            break_cause = f"p50 wall latency >60s at {conc} concurrent"
            break
        if row["wall_p95"] > 120000:
            break_cause = f"p95 wall latency >120s at {conc} concurrent"
            break

        time.sleep(3)  # cooldown entre rondas

    print(f"\n{'='*70}")
    print(f"RESULTADOS")
    print(f"{'='*70}")

    # Tabla
    print(f"\n{'Conc':5} {'OK/Fail':8} {'p50(ms)':9} {'p95(ms)':9} {'r/s':>6} {'Fail%':>6} {'VramΔ':>7}")
    print(f"{'─'*55}")
    for r in rows:
        okfail = f"{r['ok']}/{r['fail']}"
        print(f"{r['concurrent']:5d} {okfail:>8} "
              f"{r['wall_p50']:>9,.0f} {r['wall_p95']:>9,.0f} "
              f"{r['throughput_rps']:>6.2f} {r['fail_rate_pct']:>6.1f}% {r['vram_delta']:>+7d}")

    # Chart de latencia vs concurrencia
    print(f"\nLatencia p50 vs concurrencia:")
    max_p50 = max(r["wall_p50"] for r in rows)
    for r in rows:
        bar_len = int(r["wall_p50"] / max_p50 * 30) if max_p50 > 0 else 0
        bar = "█" * bar_len + "░" * (30 - bar_len)
        print(f"  c={r['concurrent']:2d} │{bar} {r['wall_p50']:,.0f}ms")

    print(f"\nThroughput vs concurrencia:")
    max_rps = max(r["throughput_rps"] for r in rows)
    for r in rows:
        bar_len = int(r["throughput_rps"] / max_rps * 30) if max_rps > 0 else 0
        bar = "█" * bar_len + "░" * (30 - bar_len)
        print(f"  c={r['concurrent']:2d} │{bar} {r['throughput_rps']:.2f}r/s")

    # Conclusiones
    ok_rows = [r for r in rows if r["fail_rate_pct"] == 0]
    best_throughput = max(rows, key=lambda r: r["throughput_rps"])
    best_p50 = min(ok_rows, key=lambda r: r["wall_p50"]) if ok_rows else rows[0]
    max_safe = max([r["concurrent"] for r in ok_rows]) if ok_rows else 0

    print(f"\n{'='*70}")
    print(f"CONCLUSIONES")
    print(f"{'='*70}")
    print(f"  Máximo concurrentes sin errores:   {max_safe}")
    print(f"  Mejor throughput:                   {best_throughput['throughput_rps']:.2f} r/s (c={best_throughput['concurrent']})")
    print(f"  Latencia más baja (p50):            {best_p50['wall_p50']:,.0f}ms (c={best_p50['concurrent']})")
    if break_cause:
        print(f"  El sistema se rompe en:            {break_cause}")
    else:
        print(f"  No se alcanzó el límite en c={levels[-1]} — posible escalar más")

    # Save
    out = Path("data/capacity_test_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump({
            "config": {"levels": levels, "queries": len(QUERIES)},
            "break_cause": break_cause,
            "max_safe_concurrent": max_safe,
            "best_throughput": best_throughput,
            "best_p50": best_p50,
            "rows": rows,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Guardado: {out}")
    return rows


if __name__ == "__main__":
    run_capacity_test()
