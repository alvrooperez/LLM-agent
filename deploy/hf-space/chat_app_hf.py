"""
chat_app_hf.py — Versión DEMO del chat para Hugging Face Spaces.

HF Spaces no tiene GPU ni Ollama. Esta versión:
- Sirve la misma UI (index.html)
- Devuelve respuestas pre-canned que muestran lo que el agente real hace
- Incluye tool calls simulados para que se vea el flujo
- Es 100% self-contained (no requiere servicios externos)

Para la versión real (con Ollama, RAG, tool calling real), usa
scripts/chat_app.py y el docker-compose.yml de la raíz.
"""
import os
import time
import json
import asyncio
from typing import Optional, List

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="AI Engineering Chat (Demo Mode)", version="demo-1.0.0")

# CORS permissive for demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Static UI (same as production)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "chat_static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/architecture")
async def architecture():
    return FileResponse(os.path.join(STATIC_DIR, "architecture.html"))


# Canned responses for the demo
DEMO_RESPONSES = {
    "default": {
        "answer": "Esta es una respuesta de **demo mode**. En el modo real, este mensaje vendría de qwen2.5-rag-ft corriendo en Ollama, con RAG sobre 62 chunks de docs y 6 tools reales (search_docs, list_models, get_gpu_stats, get_collection_info, plot_metric, write_document). El agente puede encadenar 2-3 tools en una sola iteración (multi-tool chaining: 5/5 PASS).\n\nPara ver el sistema completo corriendo, clona el repo y sigue las instrucciones del README.",
        "tool_calls": [
            {
                "name": "get_collection_info",
                "arguments": {"name": "ai_engineering_docs"},
                "result": "Colección 'ai_engineering_docs': 62 puntos, vectores de dimensión 384, distancia Cosine, estado: green",
                "duration_ms": 47
            },
            {
                "name": "list_models",
                "arguments": {},
                "result": "Modelos disponibles:\n- qwen2.5-rag-ft:latest: 1.9 GB\n- qwen2.5:3b: 1.9 GB",
                "duration_ms": 38
            }
        ]
    },
    "gpu": {
        "answer": "Tu GPU tiene **2.3 GB** de VRAM usados de 4.0 GB totales (58%), temperatura 65°C, utilización 0% (sin carga activa). Detectada como NVIDIA RTX 3050 Laptop GPU.",
        "tool_calls": [
            {
                "name": "get_gpu_stats",
                "arguments": {},
                "result": "GPU: 2.3/4.0 GB VRAM (58% usados), Utilización: 0%, Temperatura: 65°C",
                "duration_ms": 12
            }
        ]
    },
    "modelo": {
        "answer": "Tengo 2 modelos disponibles:\n\n1. **qwen2.5-rag-ft** (fine-tuned) - 1.9 GB\n2. **qwen2.5:3b** (base) - 1.9 GB\n\nAmbos corren en Q4_K_M quantization. El fine-tuned fue entrenado con LoRA sobre 230 ejemplos de tool-calling. (Honest finding: el FT no añadió capacidad nueva, el base ya sabía tool-calling.)",
        "tool_calls": [
            {
                "name": "list_models",
                "arguments": {},
                "result": "Modelos disponibles:\n- qwen2.5-rag-ft:latest: 1.9 GB\n- qwen2.5:3b: 1.9 GB",
                "duration_ms": 23
            }
        ]
    },
    "pdf": {
        "answer": "He generado un PDF de tipo project_report. Lo encuentras en la sección 'Documents' (icono 📄 en el sidebar). El PDF incluye título, secciones generadas con los campos que pasaste, y un formato profesional con ReportLab.\n\n(Tool ejecutado: write_document con template='project_report' y fields={title: 'Demo'})",
        "tool_calls": [
            {
                "name": "write_document",
                "arguments": {
                    "template": "project_report",
                    "fields": {"title": "Demo"}
                },
                "result": "PDF generado: data/docs/project_report_20260608_104000.pdf",
                "duration_ms": 412
            }
        ]
    }
}


def pick_demo_response(message: str) -> dict:
    msg_lower = message.lower()
    if "gpu" in msg_lower or "tarjeta" in msg_lower or "vram" in msg_lower:
        return DEMO_RESPONSES["gpu"]
    if "modelo" in msg_lower and ("lista" in msg_lower or "qué" in msg_lower or "tienes" in msg_lower):
        return DEMO_RESPONSES["modelo"]
    if "pdf" in msg_lower or "genera" in msg_lower or "document" in msg_lower:
        return DEMO_RESPONSES["pdf"]
    return DEMO_RESPONSES["default"]


# Request schema
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    model: str = Field(default="qwen2.5-rag-ft", max_length=100)


# SSE
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_demo(req: ChatRequest):
    """SSE que simula el agente real: tool_call, tokens, done."""
    t0 = time.time()
    response = pick_demo_response(req.message)

    # Emit tool calls
    for tc in response["tool_calls"]:
        yield _sse("tool_call", tc)
        await asyncio.sleep(0.05)

    # Stream the answer word by word
    answer = response["answer"]
    words = answer.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        yield _sse("token", {"text": chunk})
        await asyncio.sleep(0.025)

    # Done
    yield _sse("done", {
        "iterations": 2,
        "elapsed_sec": round(time.time() - t0, 2),
        "model": "demo (canned)",
    })


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        stream_demo(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/models")
async def list_models():
    return {
        "models": [
            {"name": "qwen2.5-rag-ft", "size_gb": 1.93},
            {"name": "qwen2.5:3b", "size_gb": 1.93},
        ]
    }


@app.get("/api/health")
async def health():
    return {"status": "ok (demo mode)", "components": {"demo": "ok"}}


@app.get("/api/docs")
async def list_docs():
    # No real docs in demo mode
    return {"docs": []}
