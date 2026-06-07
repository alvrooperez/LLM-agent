"""
A/B eval: compara 3 modos sobre el golden dataset.
  - baseline:   LLM solo, sin contexto
  - rag:        Pipeline RAG completo (FastAPI)
  - rag_ft:     RAG con modelo fine-tuneado (placeholder hasta Fase 3)

Calcula métricas RAGAS:
  - Faithfulness (no alucinación)
  - Answer Relevance
  - Context Precision (calidad del ranking)
  - Context Recall (cobertura del ground truth)

Uso:
  python scripts/eval_compare.py --mode baseline
  python scripts/eval_compare.py --mode rag
  python scripts/eval_compare.py --mode all
  python scripts/eval_compare.py --mode all --output report.md
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests
from eval_judge import evaluate_dataset

# ─── Config ────────────────────────────────────────────────────────
RAG_API_URL = os.environ.get("RAG_API_URL", "http://localhost:8000/ask")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
GOLDEN_PATH = Path("data/eval/golden_qa.jsonl")
REPORTS_DIR = Path("data/eval/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TOP_K = 5


# ─── Loaders ───────────────────────────────────────────────────────
def load_golden():
    items = []
    with open(GOLDEN_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


# ─── Query functions ───────────────────────────────────────────────
def query_baseline(question: str) -> dict:
    """LLM solo, sin retrieval."""
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": question, "stream": False},
        timeout=60,
    )
    r.raise_for_status()
    return {"answer": r.json().get("response", "").strip(), "contexts": []}


def query_rag(question: str) -> dict:
    """Pipeline RAG completo vía FastAPI."""
    r = requests.post(
        RAG_API_URL,
        json={"question": question, "k": TOP_K},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "answer": data["answer"],
        "contexts": [s["text"] for s in data.get("sources", [])],
    }


def query_rag_ft(question: str) -> dict:
    """RAG con modelo fine-tuneado (placeholder — mismo que rag hasta Fase 3)."""
    r = query_rag(question)
    r["answer"] = f"[FINE-TUNED PLACEHOLDER]\n{r['answer']}"
    return r


QUERY_FNS = {
    "baseline": query_baseline,
    "rag": query_rag,
    "rag_ft": query_rag_ft,
}


# ─── Run one mode ──────────────────────────────────────────────────
def run_mode(mode: str, items: list[dict]) -> list[dict]:
    print(f"\n=== Modo: {mode} ({len(items)} preguntas) ===")
    fn = QUERY_FNS[mode]
    results = []
    t_start = time.time()
    for i, item in enumerate(items, 1):
        t0 = time.time()
        try:
            r = fn(item["question"])
        except Exception as e:
            print(f"  [{i}/{len(items)}] ERROR: {e}")
            r = {"answer": f"[ERROR: {e}]", "contexts": []}
        dt = time.time() - t0
        print(f"  [{i}/{len(items)}] {dt:.1f}s — {item['question'][:55]}...")
        results.append({
            "question": item["question"],
            "answer": r["answer"],
            "contexts": r["contexts"],
            "ground_truth": item["ground_truth"],
        })
    elapsed = time.time() - t_start
    print(f"  Tiempo total: {elapsed:.1f}s ({elapsed/len(items):.2f}s/preg)")
    return results


# ─── Report ────────────────────────────────────────────────────────
def write_report(scores: dict, output_path: Path):
    metrics_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# A/B Eval Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"Modelo: `{OLLAMA_MODEL}`\n")
        f.write(f"Golden set: {GOLDEN_PATH}\n\n")
        f.write("## Métricas RAGAS\n\n")
        f.write("| Métrica | LLM solo (baseline) | LLM + RAG | LLM + RAG + FT |\n")
        f.write("|---------|---------------------|-----------|----------------|\n")
        for m in metrics_names:
            row = [m]
            for mode in ["baseline", "rag", "rag_ft"]:
                v = scores.get(mode, {}).get(m)
                if v is None:
                    row.append("N/A")
                else:
                    row.append(f"{v:.3f}")
            f.write("| " + " | ".join(row) + " |\n")
        f.write("\n## Notas\n\n")
        f.write("- `context_*` métricas son N/A para baseline (no hay retrieval)\n")
        f.write("- `rag_ft` es placeholder hasta Fase 3 (fine-tuning)\n")


# ─── Main ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=list(QUERY_FNS) + ["all"], default="all")
    parser.add_argument("--output", type=str, default=None,
                        help="Ruta del reporte markdown (default: reports/compare_<fecha>.md)")
    args = parser.parse_args()

    print(f"Cargando golden set...")
    items = load_golden()
    print(f"  {len(items)} Q&A")
    print(f"Juez: {OLLAMA_MODEL} (LLM-as-judge)")

    modes = list(QUERY_FNS) if args.mode == "all" else [args.mode]
    scores = {}
    raw_results = {}

    for mode in modes:
        results = run_mode(mode, items)
        raw_results[mode] = results
        print(f"  Evaluando con LLM-as-judge (4 metricas x {len(items)} preguntas)...")
        eval_result = evaluate_dataset(results)
        scores[mode] = eval_result["averages"]

    # Output
    if args.output:
        out = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = REPORTS_DIR / f"compare_{ts}.md"
    write_report(scores, out)
    print(f"\n✓ Reporte guardado en {out}")

    # Save raw results for inspection
    raw_path = out.with_suffix(".json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"scores": scores, "raw": raw_results}, f, indent=2, ensure_ascii=False)
    print(f"✓ Detalle JSON guardado en {raw_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    metrics_names = ["faithfulness", "answer_relevance", "context_precision", "context_recall"]
    print(f"{'Metrica':<22} {'baseline':<10} {'rag':<10} {'rag_ft':<10}")
    print("-" * 60)
    for m in metrics_names:
        row = [m]
        for mode in ["baseline", "rag", "rag_ft"]:
            v = scores.get(mode, {}).get(m)
            row.append(f"{v:.3f}" if v is not None else "N/A")
        print(f"{row[0]:<22} {row[1]:<10} {row[2]:<10} {row[3]:<10}")


if __name__ == "__main__":
    main()
