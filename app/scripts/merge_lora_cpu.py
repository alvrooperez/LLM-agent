"""
Merge LoRA → modelo completo bf16 en CPU puro.
Lento pero robusto — no necesita GPU, no necesita tricks de offload.

Modelo 3B en bf16 = 6GB en RAM. Tienes 16GB, va bien.
"""
import os
import sys
import gc
import shutil
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# NO forzamos CUDA_VISIBLE_DEVICES — dejamos GPU visible para que triton no falle
# Solo evitamos usarla con .to("cpu") explícito

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_PATH = "data/finetune/full_model"
MERGED_DIR = "data/finetune/merged_full"

print("=== Merge LoRA → HF model completo (CPU puro) ===\n")
print("Cargando base en CPU (6GB de RAM, 1-2 min)...")

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    device_map={"": "cpu"},  # explícitamente todo a CPU
)
model.eval()  # desactiva dropout, importante para merge
print(f"  Base cargado: {sum(p.numel() for p in model.parameters()) / 1e9:.2f}B params")

print(f"\n[2/4] Aplicando LoRA...")
model = PeftModel.from_pretrained(model, ADAPTER_PATH)
print("  LoRA aplicada")

print(f"\n[3/4] Merge + unload (1-2 min)...")
model = model.merge_and_unload()
print("  Merge completo")

print(f"\n[4/4] Guardando en {MERGED_DIR}...")
Path(MERGED_DIR).mkdir(parents=True, exist_ok=True)
model.save_pretrained(MERGED_DIR, safe_serialization=True, max_shard_size="2GB")
tokenizer.save_pretrained(MERGED_DIR)

print("\nArchivos guardados:")
total = 0
for f in sorted(Path(MERGED_DIR).glob("*")):
    if f.is_file():
        size_gb = f.stat().st_size / 1e9
        total += size_gb
        print(f"  {f.name}: {size_gb:.2f}GB")
print(f"  Total: {total:.2f}GB")
print(f"\n✓ Modelo merged en {MERGED_DIR}")

# Limpiar RAM
del model
gc.collect()
print("\nRAM liberada.")