"""
API RAG: recibe pregunta, busca en Qdrant, genera respuesta con Ollama.

Endpoints:
  POST /ask   - pregunta → respuesta + fuentes
  GET  /health - health check
  GET  /       - info básica

Uso local:
  uvicorn scripts.api:app --host 0.0.0.0 --port 8000
"""
import os
import sys
from typing import Optional

# Forzar UTF-8 en Windows (cp1252 rompe con caracteres no-ASCII)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# ─── Config ────────────────────────────────────────────────────────
COLLECTION = os.environ.get("COLLECTION", "ai_engineering_docs")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
TOP_K = int(os.environ.get("TOP_K", "5"))

# ─── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Engineering RAG",
    description="RAG self-hosted sobre el stack de AI engineering",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos y cliente (se inicializan al arrancar)
_model: Optional[SentenceTransformer] = None
_qdrant: Optional[QdrantClient] = None


@app.on_event("startup")
def startup():
    global _model, _qdrant
    _model = SentenceTransformer(EMBED_MODEL)
    _qdrant = QdrantClient(QDRANT_URL)
    print(f"[OK] RAG listo: {COLLECTION} @ {QDRANT_URL}, modelo {OLLAMA_MODEL} @ {OLLAMA_URL}")


# ─── Schemas ───────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=20)


class Source(BaseModel):
    text: str
    source: str
    category: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    model: str
    context_tokens_est: int


# ─── Endpoints ─────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "service": "AI Engineering RAG",
        "version": "0.1.0",
        "endpoints": ["/ask (POST)", "/health (GET)"],
    }


@app.get("/health")
def health():
    info = _qdrant.get_collection(COLLECTION)
    return {
        "status": "ok",
        "collection": COLLECTION,
        "points": info.points_count,
        "embedding_model": EMBED_MODEL,
        "llm": OLLAMA_MODEL,
    }


def build_prompt(question: str, contexts: list[dict]) -> str:
    """Construye el prompt con el contexto y la pregunta."""
    context_block = "\n\n---\n\n".join(
        f"[Fuente {i+1} | {c['category']}]\n{c['text']}"
        for i, c in enumerate(contexts)
    )
    return f"""Eres un asistente experto en AI engineering. Responde a la pregunta del usuario basándote SOLO en el contexto proporcionado a continuación. Si la información no está en el contexto, di "No tengo información suficiente para responder con estos documentos". Responde siempre en español, de forma concisa y técnica. Cita las fuentes usando la notación [Fuente N] cuando sea relevante.

CONTEXTO:
{context_block}

PREGUNTA: {question}

RESPUESTA:"""


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    # 1. Embed de la pregunta
    q_emb = _model.encode(req.question, normalize_embeddings=True).tolist()

    # 2. Retrieval en Qdrant
    res = _qdrant.query_points(
        collection_name=COLLECTION,
        query=q_emb,
        limit=req.k,
    )
    contexts = [
        {
            "text": p.payload["text"],
            "source": p.payload["source"],
            "category": p.payload["category"],
            "score": round(p.score, 4),
        }
        for p in res.points
    ]

    if not contexts:
        raise HTTPException(404, "No se encontraron documentos relevantes")

    # 3. Construir prompt
    prompt = build_prompt(req.question, contexts)

    # 4. Llamar a Ollama
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(502, f"Error llamando a Ollama: {e}")

    answer = r.json().get("response", "").strip()
    if not answer:
        raise HTTPException(502, "Ollama devolvió respuesta vacía")

    return AskResponse(
        answer=answer,
        sources=contexts,
        model=OLLAMA_MODEL,
        context_tokens_est=len(prompt.split()),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
