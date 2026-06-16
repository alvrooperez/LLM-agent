# AI Engineering Portfolio — the app

This is the active project. ~90% of the codebase lives here.

## Quick start

### With Docker (recommended)
From the repo root:
```bash
docker compose up -d
docker compose --profile bootstrap run --rm rag-bootstrap  # populate Qdrant
```
Open http://localhost:8090 and log in with `admin` / `admin123`.

### Local (without Docker)
```bash
# Assumes Ollama + Qdrant already running on host
pip install -r requirements.txt
python -m uvicorn scripts.chat_app:app --reload
```
Open http://localhost:8090. The first time, login with `admin` / `admin123`
(created automatically by `scripts/auth.py:ensure_users_file()`).
**Change the password in production** (see [`docs/AUTH.md`](docs/AUTH.md)).

## What is here

| Path | What |
|---|---|
| `scripts/chat_app.py` | FastAPI backend with SSE streaming, JWT auth, rate limiting |
| `scripts/auth.py` | User mgmt + scrypt hashing + JWT (HS256) + dependencies |
| `scripts/chat_static/index.html` | Claude-like SPA (login screen, dark/light, multi-conversation, stop button, compare) |
| `scripts/chat_static/architecture.html` | Interactive system diagram |
| `scripts/agent/run.py` | 80-line agent loop with tool calling + streaming + early-stop |
| `scripts/tools/registry.py` | `@tool` decorator and `TOOL_REGISTRY` |
| `scripts/tools/implementations.py` | 6 tools with real backends |
| `scripts/obs.py` | Observability → JSONL (per-tool timing, VRAM, errors) |
| `tests/` | 89 unit + 4 E2E pytest tests |
| `docs/AUTH.md` | User management, JWT details, adding users |
| `docs/SECURITY.md` | Security model + threat analysis |

## Tools (6)

| Tool | Backend | What it does |
|---|---|---|
| `search_docs` | RAG API :8000 | Vector search in knowledge base |
| `list_models` | Ollama :11434 | List available LLM models |
| `get_gpu_stats` | nvidia-smi | VRAM, utilization, temperature |
| `get_collection_info` | Qdrant :6333 | Collection metadata |
| `plot_metric` | matplotlib | Generate PNG charts from CSV |
| `write_document` | ReportLab | Generate PDF reports (4 templates) |

## Evaluations

| Eval | Result |
|---|---|
| Multi-tool chaining (5 tasks) | 5/5 PASS |
| Tool call rate (A/B) | base 7% / FT 7% (no regression) |
| Load test (4 concurrent) | 0% errors, p50 10s server |
| RAG answer relevance | +83% vs no-RAG baseline |
| RAG latency overhead | +11s (+121%) — counterbalanced by agent early-stop |
| Regression runner | catches metric drift |

## Tests

```bash
# Unit tests (default, no server needed, ~1 min)
python -m pytest tests/

# E2E (requires server on :8090 + Ollama running, ~3 min)
python -m pytest tests/ -m e2e

# All
python -m pytest tests/ -m ""
```

89 unit + 4 E2E = 93 tests. CI runs only the unit tests (`.github/workflows/tests.yml`).

## Authentication

JWT-based login with scrypt-hashed passwords. See [`docs/AUTH.md`](docs/AUTH.md) for:

- Default credentials & how to change them
- Adding new users (admin CLI, not exposed via API by default)
- JWT internals (HS256, 24h expiry, scrypt password hashing)
- Logout (client-side: clear sessionStorage)

Quick reference:

```python
# Add a new user from Python
from scripts.auth import add_user
add_user("alice", "secret123", role="user")

# Change password
from scripts.auth import change_password
change_password("admin", "admin123", "newStrongPassword456")
```

## Security

- **Authentication**: JWT (HS256) with scrypt-hashed passwords. 24h expiry.
  See [`docs/SECURITY.md`](docs/SECURITY.md).
- **Rate limiting** via `slowapi`: chat 20/min, login 10/min, models 60/min
- **CORS** restrictive via `ALLOWED_ORIGINS` env
- **Block scanners** (sqlmap, nikto, masscan, nmap) by User-Agent
- **XSS escape** in `write_document` (xml.sax.saxutils)
- **DoS protection**: max 50KB fields, max 2000 chars message, max 64 chars username
- **Errors** don't expose stack traces
- **Health endpoint** with hard timeouts (no event-loop deadlock)
- **401 redirect**: expired/invalid token → automatic redirect to login screen

## Performance

Optimizations to prevent the 60s "stuck" responses reported in v0.2:

- **Early-stop in agent loop**: if 2 consecutive iterations call the same
  set of tools, the loop terminates (avoids infinite oscillation on RAG).
- **MAX_ITER = 3** (down from 5): typical RAG queries finish in 1-2 iter.
- **Reuse first response**: no double Ollama call for streaming final answer
  (~2-3s saved per response).
- **Real-time SSE**: `startAutoScroll()` updates chat position every RAF
  while the user is at the bottom (no scroll jumps if user scrolled up).
- **TTFT (time-to-first-token)**: ~2s (just one Ollama call + system prompt).

## UX features

- **Login screen** full-screen with default credentials hint
- **Sign out** button in sidebar with user info display
- Claude-like SPA: left sidebar with conversation list, main chat, doc modal
- **Dark/light theme** toggle
- **Stop button** during streaming (AbortController)
- **Keyboard shortcuts**: Enter send, Esc stop/close, Ctrl+K new chat,
  Ctrl+L focus, Ctrl+M compare, Ctrl+/ help
- **Real-time streaming** from Ollama (tokens arrive as generated)
- **Markdown rendering** in responses
- **Tool cards** with expand/collapse
- **Compare mode** (Ctrl+M): same query to base and FT side-by-side

## Files of interest for code review

1. `scripts/agent/run.py` — 80-line agent loop, no LangChain, early-stop
2. `scripts/auth.py` — JWT + scrypt, no external deps
3. `scripts/tools/registry.py` — `@tool` decorator pattern
4. `scripts/chat_app.py` — SSE streaming with auth + rate limit + scanner block
5. `scripts/obs.py` — thread-safe observability (contextvars, not globals)
6. `scripts/chat_static/index.html` — login screen, SSE consumer, auto-scroll
7. `tests/test_*.py` — 93 tests including E2E with real Ollama
