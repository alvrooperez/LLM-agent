"""
Export LoRA → GGUF Q4_K_M usando Unsloth directamente desde el adapter.

Unsloth tiene gguf export que funciona con Qwen 2.5 y maneja la conversión
sin necesidad de compilar llama-quantize por separado.

Estrategia: cargar base + adapter, hacer merge, exportar a GGUF.
"""
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

print("=== Export LoRA → GGUF Q4_K_M (vía Unsloth) ===\n")

from unsloth import FastLanguageModel
from peft import PeftModel

# Cargamos el base con Unsloth
print("[1/3] Cargando base + LoRA...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-3B-Instruct",
    max_seq_length=2048,
    load_in_4bit=True,
)
# Aplicar la LoRA entrenada
model = PeftModel.from_pretrained(model, "data/finetune/full_model")
print("  Base + LoRA cargados")

# Merge de LoRA → modelo completo (4bit → 16bit)
print("\n[2/3] Merge LoRA...")
model = model.merge_and_unload()
print("  Merge completo")

# Exportar a GGUF Q4_K_M
print("\n[3/3] Exportando a GGUF Q4_K_M...")
gguf_dir = Path("data/finetune/full_model_q4_gguf")
gguf_dir.mkdir(parents=True, exist_ok=True)

# save_pretrained_gguf hace: merge 4bit → 16bit → GGUF → quantize
model.save_pretrained_gguf(
    str(gguf_dir),
    tokenizer,
    quantization_method="q4_k_m",
)

print(f"\n✓ GGUF exportado en {gguf_dir}")
print("\nArchivos:")
for f in sorted(gguf_dir.glob("*")):
    if f.is_file():
        size_mb = f.stat().st_size / 1e6
        print(f"  {f.name}: {size_mb:.1f}MB")