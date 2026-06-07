"""Combina los JSONs de baseline y RAG en un report unificado."""
import sys
import json
import glob
import os
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORTS_DIR = Path("data/eval/reports")

files = sorted(REPORTS_DIR.glob("compare_*.json"), key=os.path.getmtime)
if len(files) < 2:
    print(f"Necesito >= 2 reports, encontré {len(files)}")
    sys.exit(1)

baseline_file = files[0]
rag_file = files[-1]

print(f"Baseline: {baseline_file.name}")
print(f"RAG:      {rag_file.name}")

with open(baseline_file, encoding="utf-8") as f:
    base = json.load(f)
with open(rag_file, encoding="utf-8") as f:
    rag = json.load(f)

combined_scores = {
    "baseline": base["scores"].get("baseline", {}),
    "rag":      rag["scores"].get("rag", {}),
    "rag_ft":   {},
}

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
out_md = REPORTS_DIR / f"COMBINED_{ts}.md"
out_json = REPORTS_DIR / f"COMBINED_{ts}.json"

# Write markdown report
with open(out_md, "w", encoding="utf-8") as f:
    f.write(f"# A/B Eval — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
    f.write("Juez: qwen2.5:3B (LLM-as-judge). Golden set: 17 Q&A. Comparativa A/B.\n\n")
    f.write("## Metricas (0-1, higher is better)\n\n")
    f.write("| Metrica | LLM solo | LLM + RAG | Mejora |\n")
    f.write("|---------|----------|-----------|--------|\n")
    metrics = ["answer_relevance", "faithfulness", "context_precision", "context_recall"]
    for m in metrics:
        b = combined_scores["baseline"].get(m)
        r = combined_scores["rag"].get(m)
        if b is None and r is None:
            f.write(f"| {m} | N/A | N/A | - |\n")
        elif b is None:
            f.write(f"| {m} | N/A | {r:.3f} | nuevo |\n")
        elif r is None:
            f.write(f"| {m} | {b:.3f} | N/A | - |\n")
        else:
            imp = ((r - b) / b * 100) if b > 0 else 0
            f.write(f"| {m} | {b:.3f} | {r:.3f} | +{imp:.0f}% |\n")
    f.write("\n## Lectura\n\n")
    f.write("- **answer_relevance** sube con RAG: el modelo contesta mejor lo que se le pregunta.\n")
    f.write("- **faithfulness** baja en RAG: el modelo tiene donde copiar, pero tambien alucina mas (paradoja: con mas material, mas tentacion de inventar).\n")
    f.write("- **context_precision y recall bajos**: el retrieval es el cuello de botella. Corpus de 62 chunks es pequeno.\n")
    f.write("- Trampas (Q15-17, fuera de corpus): el RAG deberia rehusar y dar faithfulness ~1.0.\n\n")
    f.write("## Que nos dice esto para Fase 3 (fine-tuning)\n\n")
    f.write("- RAG aporta el esqueleto (mas cobertura, mejor relevancia)\n")
    f.write("- Falta fidelidad: el fine-tuning con DPO/RLHF deberia subir faithfulness\n")
    f.write("- Si augmentamos el corpus (mas docs) suben context_* metrics\n")

# Write combined JSON
with open(out_json, "w", encoding="utf-8") as f:
    raw_combined = {}
    if "baseline" in base.get("raw", {}):
        raw_combined["baseline"] = base["raw"]["baseline"]
    if "rag" in rag.get("raw", {}):
        raw_combined["rag"] = rag["raw"]["rag"]
    json.dump({"scores": combined_scores, "raw": raw_combined}, f, indent=2, ensure_ascii=False)

# Print to console
print()
print("=" * 60)
print("COMPARATIVA FINAL (baseline vs RAG)")
print("=" * 60)
print(f"{'Metrica':<22} {'baseline':<10} {'rag':<10} {'mejora':<10}")
print("-" * 60)
for m in metrics:
    b = combined_scores["baseline"].get(m)
    r = combined_scores["rag"].get(m)
    b_s = f"{b:.3f}" if b is not None else "N/A"
    r_s = f"{r:.3f}" if r is not None else "N/A"
    if b is not None and r is not None and b > 0:
        imp = f"+{(r - b) / b * 100:.0f}%"
    elif b is None and r is not None:
        imp = "nuevo"
    else:
        imp = "-"
    print(f"{m:<22} {b_s:<10} {r_s:<10} {imp:<10}")
print()
print(f"Reporte: {out_md}")
