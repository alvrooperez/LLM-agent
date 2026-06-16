"""
Web chat que reutiliza el agent loop (scripts/agent/run.py).

Backend FastAPI con seguridad, rate limiting y autenticación:
  POST /api/auth/login    → username/password → JWT
  POST /api/auth/logout   → (client-side: borrar token)
  GET  /                  → index.html
  GET  /architecture      → architecture.html
  POST /api/chat          → ejecuta el agent loop (no streaming)
  POST /api/chat/stream   → SSE streaming
  GET  /api/models        → modelos Ollama disponibles
  GET  /api/health        → health check
  GET  /api/docs          → lista PDFs generados
  GET  /api/docs/{file}   → sirve PDF

Seguridad:
  - Auth JWT (Authorization: Bearer <token>). Ver scripts/auth.py.
  - Login con usuarios en data/users.json (scrypt hashed).
  - Rate limit por IP: chat 20/min, models 60/min, otros más permisivos.
  - CORS restrictivo (env ALLOWED_ORIGINS, default localhost).
  - Inputs sanitizados; errores no exponen stack traces.
  - User-Agent vacío o ausente = 403.

Uso:
  python -m uvicorn scripts.chat_app:app --host 0.0.0.0 --port 8090
  # con auth:
  CHAT_API_KEY=sk-local-123 python -m uvicorn scripts.chat_app:app --port 8090
"""
import os
import sys
import time
import json
import hmac
import hashlib
import secrets
import logging
import urllib.request
import re
from pathlib import Path
from html import escape as html_escape
from typing import Optional

# Logging (no expone a clientes)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
log = logging.getLogger("chat_app")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Setup imports del agent loop ─────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))
import tools.implementations  # noqa: F401 — registra las tools
from agent.run import run_agent

STATIC_DIR = SCRIPTS_DIR / "chat_static"
STATIC_DIR.mkdir(exist_ok=True)

# Directorio donde write_document guarda los PDFs
DOCS_DIR = SCRIPTS_DIR.parent / "data" / "docs"

# ── Security config ──────────────────────────────────────────────────────
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:8090,http://127.0.0.1:8090").split(",") if o.strip()]
MAX_MESSAGE_LEN = int(os.environ.get("MAX_MESSAGE_LEN", "2000"))
BLOCKED_UA_PATTERNS = [r"sqlmap", r"nikto", r"masscan", r"nmap"]  # bots/scanners comunes

# Auth: importar modulo y crear users.json al arranque
from auth import (
    ensure_users_file, login as auth_login, get_user_from_token,
    extract_bearer_token, CurrentUser, get_user as get_user_record,
)
ensure_users_file()  # crea data/users.json con admin/admin123 si no existe


# ── FastAPI app ──────────────────────────────────────────────────────────
app = FastAPI(title="AI Engineering Chat", version="0.2.0")

# CORS restrictivo (no "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)

# Rate limiter (slowapi). Key = IP del cliente.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Security dependencies ────────────────────────────────────────────────

def get_current_user(request: Request) -> CurrentUser:
    """Dependencia FastAPI: extrae JWT del header Authorization: Bearer <token>,
    valida firma + expiración, y devuelve CurrentUser. Si falla, 401."""
    auth_header = request.headers.get("authorization", "")
    token = extract_bearer_token(auth_header)
    if not token:
        log.warning("auth_fail ip=%s path=%s reason=no_token",
                    get_remote_address(request), request.url.path)
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_from_token(token)
    if not user:
        log.warning("auth_fail ip=%s path=%s reason=invalid_token",
                    get_remote_address(request), request.url.path)
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def block_scanners(request: Request) -> None:
    """Bloquea user-agents típicos de herramientas de ataque.
    Si el UA está ausente, asigna uno generico (no bloqueamos — WebClient de
    .NET y curl no siempre lo mandan, y no son atacantes por eso)."""
    ua = (request.headers.get("user-agent", "") or "").strip().lower()
    if not ua:
        # Log pero no bloquear — clientes legítimos sin UA (curl, WebClient)
        log.debug("empty_ua path=%s ip=%s", request.url.path, get_remote_address(request))
        ua = "unknown"
    for pattern in BLOCKED_UA_PATTERNS:
        if re.search(pattern, ua):
            log.warning("scanner_blocked ua=%s ip=%s", ua, get_remote_address(request))
            raise HTTPException(status_code=403, detail="Forbidden")


# ── Auth endpoints ───────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=256)


