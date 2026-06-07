"""
Pilot fine-tuning con Unsloth en Qwen 2.5 3B.

Unsloth se encarga automaticamente de:
- 4-bit quantization (bitsandbytes)
- LoRA adapters (peft)
- Gradient checkpointing
- Flash Attention / Xformers

Setup verificado: Python 3.12, torch 2.11+cu128, unsloth 2026.6.1
"""
import os
import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer, SFTConfig


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    n_examples = int(os.environ.get("N_EXAMPLES", "25"))
    epochs = int(os.environ.get("EPOCHS", "2"))
    output_dir = os.environ.get("OUTPUT_DIR", "data/finetune/pilot_model")
    train_path = "data/finetune/train.jsonl"

    print(f"=== Pilot Unsloth ===")
    print(f"  N ejemplos: {n_examples}")
    print(f"  Epochs: {epochs}")
    print(f"  Output: {output_dir}")

    # Cargar modelo con Unsloth
    print("\nCargando Qwen 2.5 3B (4-bit, optimizado Unsloth)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-3B-Instruct",
        max_seq_length=2048,
        load_in_4bit=True,
    )

    # LoRA
    print("Configurando LoRA r=8 alpha=16...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # Cargar dataset
    print(f"\nCargando {n_examples} ejemplos de {train_path}...")
    items = load_jsonl(train_path)[:n_examples]
    print(f"  {len(items)} cargados")

    # Convertir messages a texto con chat template
    print("Aplicando chat template...")
    texts = [tokenizer.apply_chat_template(item["messages"], tokenize=False, add_generation_prompt=False) for item in items]
    dataset = Dataset.from_dict({"text": texts})

    # Mostrar un ejemplo
    print(f"\nEjemplo de texto formateado (primeros 300 chars):")
    print(f"  {texts[0][:300]}...")
    print()

    # SFTTrainer
    print("Creando SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            learning_rate=1e-5,
            warmup_ratio=0.1,
            lr_scheduler_type="cosine",
            logging_steps=2,
            save_strategy="no",
            bf16=True,
            fp16=False,
            max_grad_norm=1.0,
            report_to="none",
            dataset_text_field="text",
            max_seq_length=2048,
            packing=False,
        ),
    )

    print("\n=== ENTRENANDO ===")
    trainer.train()

    # Guardar
    print(f"\nGuardando modelo en {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Export GGUF para Ollama (opcional — saltar si SKIP_GGUF=1 o ya hay GGUF previo)
    skip_gguf = os.environ.get("SKIP_GGUF", "0") == "1"
    if not skip_gguf:
        gguf_dir = Path(output_dir) / "gguf"
        print(f"Exportando a GGUF (para Ollama) en {gguf_dir}...")
        try:
            model.save_pretrained_gguf(str(gguf_dir), tokenizer, quantization_method="q4_k_m")
            print("  GGUF exportado")
        except Exception as e:
            print(f"  GGUF export falló (no crítico): {e}")
    else:
        print("GGUF export saltado (SKIP_GGUF=1)")

    print(f"\n✓ Pilot entrenado. Modelo en {output_dir}")


if __name__ == "__main__":
    main()
