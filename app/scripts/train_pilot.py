"""Pilot fine-tuning con QLoRA en Qwen 2.5 3B.

NOTA sobre el entorno:
- Python 3.14 + transformers 5.x tiene incompatibilidades con Qwen2ForCausalLM
- El script fue TESTEADO con Python 3.12 + transformers 4.47 + trl<0.12
- Para usar en Windows, crear venv con Python 3.12:
    py -3.12 -m venv .venv-train
    .venv-train\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu124
    .venv-train\Scripts\python.exe -m pip install "transformers==4.47.0" "trl<0.12" "peft<0.14" bitsandbytes accelerate datasets

- Alternativa limpia: contenedor Docker Linux con todo preinstalado (recomendado).

Uso:
  python scripts/train_pilot.py --n-examples 25
  python scripts/train_pilot.py --n-examples 25 --epochs 2
"""
import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig


def load_messages(path, n):
    items = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def format_for_training(example, tokenizer):
    return tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-examples", type=int, default=25)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--output", type=str, default="data/finetune/pilot_model")
    args = parser.parse_args()

    print(f"=== Pilot fine-tuning ===")
    print(f"  Ejemplos: {args.n_examples}, Epochs: {args.epochs}, LR: {args.lr}")
    print(f"  LoRA: r={args.lora_r}, alpha={args.lora_alpha}")
    print(f"  Output: {args.output}")

    if not torch.cuda.is_available():
        print("ERROR: CUDA no disponible.")
        sys.exit(1)
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    print("\nCargando tokenizer...")
    model_name = "Qwen/Qwen2.5-3B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Cargando {args.n_examples} ejemplos...")
    items = load_messages(Path("data/finetune/train.jsonl"), args.n_examples)
    texts = [format_for_training(ex, tokenizer) for ex in items]
    dataset = Dataset.from_dict({"text": texts})
    print(f"  Dataset: {len(dataset)} ejemplos")

    print("Configurando 4-bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    print("Cargando modelo en 4-bit...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
        attn_implementation="eager",
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    print("Configurando LoRA...")
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    sft_config = SFTConfig(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        logging_steps=5,
        save_strategy="no",
        fp16=True,
        max_grad_norm=1.0,
        report_to="none",
        dataset_text_field="text",
        packing=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    print("\n=== ENTRENANDO ===")
    trainer.train()

    adapter_path = Path(args.output) / "adapter"
    print(f"\nGuardando adapter en {adapter_path}...")
    trainer.model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)

    merged_path = Path(args.output) / "merged"
    print(f"Merging -> {merged_path}...")
    merged_model = trainer.model.merge_and_unload()
    merged_model.save_pretrained(merged_path, safe_serialization=True)
    tokenizer.save_pretrained(merged_path)

    print(f"\n✓ Pilot entrenado. Adapter: {adapter_path}, Merged: {merged_path}")


if __name__ == "__main__":
    main()