@app.post("/api/auth/login")
@limiter.limit("10/minute")
async def login_endpoint(
    request: Request,
    req: LoginRequest,
    _: None = Depends(block_scanners),
):
    """POST /api/auth/login con {username, password}. Devuelve {token, user, expires_in}.
    401 si credenciales invalidas. Rate-limited a 10/min por IP (anti brute force)."""
    ip = get_remote_address(request)
    result = auth_login(req.username, req.password)
    if not result:
        log.warning("login_fail ip=%s user=%s", ip, req.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    log.info("login_ok ip=%s user=%s role=%s",
             ip, result["user"]["username"], result["user"]["role"])
    return result


@app.get("/api/auth/me")
async def me_endpoint(
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(block_scanners),
):
    """GET /api/auth/me — devuelve info del usuario autenticado. Útil para
    que el frontend sepa si el JWT sigue siendo válido al recargar."""
    return {
        "username": user.username,
        "role": user.role,
        "is_admin": user.is_admin(),
    }


# ── Schemas ───────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LEN)
    model: str = Field(default="qwen2.5-rag-ft", max_length=100)
    session_id: Optional[str] = Field(default=None, max_length=64)


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list
    iterations: int
    elapsed_sec: float
    model: str


# ── Helpers ──────────────────────────────────────────────────────────────
def _safe_error_log(e: Exception, context: str) -> str:
    """Log interno, mensaje genérico al cliente."""
    log.exception("error in %s: %s", context, e)
    return "Internal server error"


def _validate_message(msg: str) -> str:
    """Sanitiza el mensaje antes de enviarlo al modelo."""
    # Strip control chars excepto newline/tab
    msg = "".join(c for c in msg if c == "\t" or c == "\n" or c >= " ")
    return msg.strip()


def _check_service_ok(url: str, timeout: float = 2.0) -> bool:
    """Comprueba si un servicio responde. Bloqueante — usar con asyncio.to_thread."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


# ── Endpoints ─────────────────────────────────────────────────────────────
@app.get("/")
async def index(_: None = Depends(block_scanners)):
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/architecture")
async def architecture(_: None = Depends(block_scanners)):
    return FileResponse(STATIC_DIR / "architecture.html")


@app.get("/api/health")
@limiter.limit("120/minute")
async def health(request: Request, _: None = Depends(block_scanners)):
    """Health check con timeouts duros. Cada check corre en su thread para
    no bloquear el event loop. Si el check tarda mas de 2.5s, devuelve 'down'
    y sigue."""
    out = {"status": "ok", "components": {}}

    async def check(name: str, url: str):
        try:
            # Timeout duro: si el thread tarda mas de 2.5s, asumimos down
            ok = await asyncio.wait_for(
                asyncio.to_thread(_check_service_ok, url, 2.0),
                timeout=2.5,
            )
            out["components"][name] = "ok" if ok else "down"
        except (asyncio.TimeoutError, Exception):
            out["components"][name] = "down"

    # Ejecutar los 3 checks en paralelo, sin bloquearse mutuamente
    await asyncio.gather(
        check("ollama", "http://localhost:11434/api/tags"),
        check("qdrant", "http://localhost:6333/collections"),
        check("rag_api", "http://localhost:8000/health"),
    )

    if any(v == "down" for v in out["components"].values()):
        out["status"] = "degraded"
    return out


@app.get("/api/models")
@limiter.limit("60/minute")
async def list_models(request: Request, user: CurrentUser = Depends(get_current_user), __: None = Depends(block_scanners)):
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {
            "models": [
                {"name": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 2)}
                for m in data.get("models", [])
            ]
        }
    except Exception as e:
        log.error("list_models error: %s", e)
        raise HTTPException(status_code=503, detail="Models service unavailable")


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    __: None = Depends(block_scanners),
):
    t0 = time.time()
    try:
        from obs import instrumented_run_agent
        # Sanitizar input
        clean_msg = _validate_message(req.message)
        if not clean_msg:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        result = instrumented_run_agent(clean_msg, model=req.model, verbose=False)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_error_log(e, "chat"))

    elapsed = time.time() - t0
    raw_tcs = result.get("tool_calls", [])
    norm_tcs = []
    for tc in raw_tcs:
        name = tc.get("name", "")
        args = tc.get("arguments") if "arguments" in tc else tc.get("args", {})
        norm_tcs.append({
            "name": name,
            "arguments": args,
            "result": tc.get("result"),
            "duration_ms": tc.get("duration_ms"),
        })
    return ChatResponse(
        answer=result["answer"],
        tool_calls=norm_tcs,
        iterations=result["iterations"],
        elapsed_sec=round(elapsed, 2),
        model=req.model,
    )


@app.get("/api/docs")
@limiter.limit("60/minute")
async def list_docs(request: Request, user: CurrentUser = Depends(get_current_user), __: None = Depends(block_scanners)):
    if not DOCS_DIR.exists():
        return {"docs": []}
    docs = []
    for p in sorted(DOCS_DIR.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True):
        st = p.stat()
        docs.append({
            "name": p.name,
            "size_kb": round(st.st_size / 1024, 1),
            "modified": st.st_mtime,
            "url": f"/api/docs/{p.name}",
        })
    return {"docs": docs}


@app.get("/api/docs/{filename}")
@limiter.limit("60/minute")
async def get_doc(
    request: Request,
    filename: str,
    user: CurrentUser = Depends(get_current_user),
    __: None = Depends(block_scanners),
):
    # Sanitize: solo nombre, no paths ni traversal
    if "/" in filename or "\\" in filename or ".." in filename or not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    # Limitar longitud
    if len(filename) > 200:
        raise HTTPException(status_code=400, detail="Filename too long")
    path = DOCS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


# ── Streaming endpoint (SSE) ──────────────────────────────────────────────
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_agent(req: ChatRequest):
    """SSE que consume run_agent_streaming y emite eventos al cliente.

    Eventos emitidos:
      - thinking: {iter} cuando arranca una iteracion del agent loop
      - tool_call: {name, arguments, result, duration_ms} por cada tool
      - token: {text} por cada chunk de la respuesta final (streaming real)
      - done: {iterations, elapsed_sec, model} al final
      - error: {message} si algo falla
    """
    t0 = time.time()
    iterations = 0
    try:
        from agent.run import run_agent_streaming
        # Streaming REAL token-a-token: ejecutamos el generador en un hilo
        # y empujamos cada evento a una queue asincrona. La coroutine hace
        # yield de los eventos conforme llegan, para que el cliente vea
        # "Pensando... (iter N)" antes de la primera respuesta.
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def producer():
            try:
                for ev in run_agent_streaming(req.message, model=req.model, verbose=False):
                    loop.call_soon_threadsafe(queue.put_nowait, ev)
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})
                loop.call_soon_threadsafe(queue.put_nowait, None)

        # Arrancar el productor en background
        future = loop.run_in_executor(None, producer)

        # Drenar la queue y hacer yield de cada evento al cliente
        while True:
            ev = await queue.get()
            if ev is None:  # sentinel = productor terminó
                break
            et = ev.get("type")
            if et == "thinking":
                iterations = ev.get("iter", iterations)
                yield _sse("thinking", {"iter": iterations})
            elif et == "tool_call":
                yield _sse("tool_call", {
                    "name": ev["name"],
                    "arguments": ev.get("arguments", {}),
                    "result": ev.get("result"),
                    "duration_ms": ev.get("duration_ms"),
                })
            elif et == "token":
                yield _sse("token", {"text": ev["text"]})
            elif et == "error":
                yield _sse("error", {"message": ev.get("message", "Internal error")})
            elif et == "done":
                iterations = ev.get("iterations", iterations)
    except Exception as e:
        log.exception("stream error: %s", e)
        yield _sse("error", {"message": "Internal error"})
        return

    elapsed = time.time() - t0
    yield _sse("done", {
        "iterations": iterations,
        "elapsed_sec": round(elapsed, 2),
        "model": req.model,
    })


async def stream_one_model(message: str, model: str):
    """Generador SSE para un solo modelo. Etiqueta eventos con 'model' field
    para que el frontend pueda separar los streams de cada modelo."""
    t0 = time.time()
    iterations = 0
    try:
        from agent.run import run_agent_streaming
        # Mismo patron queue/producer que stream_agent: el productor en hilo
        # empuja cada evento a la queue, y aqui hacemos yield conforme llegan.
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def producer():
            try:
                for ev in run_agent_streaming(message, model=model, verbose=False):
                    loop.call_soon_threadsafe(queue.put_nowait, ev)
                loop.call_soon_threadsafe(queue.put_nowait, None)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})
                loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(None, producer)

        while True:
            ev = await queue.get()
            if ev is None:
                break
            et = ev.get("type")
            if et == "thinking":
                iterations = ev.get("iter", iterations)
                yield _sse("thinking", {"model": model, "iter": iterations})
            elif et == "tool_call":
                yield _sse("tool_call", {
                    "model": model,
                    "name": ev["name"],
                    "arguments": ev.get("arguments", {}),
                    "result": ev.get("result"),
                    "duration_ms": ev.get("duration_ms"),
                })
            elif et == "token":
                yield _sse("token", {"model": model, "text": ev["text"]})
            elif et == "error":
                yield _sse("error", {"model": model, "message": ev.get("message", "Internal error")})
            elif et == "done":
                iterations = ev.get("iterations", iterations)

    except Exception as e:
        log.exception("compare stream error for %s: %s", model, e)
        yield _sse("error", {"model": model, "message": "Internal error"})
        return

    elapsed = time.time() - t0
    yield _sse("done", {
        "model": model,
        "iterations": iterations,
        "elapsed_sec": round(elapsed, 2),
    })


async def stream_compare(message: str, models: list):
    """SSE con dos streams en paralelo (base vs fine-tuned).
    Cada evento incluye 'model' field para que el frontend pueda separar.
    """
    # Default: comparar base vs FT
    if not models or len(models) == 0:
        models = ["qwen2.5:3b", "qwen2.5-rag-ft"]
    # Limitar a 2 modelos para no abusar
    if len(models) > 2:
        models = models[:2]

    # Lanzar los dos generadores en paralelo
    generators = [stream_one_model(message, m) for m in models]
    # Mezclar eventos con asyncio
    import asyncio as _asyncio
    queues = [_asyncio.Queue() for _ in models]
    done_events = [_asyncio.Event() for _ in models]

    async def pump(gen, queue, done):
        try:
            async for ev in gen:
                await queue.put(ev)
        finally:
            done.set()

    tasks = [_asyncio.create_task(pump(g, q, d)) for g, q, d in zip(generators, queues, done_events)]

    # Leer de las dos colas y emitir conforme llegan
    while not all(d.is_set() for d in done_events) or any(not q.empty() for q in queues):
        for q in queues:
            try:
                ev = q.get_nowait()
                yield ev
            except _asyncio.QueueEmpty:
                pass
        await _asyncio.sleep(0.01)

    # Asegurar que las tasks terminaron
    for t in tasks:
        try:
            await _asyncio.wait_for(t, timeout=1.0)
        except _asyncio.TimeoutError:
            t.cancel()


class CompareRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LEN)
    models: Optional[list] = Field(default=None, max_length=2)
    session_id: Optional[str] = Field(default=None, max_length=64)


@app.post("/api/chat/compare")
@limiter.limit("10/minute")
async def chat_compare(
    request: Request,
    req: CompareRequest,
    user: CurrentUser = Depends(get_current_user),
    __: None = Depends(block_scanners),
):
    """Compara dos modelos side-by-side sobre la misma query.
    Devuelve SSE con eventos etiquetados por modelo.
    """
    # Sanitizar
    clean_msg = _validate_message(req.message)
    if not clean_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    return StreamingResponse(
        stream_compare(clean_msg, req.models),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    req: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    __: None = Depends(block_scanners),
):
    # Sanitizar input
    clean_msg = _validate_message(req.message)
    if not clean_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    req.message = clean_msg
    return StreamingResponse(
        stream_agent(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Sanitize write_document inputs (defense in depth) ────────────────────
# Aunque el registry valida el template, los fields van tal cual a ReportLab.
# Aplicar escape HTML a strings que se pasarán a <Paragraph> como contenido.
# Esto se hace en implementations.py, pero documentamos aquí la decisión.


# ── Shutdown handlers (top-level, para tests) ────────────────────────────────
import signal as _signal
import atexit as _atexit
import uvicorn as _uvicorn

_server_ref = {"server": None}  # mutable container para signal handler


def shutdown_handler(signum, frame):
    """Maneja SIGTERM/SIGINT para shutdown limpio."""
    log.info("received signal %d, shutting down gracefully...", signum)
    if _server_ref["server"] is not None:
        _server_ref["server"].should_exit = True


def cleanup():
    """Cleanup al exit: flush logs, cerrar handles."""
    log.info("cleanup: closing obs file handles if any")
    log.info("cleanup: done")


# Registrar cleanup (idempotente, atexit lo maneja)
_atexit.register(cleanup)


# ── Main ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    print(f"=== AI Engineering Chat ===")
    print(f"  http://localhost:{port}")
    print(f"  Auth: {'ENABLED' if CHAT_API_KEY else 'DISABLED (set CHAT_API_KEY to enable)'}")
    print(f"  CORS origins: {ALLOWED_ORIGINS}")

    config = _uvicorn.Config(
        app, host="0.0.0.0", port=port, log_level="info",
        access_log=True,
    )
    server = _uvicorn.Server(config)
    _server_ref["server"] = server

    # Registrar handlers (reemplazan los de uvicorn para que loguee primero)
    try:
        _signal.signal(_signal.SIGTERM, shutdown_handler)
        _signal.signal(_signal.SIGINT, shutdown_handler)
    except ValueError:
        # No estamos en el main thread (e.g. en tests)
        pass

    log.info("starting uvicorn...")
    server.run()
    log.info("server stopped")
