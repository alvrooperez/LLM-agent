"""
rag_latency.py — Mide la latencia de queries con RAG vs sin RAG.

Objetivo: responder "¿vale la pena los X segundos extra de RAG?"

Compara:
  - Sin RAG: el modelo responde directamente (no llama search_docs)
  - Con RAG: el modelo llama search_docs, recibe contexto, y responde

Métricas:
  - Latencia media y p95
  - Overhead de RAG (con_RAG - sin_RAG)
  - Throughput (queries/segundo)

Uso:
  python scripts/rag_latency.py --queries 10
"""
import sys, os, time, statistics, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agent.run import run_agent

# Queries que PUEDEN usar RAG (sobre el dominio) y que NO lo necesitan
RAG_QUERIES = [
    "¿Cómo se configura Qdrant para hacer RAG?",
    "Explica qué hace Ollama con el parámetro temperature.",
    "¿Cuál es la diferencia entre Qwen2.5 y Llama 3?",
    "¿Cómo se hace fine-tuning con Unsloth?",
    "Busca en los docs cómo configurar sentence-transformers",
]

NO_RAG_QUERIES = [
    "¿Cuál es tu color favorito?",
    "Dime un chiste",
    "Cuenta hasta 5",
    "Hola, ¿cómo estás?",
    "Explica qué es un vector de embeddings",
]


def time_query(query: str, model: str = "qwen2.5-rag-ft", force_no_rag: bool = False) -> dict:
    """Ejecuta una query y mide tiempo."""
    # Si force_no_rag, modificamos el system prompt para no usar search_docs
    # (alternativa: monkey-patch search_docs para devolver "")
    from tools.implementations import search_docs as real_search

    if force_no_rag:
        # Patch search_docs para que falle inmediatamente
        import agent.run
        from tools.registry import tool
        @tool(name="__noop_search__", description="noop", params={"query": {"type": "string"}})
        def noop_search(query):
            return "[SEARCH DISABLED FOR LATENCY TEST]"
        # Patchear TOOL_REGISTRY directamente
        from tools.registry import TOOL_REGISTRY
        original_fn = TOOL_REGISTRY["search_docs"].fn
        TOOL_REGISTRY["search_docs"].fn = lambda **kwargs: "[DISABLED]"

    t0 = time.perf_counter()
    try:
        result = run_agent(query, model=model, verbose=False)
    finally:
        if force_no_rag:
            TOOL_REGISTRY["search_docs"].fn = original_fn

    elapsed = time.perf_counter() - t0
    return {
        "query": query,
        "elapsed": elapsed,
        "iterations": result.get("iterations", 0),
        "tool_calls": [tc.get("name") for tc in result.get("tool_calls", [])],
        "answer_len": len(result.get("answer", "")),
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=int, default=5)
    p.add_argument("--model", default="qwen2.5-rag-ft")
    args = p.parse_args()

    print("=" * 60)
    print(f"RAG LATENCY — {args.queries} queries per mode, model={args.model}")
    print("=" * 60)

    # Sin RAG
    print(f"\n[A] Sin RAG (search_docs disabled)")
    no_rag_times = []
    for i, q in enumerate(NO_RAG_QUERIES[:args.queries]):
        r = time_query(q, model=args.model, force_no_rag=True)
        no_rag_times.append(r["elapsed"])
        print(f"  {i+1}. {r['elapsed']:6.1f}s  iters={r['iterations']}  tools={r['tool_calls']}")

    # Con RAG
    print(f"\n[B] Con RAG (search_docs habilitado)")
    rag_times = []
    for i, q in enumerate(RAG_QUERIES[:args.queries]):
        r = time_query(q, model=args.model, force_no_rag=False)
        rag_times.append(r["elapsed"])
        print(f"  {i+1}. {r['elapsed']:6.1f}s  iters={r['iterations']}  tools={r['tool_calls']}")

    # Resumen
    def stats(times, label):
        s = sorted(times)
        return {
            "label": label,
            "n": len(s),
            "min": s[0] if s else 0,
            "max": s[-1] if s else 0,
            "avg": statistics.mean(s) if s else 0,
            "median": statistics.median(s) if s else 0,
            "p95": s[int(len(s)*0.95)] if s else 0,
        }

    s_no_rag = stats(no_rag_times, "Sin RAG")
    s_rag = stats(rag_times, "Con RAG")
    overhead = s_rag["avg"] - s_no_rag["avg"]
    overhead_pct = (overhead / s_no_rag["avg"] * 100) if s_no_rag["avg"] > 0 else 0

    print(f"\n{'='*60}")
    print("RESUMEN")
    print(f"{'='*60}")
    print(f"  {'Mode':15} {'avg':>7} {'median':>7} {'p95':>7} {'min':>7} {'max':>7}")
    for s in [s_no_rag, s_rag]:
        print(f"  {s['label']:15} {s['avg']:>6.1f}s {s['median']:>6.1f}s {s['p95']:>6.1f}s {s['min']:>6.1f}s {s['max']:>6.1f}s")
    print(f"\n  Overhead de RAG: {overhead:+.1f}s ({overhead_pct:+.0f}%)")
    if overhead < 0:
        print("  -> RAG es mas rapido (raro, probablemente por variacion)")
    elif overhead < 5:
        print("  -> RAG vale la pena (overhead aceptable)")
    elif overhead < 15:
        print("  -> RAG tiene overhead moderado, OK para queries tecnicas")
    else:
        print("  -> RAG es lento. Considerar: cache de embeddings, RAG mas pequeno, RAG asincrono")

    # Save
    out = Path("data/rag_latency.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump({
            "model": args.model,
            "no_rag": s_no_rag,
            "rag": s_rag,
            "overhead_sec": overhead,
            "overhead_pct": overhead_pct,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Guardado: {out}")


if __name__ == "__main__":
    main()
