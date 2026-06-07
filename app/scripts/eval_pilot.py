"""
Pilot eval: load Qwen 2.5 3B + LoRA adapter, run on held-out set, show outputs.
Compare FT model vs base (qualitative).
"""
import os
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from unsloth import FastLanguageModel
from datasets import load_dataset


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def format_for_inference(messages):
    """Format messages as a prompt ending in assistant turn (for generation)."""
    return messages[:-1]  # drop the assistant turn; we'll let the model generate it


def main():
    held_out_path = "data/finetune/held_out_test.jsonl"
    adapter_path = "data/finetune/pilot_model"

    n_examples = int(os.environ.get("N", "5"))

    print(f"=== Pilot Eval: Qwen 2.5 3B + LoRA ===\n")
    print(f"  Held-out: {held_out_path}")
    print(f"  Adapter: {adapter_path}")
    print(f"  N: {n_examples}\n")

    # Load held-out
    items = load_jsonl(held_out_path)[:n_examples]
    print(f"  {len(items)} ejemplos cargados\n")

    # Load model with adapter
    print("Cargando base model + LoRA adapter...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-3B-Instruct",
        max_seq_length=2048,
        load_in_4bit=True,
    )
    # Apply adapter
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, adapter_path)
    FastLanguageModel.for_inference(model)  # 2x faster inference
    print("  Adapter cargado. Inferencia lista.\n")

    # Run on held-out
    for i, item in enumerate(items):
        print(f"\n{'='*70}")
        print(f"EJEMPLO {i+1}/{len(items)}")
        print(f"{'='*70}")

        messages = item["messages"]
        # The last message is the ground-truth assistant response
        # Use all but the last as input, generate the assistant response
        prompt_messages = messages[:-1]
        ground_truth = messages[-1]["content"]

        # Print user query
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        print(f"\nUSER QUERY:\n  {user_msg[:200]}...")

        # Print expected tool calls if any
        if "tool_calls" in item.get("messages", [{}])[-1] or any("tool_calls" in m for m in messages if isinstance(m, dict)):
            for m in messages:
                if isinstance(m, dict) and m.get("tool_calls"):
                    for tc in m["tool_calls"]:
                        fn = tc.get("function", {})
                        args = json.loads(fn.get("arguments", "{}")) if isinstance(fn.get("arguments"), str) else fn.get("arguments", {})
                        print(f"  EXPECTED tool_call: {fn.get('name', '?')}({args})")

        # Format and generate
        prompt_text = tokenizer.apply_chat_template(
            prompt_messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)

        outputs = model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=False,  # greedy for reproducibility
            temperature=1.0,
            pad_token_id=tokenizer.eos_token_id,
        )

        generated = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

        print(f"\nGROUND TRUTH:\n  {ground_truth[:200]}...")
        print(f"\nMODEL OUTPUT:\n  {generated[:300]}...")

    print(f"\n{'='*70}")
    print("✓ Pilot eval completo")


if __name__ == "__main__":
    main()
