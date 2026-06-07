"""
A/B eval: qwen2.5:3b (base) vs qwen2.5-rag-ft (fine-tuneado con LoRA).
Mismas 4 tareas multi-step, mide formato y consistencia.
"""
import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tools.implementations  # noqa
from agent.run import run_agent


TASKS = [
    "Dime el estado de la GPU",
    "Lista los modelos que tienes cargados",
    "Dame el número de puntos de la colección ai_engineering_docs en Qdrant",
    "Busca en los docs cómo configurar Qdrant para hacer RAG",
]


def eval_model(model_name: str):
    results = []
    print(f"\n=== Modelo: {model_name} ===")
    for i, task in enumerate(TASKS):
        print(f"\n--- Tarea {i+1}/{len(TASKS)}: {task[:60]}...")
        t0 = time.time()
        r = run_agent(task, model=model_name, verbose=False)
        elapsed = time.time() - t0
        tool_count = len(r["tool_calls"])
        has_completion = "[TAREA_COMPLETADA]" in r["answer"] or "[TEMA_COMPLETADO]" in r["answer"]
        has_tool_call = tool_count > 0
        results.append({
            "task": task,
            "tool_calls": tool_count,
            "iterations": r["iterations"],
            "answer_len": len(r["answer"]),
            "has_completion_token": has_completion,
            "has_tool_call": has_tool_call,
            "elapsed_sec": round(elapsed, 1),
        })
        print(f"  tools={tool_count} iter={r['iterations']} len={len(r['answer'])} done={has_completion} time={elapsed:.1f}s")
    return results


def summarize(results, label):
    n = len(results)
    avg_iter = sum(r["iterations"] for r in results) / n
    avg_len = sum(r["answer_len"] for r in results) / n
    avg_time = sum(r["elapsed_sec"] for r in results) / n
    completion = sum(1 for r in results if r["has_completion_token"])
    tool_use = sum(1 for r in results if r["has_tool_call"])
    print(f"\n=== {label} ===")
    print(f"  Iteraciones medias: {avg_iter:.1f}")
    print(f"  Longitud media: {avg_len:.0f} chars")
    print(f"  Tiempo medio: {avg_time:.1f}s")
    print(f"  Usa tool calls: {tool_use}/{n}")
    print(f"  Cierra con token: {completion}/{n}")


def main():
    base = eval_model("qwen2.5:3b")
    ft = eval_model("qwen2.5-rag-ft")

    print("\n" + "="*60)
    summarize(base, "BASE qwen2.5:3b")
    summarize(ft, "FT qwen2.5-rag-ft")

    out = {"base": base, "ft": ft}
    with open("data/finetune/ab_agent_eval.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n✓ Resultados en data/finetune/ab_agent_eval.json")


if __name__ == "__main__":
    main()