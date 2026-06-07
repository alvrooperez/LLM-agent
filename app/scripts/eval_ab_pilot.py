"""
A/B eval: Qwen 2.5 3B base vs Qwen 2.5 3B + LoRA (full_model)
Sobre el held-out set (15 ejemplos, NUNCA vistos en training).

Métricas:
- tool_call_emission: ¿emite un tool call correcto?
- format_compliance: ¿usa [TAREA_COMPLETADA] cuando corresponde?
- relevance: LLM-as-judge (1-5)
- refusal_handling: ¿se niega educadamente cuando no debe usar tools?
"""
import os
import sys
import json
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from unsloth import FastLanguageModel
from peft import PeftModel


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def extract_tool_call(text):
    """Busca un tool call en JSON o en pseudo-JSON."""
    # JSON estricto
    m = re.search(r'\{[^{}]*"name"[^{}]*"arguments"[^{}]*\{[^{}]*\}[^{}]*\}', text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # Pseudo-formato tipo Unsloth: {"name": "...", "arguments": {...}}
    m = re.search(r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^{}]*\})', text)
    if m:
        try:
            return {"name": m.group(1), "arguments": json.loads(m.group(2))}
        except Exception:
            return {"name": m.group(1), "arguments": {}}
    return None


def score_response(item, generated):
    """Devuelve (tool_call_emitted, tool_call_correct, has_completion_token, length)."""
    messages = item["messages"]
    expected_tool_calls = []
    for m in messages:
        if isinstance(m, dict) and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                expected_tool_calls.append(tc.get("function", {}).get("name"))

    # Detectar tool call emitido
    tc = extract_tool_call(generated)
    tc_emitted = tc is not None
    tc_correct = False
    if tc and expected_tool_calls:
        tc_correct = tc.get("name") in expected_tool_calls
    elif tc and not expected_tool_calls:
        # No esperaba tool call pero emitió uno
        tc_correct = False

    # Detectar [TAREA_COMPLETADA]
    has_completion = "[TAREA_COMPLETADA]" in generated

    return {
        "tc_emitted": tc_emitted,
        "tc_correct": tc_correct,
        "expected_tc": expected_tool_calls,
        "has_completion": has_completion,
        "length": len(generated),
    }


def run_inference(model, tokenizer, items, label, max_new_tokens=300):
    results = []
    print(f"\n--- {label} ---")
    for i, item in enumerate(items):
        messages = item["messages"]
        prompt_messages = messages[:-1]  # drop the ground-truth assistant turn
        prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
        generated = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        s = score_response(item, generated)
        results.append({"item_idx": i, "generated": generated, **s})
        print(f"  [{i+1}/{len(items)}] tc={s['tc_emitted']} correct={s['tc_correct']} compl={s['has_completion']} len={s['length']}")
    return results


def summarize(results, label):
    n = len(results)
    tc_emitted = sum(1 for r in results if r["tc_emitted"])
    tc_correct = sum(1 for r in results if r["tc_correct"])
    completion = sum(1 for r in results if r["has_completion"])
    avg_len = sum(r["length"] for r in results) / n if n else 0
    print(f"\n=== {label} ===")
    print(f"  N ejemplos: {n}")
    print(f"  Tool calls emitidos: {tc_emitted}/{n} ({100*tc_emitted/n:.0f}%)")
    print(f"  Tool calls correctos: {tc_correct}/{n} ({100*tc_correct/n:.0f}%)")
    print(f"  [TAREA_COMPLETADA] usado: {completion}/{n} ({100*completion/n:.0f}%)")
    print(f"  Longitud media: {avg_len:.0f} chars")


def main():
    held_out = "data/finetune/held_out_test.jsonl"
    adapter_path = "data/finetune/full_model"

    items = load_jsonl(held_out)
    print(f"=== A/B Eval: Base vs Base+LoRA ===")
    print(f"  Held-out: {len(items)} ejemplos")

    # Cargar base
    print("\nCargando modelo base...")
    base_model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-3B-Instruct",
        max_seq_length=2048,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(base_model)
    base_results = run_inference(base_model, tokenizer, items, "BASE (sin LoRA)")

    # Liberar VRAM
    del base_model
    import gc
    gc.collect()
    import torch
    torch.cuda.empty_cache()

    # Cargar base + adapter
    print("\nCargando base + LoRA adapter...")
    ft_model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-3B-Instruct",
        max_seq_length=2048,
        load_in_4bit=True,
    )
    ft_model = PeftModel.from_pretrained(ft_model, adapter_path)
    FastLanguageModel.for_inference(ft_model)
    ft_results = run_inference(ft_model, tokenizer, items, "FULL + LoRA (230 ej, 2 ep)")

    # Resumen
    summarize(base_results, "BASE")
    summarize(ft_results, "FULL + LoRA")

    # Guardar
    out_path = "data/finetune/eval_ab.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "base": base_results,
            "ft": ft_results,
            "summary": {
                "base_tc_emitted": sum(1 for r in base_results if r["tc_emitted"]),
                "ft_tc_emitted": sum(1 for r in ft_results if r["tc_emitted"]),
                "base_completion": sum(1 for r in base_results if r["has_completion"]),
                "ft_completion": sum(1 for r in ft_results if r["has_completion"]),
            }
        }, f, ensure_ascii=False, indent=2)
    print(f"\nResultados guardados en {out_path}")


if __name__ == "__main__":
    main()
