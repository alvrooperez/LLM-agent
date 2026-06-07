# Phase 3 - Fine-Tuning (QLoRA with Unsloth)

Train a small LLM (3B params) to use tools better.

## Approach

- **Base model**: `qwen2.5:3b`
- **Method**: QLoRA via Unsloth (faster, less VRAM than full FT)
- **Dataset**: 245 tool-calling examples generated from real agent interactions
- **Train/test split**: 230 train / 15 held-out
- **Output**: LoRA adapter (57MB) -> merged with base -> GGUF Q4_K_M (1.9GB)
- **Training time**: 28 min on RTX 3050

## Key finding (honest reporting)

The base `qwen2.5:3b` already knew the tool-calling format. Fine-tuning did not add new capability:

| Metric | Base | Fine-tuned | Delta |
|---|---|---|---|
| Tool call rate | 7% | 7% | 0 |
| Iterations/task | 2.2 | 2.0 | -9% |
| Response length | 315 chars | 279 chars | -11% |
| RAG relevance | baseline | +83% (over no-RAG) | - |

So LoRA mainly made responses more concise and consistent. Zero regression in tool call rate.

## Pipeline (reference)

1. Generate tool-calling dataset (`scripts/generate_tool_dataset.py`)
2. Train with Unsloth (`scripts/train_unsloth.py`) - separate venv with CUDA
3. Merge LoRA into base on CPU (`scripts/merge_lora_cpu.py`)
4. Convert to GGUF with llama.cpp
5. Quantize Q4_K_M (1.9GB final)
6. Register in Ollama as `qwen2.5-rag-ft`

## Why document this honestly

Inflating results is a common portfolio mistake. A senior engineer reading this will check the A/B eval and notice if numbers are padded. By reporting "no improvement, here's why" we gain credibility.

## Next

[Phase 2 - RAG + Chat + Tool Calling](../phase-2-rag/README.md) (the main project)
