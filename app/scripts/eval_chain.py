"""
Phase 5F — Multi-tool chaining eval.

Evalúa si el agente puede encadenar 2-3 tool calls en una sola respuesta
sin necesidad de repreguntar al usuario. Esto es lo que diferencia un
agent capaz de uno que solo hace una cosa.

Queries diseñadas para requerir chaining:
  1. "Dame el estado de la GPU y cuántos puntos hay en Qdrant"
     → get_gpu_stats + get_collection_info

  2. "Busca en docs cómo hacer fine-tuning y dime qué modelos tienes"
     → search_docs + list_models

  3. "Lista los modelos y para cada uno dime el estado de la GPU"
     → list_models + get_gpu_stats

  4. "Genera un PDF de project_report con título 'Evaluación multi-tool'
     y luego muéstrame el estado de la GPU"
     → write_document + get_gpu_stats

  5. "Cuántos puntos hay en Qdrant, qué modelos tienes disponibles
     y cuál es el estado de la GPU"
     → get_collection_info + list_models + get_gpu_stats

Métricas:
  - Tasa de chaining exitoso (llama ≥2 tools en la misma iteración)
  - Longitud de la cadena
  - Tasks completadas vs abortadas
"""
import sys, json, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agent.run import run_agent

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHAIN_TASKS = [
    {
        "id": "gpu_qdrant",
        "query": "Dame el estado de la GPU y cuántos puntos hay en Qdrant",
        "expected_tools": {"get_gpu_stats", "get_collection_info"},
        "min_chain": 2,
    },
    {
        "id": "docs_models",
        "query": "Busca en los docs cómo hacer fine-tuning y dime qué modelos tienes disponibles",
        "expected_tools": {"search_docs", "list_models"},
        "min_chain": 2,
    },
    {
        "id": "models_gpu",
        "query": "Lista los modelos de Ollama y dime el estado de la GPU",
        "expected_tools": {"list_models", "get_gpu_stats"},
        "min_chain": 2,
    },
    {
        "id": "pdf_gpu",
        "query": "Genera un PDF de project_report con título 'Evaluación multi-tool chaining' y luego muéstrame el estado de la GPU",
        "expected_tools": {"write_document", "get_gpu_stats"},
        "min_chain": 2,
    },
    {
        "id": "qdrant_models_gpu",
        "query": "Cuántos puntos hay en Qdrant, qué modelos tienes disponibles y cuál es el estado de la GPU",
        "expected_tools": {"get_collection_info", "list_models", "get_gpu_stats"},
        "min_chain": 3,
    },
]


def run_chain_eval(tasks, model="qwen2.5-rag-ft", verbose=True):
    results = []

    for task in tasks:
        tid = task["id"]
        if verbose:
            print(f"\n{'='*60}")
            print(f"[{tid}] {task['query'][:60]}...")

        r = run_agent(task["query"], model=model, verbose=verbose)
        tcs = r.get("tool_calls", [])
        tc_names = {tc["name"] for tc in tcs}
        found = tc_names & task["expected_tools"]
        missed = task["expected_tools"] - tc_names

        # Contar herramientas en cada iteración (aproximado: por tool_calls global)
        chain_count = len(tcs)
        is_chain = chain_count >= task["min_chain"]

        status = "PASS" if is_chain else "PARTIAL" if found else "FAIL"
        if verbose:
            print(f"  → Status: {status}")
            print(f"  → Tools llamadas: {sorted(tc_names)}")
            print(f"  → Esperadas:     {sorted(task['expected_tools'])}")
            print(f"  → Encontradas:   {sorted(found)}")
            print(f"  → Perdidas:      {sorted(missed)}")

        results.append({
            "task_id": tid,
            "query": task["query"],
            "status": status,
            "tools_called": list(tc_names),
            "expected_tools": list(task["expected_tools"]),
            "found_tools": list(found),
            "missed_tools": list(missed),
            "chain_count": chain_count,
            "iterations": r.get("iterations", 0),
            "answer_length": len(r.get("answer", "")),
        })

    # ── Summary ─────────────────────────────────────────────────
    passed = [x for x in results if x["status"] == "PASS"]
    partial = [x for x in results if x["status"] == "PARTIAL"]
    failed = [x for x in results if x["status"] == "FAIL"]
    total = len(results)

    print(f"\n{'='*60}")
    print(f"MULTI-TOOL CHAINING EVAL — {model}")
    print(f"{'='*60}")
    print(f"  PASS:     {len(passed)}/{total}")
    print(f"  PARTIAL:  {len(partial)}/{total}")
    print(f"  FAIL:     {len(failed)}/{total}")
    print(f"  Chaining rate: {len(passed)/total*100:.0f}%")
    print()

    for r in results:
        mark = {"PASS": "✓", "PARTIAL": "◐", "FAIL": "✗"}[r["status"]]
        print(f"  {mark} [{r['task_id']}] chain={r['chain_count']} "
              f"found={sorted(r['found_tools'])}")

    # Guardar
    out = Path("data/eval_chain_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump({
            "model": model,
            "summary": {
                "pass": len(passed), "partial": len(partial),
                "fail": len(failed), "total": total,
                "chaining_rate": len(passed) / total,
            },
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {out}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-rag-ft")
    args = parser.parse_args()
    run_chain_eval(CHAIN_TASKS, model=args.model)
