"""
Merge LoRA → modelo bf16 → GGUF Q4_K_M → Ollama.

Estrategia mixta: usar GPU para los layers críticos y CPU para el resto.
"""
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# No forzamos CUDA_VISIBLE_DEVICES — dejamos GPU visible para que la use si puede

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_PATH = "data/finetune/full_model"
MERGED_DIR = "data/finetune/merged_full"
OFFLOAD_DIR = "data/finetune/offload_tmp"

print("=== Merge LoRA → HF model completo (CPU + GPU mixta con offload) ===\n")

# ── 1. Cargar base con device_map automático + disk offload ─────────
print(f"[1/4] Cargando base {BASE_MODEL} con disk offload...")
print("(GPU: 3GB para layers iniciales; resto a disco y se carga bajo demanda)")

Path(OFFLOAD_DIR).mkdir(parents=True, exist_ok=True)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype="bfloat16",
    device_map="auto",
    offload_folder=OFFLOAD_DIR,
    offload_state_dict=True,
    low_cpu_mem_usage=True,
    max_memory={0: "3GB", "cpu": "10GB"},
)

# Ver dónde quedó cada cosa
device_summary = {}
for name, p in model.named_parameters():
    dev = str(p.device)
    device_summary[dev] = device_summary.get(dev, 0) + p.numel()
print(f"  Distribución params por device: {device_summary}")
print(f"  Total params: {sum(p.numelel() for p in model.parameters() if p.requires_grad) / 1e9:.2f}B" if False else f"  (skip)")

# ── 2. Aplicar LoRA ─────────────────────────────────────────────────────
print(f"\n[2/4] Aplicando LoRA desde {ADAPTER_PATH}...")
model = PeftModel.from_pretrained(model, ADAPTER_PATH)
print("  LoRA aplicado")

# ── 3. Merge ────────────────────────────────────────────────────────────
print("\n[3/4] Merge + unload...")
model = model.merge_and_unload()
print("  Merge completo")

# ── 4. Guardar ──────────────────────────────────────────────────────────
print(f"\n[4/4] Guardando en {MERGED_DIR}...")
Path(MERGED_DIR).mkdir(parents=True, exist_ok=True)
model.save_pretrained(MERGED_DIR, safe_serialization=True, max_shard_size="2GB")
tokenizer.save_pretrained(MERGED_DIR)

print("\nArchivos guardados:")
total_size = 0
for f in Path(MERGED_DIR).glob("*"):
    size_gb = f.stat().st_size / 1e9
    total_size += size_gb
    print(f"  {f.name}: {size_gb:.2f}GB")
print(f"\n  Total: {total_size:.2f}GB")
print(f"\n✓ Modelo merged en {MERGED_DIR}")