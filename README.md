# AI Engineering Portfolio

> Self-hosted LLM agent on a laptop GPU - inference, RAG, fine-tuning, tool calling. All local, no cloud APIs, MIT-licensed.

A complete **AI agent** system that runs on a **4GB VRAM laptop GPU** (RTX 3050).

- **Inference**: Ollama + `qwen2.5:3b` (Q4_K_M, 1.9GB) - 68 tok/s
- **RAG**: Qdrant + sentence-transformers - **+83% answer relevance** vs no-RAG
- **Fine-tuning**: Unsloth LoRA on 230 examples - merged to GGUF Q4_K_M
- **Tool calling**: 6 real tools, 80-line agent loop, no LangChain
- **Multi-tool chaining**: 5/5 - agent plans and executes 2-3 tools in parallel
- **Streaming**: real tokens from Ollama (no fake delays)
- **Web UI**: Claude-like SPA with dark/light theme, multi-conversation
- **Security**: API key auth, rate limiting, CORS, XSS escape, input validation
- **89 pytest tests** with a regression runner that catches metric drift
- **One-command setup**: `docker compose up` starts the entire stack

## Live demo

After `setup.bat` (Windows) or `./setup.sh` (Linux/Mac):

| URL | What |
|---|---|
| http://localhost:8090 | Chat with the agent |
| http://localhost:8090/architecture | Interactive system diagram |
| http://localhost:8090?compare=1 | Compare base vs fine-tuned (Ctrl+M) |
| http://localhost:11434 | Ollama API |
| http://localhost:6333 | Qdrant API |
| http://localhost:8000 | RAG API |

## Quick start

### Windows
```
setup.bat                 # check + start everything
setup.bat bootstrap       # also populate Qdrant with knowledge base
```

### Linux / Mac
```
./setup.sh                # check + start everything
./setup.sh bootstrap      # also populate Qdrant with knowledge base
```

After setup, open http://localhost:8090.

## Architecture

```
                  Browser
                     |
                     v
        +--------------------------+
        |  Chat App (FastAPI :8090)|
        |  - SPA (vanilla JS)      |
        |  - SSE streaming         |
        |  - Tool cards            |
        +-----------+--------------+
                    |
        +-----------v--------------+
        |  Agent Loop (80 lines)  |
        |  run_agent_streaming()  |
        +---+------+--------+------+
            |      |        |
   +--------+  +---v----+  +v-------+
   |        |  | 6 Tools|  | Ollama |
   |        |  | - RAG |  | :11434 |
   |        |  | - GPU |  | qwen2.5|
   |        |  | - Qdr |  |   :3b   |
   |        |  | - PDF |  |  -FT   |
   |        |  +-------+  +--------+
   |        |
+--v---+ +---v----+
| Rag  | | Qdrant |
| API  | |  :6333 |
| :8000| +--------+
+------+
```

Full interactive diagram: http://localhost:8090/architecture

## Project structure

```
ai-engineer-portfolio/
|-- README.md                       <- you are here
|-- LICENSE                         <- MIT
|-- docker-compose.yml              <- one-command full stack
|-- setup.bat / setup.sh            <- cross-platform setup
|-- GITHUB_PUSH_INSTRUCTIONS.md    <- how to push to your own GitHub
|-- .gitignore
|
|-- app/                            <- THE PROJECT. The main code lives here.
|   |-- README.md                   <- detailed docs for the app
|   |-- Dockerfile
|   |-- docker-compose.yml
|   |-- requirements.txt
|   |-- scripts/                    <- backend (chat_app.py, agent loop, tools, evals)
|   |-- tests/                      <- 89 pytest tests
|   |-- data/                       <- eval results, generated PDFs (PDFs gitignored)
|   `-- slides/                     <- PPTX generation (PptxGenJS)
|
|-- infrastructure/                 <- Ollama docker-compose (used by root docker-compose.yml)
|   `-- docker-compose.yml
|
`-- docs/                           <- documentation
    |-- architecture.md
    |-- screenshots/                <- (empty for now)
    `-- development-notes/          <- process notes (setup, fine-tuning, agent design)
        |-- 00-setup.md
        |-- 03-finetuning.md
        `-- 04-agent-design.md
```

**Where to start**:
- **If you want to USE the app**: `app/README.md` has quick start, tools list, evals
- **If you want to UNDERSTAND the system**: `app/scripts/` (80-line agent loop) + `app/scripts/chat_app.py` (FastAPI backend)
- **If you want to know HOW it was built**: `docs/development-notes/`

## Tests

```bash
cd phase-2-rag
python -m pytest tests/ -v          # 89 tests
python scripts/regression_test.py   # catches metric drift
```

Latest run: 89/89 passing.

## Highlights (what this project demonstrates)

1. **Engineering under real constraints** (4GB VRAM, no cloud)
2. **Defensible decisions** with data, not vibes (every choice has a tested "why")
3. **Honest reporting**: LoRA fine-tuning on 230 examples did not add new capability (base model already knew tool calling) - documented, not hidden
4. **Thread-safety by design** (contextvars, not monkey-patching)
5. **89 tests** with regression runner that catches metric drift
6. **Production-ready** observability (JSONL with per-tool timing)
7. **Security from day 1**: API key, rate limit, CORS, XSS escape

## License

MIT - see [LICENSE](LICENSE).
