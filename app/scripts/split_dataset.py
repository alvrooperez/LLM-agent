"""
Split del dataset: 15 ejemplos van a held-out test, el resto a training.

El held-out NUNCA se usa para entrenar. Sirve para:
  1. Detectar overfitting (modelo que solo funciona en lo que vio)
  2. Detectar catastrophic forgetting (si la eval general empeora)
  3. Comparar base vs fine-tuned en datos no vistos

Output:
  data/finetune/train.jsonl       (~230 ejemplos)
  data/finetune/held_out_test.jsonl (15 ejemplos, estratificados)
"""
import json
import random
from pathlib import Path
from collections import Counter

INPUT = Path("data/finetune/tool_calling_dataset.jsonl")
TRAIN_OUT = Path("data/finetune/train.jsonl")
HELD_OUT_OUT = Path("data/finetune/held_out_test.jsonl")

HELD_OUT_SIZE = 15
SEED = 42


def categorize(ex):
    n_tools = sum(1 for m in ex["messages"] if m.get("content", "").startswith("<tool_call>"))
    if n_tools == 0:
        return "direct"
    elif n_tools == 1:
        return "1-tool"
    elif n_tools <= 3:
        return "2-3-tools"
    else:
        return "4+-tools"


def main():
    random.seed(SEED)

    # Cargar
    with open(INPUT, encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]

    print(f"Total cargados: {len(data)}")

    # Estratificar por categoría para que el held-out sea representativo
    by_cat = {}
    for ex in data:
        cat = categorize(ex)
        by_cat.setdefault(cat, []).append(ex)

    for cat, items in by_cat.items():
        random.shuffle(items)
        print(f"  {cat}: {len(items)}")

    # Distribuir held-out proporcionalmente
    held_out = []
    train = []
    distribution = {
        "direct": 4,
        "1-tool": 5,
        "2-3-tools": 4,
        "4+-tools": 2,
    }

    for cat, n in distribution.items():
        items = by_cat.get(cat, [])
        take = min(n, len(items))
        held_out.extend(items[:take])
        train.extend(items[take:])

    # Mezclar train
    random.shuffle(train)

    # Guardar
    with open(TRAIN_OUT, "w", encoding="utf-8") as f:
        for ex in train:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    with open(HELD_OUT_OUT, "w", encoding="utf-8") as f:
        for ex in held_out:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nTrain:        {len(train)} -> {TRAIN_OUT}")
    print(f"Held-out:     {len(held_out)} -> {HELD_OUT_OUT}")
    print(f"Distribucion held-out: {Counter(categorize(e) for e in held_out)}")

    # Mostrar los held-out para revision
    print("\n=== Held-out test set (NO entrenar con esto) ===")
    for i, ex in enumerate(held_out, 1):
        user_msg = ex["messages"][1]["content"]
        n_tools = sum(1 for m in ex["messages"] if m.get("content", "").startswith("<tool_call>"))
        print(f"\n[{i}] {user_msg[:80]}... (tools: {n_tools})")


if __name__ == "__main__":
    main()
