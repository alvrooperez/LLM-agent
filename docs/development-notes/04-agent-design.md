# Phase 4 - Tool-Calling Agent

LLM agent that can use real tools. Detects when it needs information and calls functions explicitly.

## Architecture

80-line agent loop, no LangChain:

```
User query
   |
   v
Ollama (with tools schema)
   |
   v
Parse response
   |
   +-- tool_calls present --> Execute tools, append results, loop
   |
   +-- no tool_calls --> Final response, return
```

## 6 tools

| Tool | Backend |
|---|---|
| `search_docs` | RAG API :8000 |
| `list_models` | Ollama :11434 |
| `get_gpu_stats` | nvidia-smi |
| `get_collection_info` | Qdrant :6333 |
| `plot_metric` | matplotlib |
| `write_document` | ReportLab (PDF) |

See `phase-2-rag/scripts/tools/implementations.py` for the actual code.

## Why no LangChain

- 80 lines is easier to read than 800 lines of framework
- Full control over the tool call format (no surprises)
- No transitive dependencies
- No version-locking to a fast-moving framework

## Multi-tool chaining

The agent plans and executes 2-3 tools in a single iteration without re-prompting. Eval: 5/5 tasks pass.

## E2E results

4/4 multi-step tasks completed:
- "Estado del sistema" -> get_gpu_stats + get_collection_info + list_models
- "Genera informe + estado" -> write_document + get_gpu_stats
- "Lista modelos y explica" -> list_models + search_docs
- ... and one more

## Next

[Phase 2 README](../phase-2-rag/README.md) has the live code, tests, and demo.
