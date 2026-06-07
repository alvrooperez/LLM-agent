"""
LLM-as-a-Judge: evalúa respuestas RAG con 4 métricas usando el propio LLM como juez.

Métricas:
  - Faithfulness:     ¿La respuesta se basa solo en el contexto? (sin alucinaciones)
  - Answer Relevance: ¿La respuesta contesta la pregunta?
  - Context Precision: ¿Los chunks retrieved son relevantes y bien rankeados?
  - Context Recall:   ¿El ground truth está cubierto por el contexto?

Cada métrica devuelve un score 0.0-1.0.

Uso:
  python scripts/eval_judge.py --input results.json
  # o integrado con eval_compare.py
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")


def call_judge(prompt: str, max_retries: int = 2) -> str:
    """Llama al LLM juez y devuelve el texto de la respuesta."""
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}},
                timeout=60,
            )
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except Exception as e:
            if attempt == max_retries:
                return f"[ERROR: {e}]"
    return ""


# ─── Métricas ──────────────────────────────────────────────────────
def score_faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    """0-1: ¿La respuesta está soportada por el contexto?"""
    ctx = "\n---\n".join(contexts[:5])
    prompt = f"""Eres un evaluador estricto de un sistema RAG. Tu trabajo es detectar alucinaciones.

CONTEXTO (información disponible):
{ctx}

PREGUNTA: {question}

RESPUESTA DEL MODELO:
{answer}

¿Cada afirmación concreta de la respuesta está respaldada por el contexto? Si la respuesta añade información que NO está en el contexto (incluso si es verdadera), es una alucinación.

Responde SOLO con un número entre 0.0 y 1.0, donde:
  1.0 = toda la respuesta está respaldada por el contexto
  0.5 = mitad de la respuesta es alucinación
  0.0 = la respuesta es completamente inventada

Si la respuesta dice "no tengo información" o "no sé" y el contexto no la contiene, eso es 1.0 (comportamiento correcto).

SCORE:"""
    out = call_judge(prompt)
    return _parse_score(out, default=0.5)


def score_answer_relevance(question: str, answer: str) -> float:
    """0-1: ¿La respuesta contesta la pregunta?"""
    prompt = f"""Eres un evaluador estricto. Mide si la respuesta contesta lo que se pregunta.

PREGUNTA: {question}

RESPUESTA:
{answer}

¿La respuesta aborda directamente la pregunta? Responde SOLO con un número entre 0.0 y 1.0:
  1.0 = contesta perfectamente
  0.5 = responde tangencialmente o parcialmente
  0.0 = no tiene nada que ver con la pregunta

Si la respuesta dice "no sé" o "no tengo información" y la pregunta es sobre algo que SÍ debería contestar el sistema, es un score bajo (rechazo legítimo pero no útil).

SCORE:"""
    out = call_judge(prompt)
    return _parse_score(out, default=0.5)


def score_context_precision(question: str, contexts: list[str]) -> float:
    """0-1: ¿Los chunks retrieved son relevantes? Considera el ranking."""
    if not contexts:
        return 0.0
    chunks_str = "\n".join(f"[Chunk {i+1}]\n{c[:300]}\n" for i, c in enumerate(contexts[:5]))
    prompt = f"""Eres un evaluador de un sistema de retrieval. Mide la calidad del ranking de chunks.

PREGUNTA: {question}

CHUNKS RETRIEVED (en orden de ranking, chunk 1 = más relevante):
{chunks_str}

Para cada chunk, decide si contiene información relevante para responder la pregunta (SÍ/NO). Luego calcula la "precision@k" promedio ponderada: chunks relevantes en posiciones altas valen más.

Responde SOLO con un número entre 0.0 y 1.0:
  1.0 = todos los chunks son relevantes y bien rankeados
  0.5 = mix de relevantes e irrelevantes
  0.0 = ningún chunk es relevante

SCORE:"""
    out = call_judge(prompt)
    return _parse_score(out, default=0.5)


def score_context_recall(question: str, ground_truth: str, contexts: list[str]) -> float:
    """0-1: ¿El contexto contiene lo necesario para producir el ground truth?"""
    ctx = "\n---\n".join(contexts[:5])
    prompt = f"""Eres un evaluador. Mide si el contexto recuperado contiene la información necesaria para responder correctamente.

PREGUNTA: {question}

CONTEXTO RETRIEVED:
{ctx}

RESPUESTA CORRECTA ESPERADA (ground truth):
{ground_truth}

¿El contexto contiene la información necesaria para producir la respuesta correcta? Responde SOLO con un número entre 0.0 y 1.0:
  1.0 = el contexto tiene todo lo necesario
  0.5 = el contexto tiene parte
  0.0 = el contexto no tiene la información

SCORE:"""
    out = call_judge(prompt)
    return _parse_score(out, default=0.5)


def _parse_score(text: str, default: float = 0.5) -> float:
    """Extrae un número 0-1 del texto de salida del juez."""
    if not text or text.startswith("[ERROR"):
        return default
    # Buscar primer número decimal en el texto
    match = re.search(r"(\d+\.?\d*)", text)
    if not match:
        return default
    try:
        val = float(match.group(1))
        # Si parece ser 0-10 o 0-100, normalizar
        if val > 1.0 and val <= 10:
            val = val / 10.0
        elif val > 10:
            val = val / 100.0
        return max(0.0, min(1.0, val))
    except (ValueError, TypeError):
        return default


# ─── Eval set ──────────────────────────────────────────────────────
def evaluate_item(item: dict) -> dict:
    """Evalúa un (question, answer, contexts, ground_truth) con las 4 métricas."""
    q = item["question"]
    a = item["answer"]
    ctxs = item.get("contexts", [])
    gt = item.get("ground_truth", "")

    # Faithfulness y context_* solo si hay contextos
    scores = {
        "faithfulness": score_faithfulness(q, a, ctxs) if ctxs else None,
        "answer_relevance": score_answer_relevance(q, a),
        "context_precision": score_context_precision(q, ctxs) if ctxs else None,
        "context_recall": score_context_recall(q, gt, ctxs) if ctxs else None,
    }
    return scores


def evaluate_dataset(items: list[dict]) -> dict:
    """Evalúa un dataset completo y devuelve promedios."""
    all_scores = {"faithfulness": [], "answer_relevance": [],
                  "context_precision": [], "context_recall": []}
    per_item = []

    for i, item in enumerate(items, 1):
        print(f"  [{i}/{len(items)}] {item['question'][:55]}...")
        s = evaluate_item(item)
        per_item.append({"question": item["question"], "scores": s})
        for k, v in s.items():
            if v is not None:
                all_scores[k].append(v)

    averages = {k: (sum(v) / len(v) if v else None) for k, v in all_scores.items()}
    return {"averages": averages, "per_item": per_item}


# ─── CLI ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True,
                        help="JSONL con {question, answer, contexts, ground_truth}")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    items = []
    with open(args.input) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    print(f"Evaluando {len(items)} items con {OLLAMA_MODEL} como juez...")
    result = evaluate_dataset(items)

    print("\n" + "=" * 50)
    print("RESULTADOS")
    print("=" * 50)
    for k, v in result["averages"].items():
        if v is not None:
            print(f"  {k:<22} {v:.3f}")
        else:
            print(f"  {k:<22} N/A")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Detalle guardado en {args.output}")


if __name__ == "__main__":
    main()
