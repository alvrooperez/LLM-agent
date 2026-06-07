"""
Ingestión de documentación de AI engineering en Qdrant.

Pipeline:
  1. Descarga HTML/MD de fuentes configuradas (con caché local)
  2. Parsea a texto limpio (BeautifulSoup)
  3. Trocea en chunks con overlap
  4. Genera embeddings con BGE-small (CPU)
  5. Carga en Qdrant con metadata

Uso:
  python scripts/ingest.py
"""
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

# Forzar UTF-8 en Windows (cp1252 rompe con caracteres no-ASCII)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# ─── Config ────────────────────────────────────────────────────────
import os
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = "ai_engineering_docs"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384
DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHUNK_WORDS = 400
CHUNK_OVERLAP = 50
MIN_CHUNK_WORDS = 50

# Fuentes: nombre de categoría → lista de URLs
SOURCES = {
    "llamaindex": [
        "https://docs.llamaindex.ai/en/stable/getting_started/starter_example/",
        "https://docs.llamaindex.ai/en/stable/getting_started/concepts/",
        "https://docs.llamaindex.ai/en/stable/module_guides/models/llms/usage_custom/",
    ],
    "qdrant": [
        "https://qdrant.tech/documentation/quickstart/",
        "https://qdrant.tech/documentation/concepts/collections/",
        "https://qdrant.tech/documentation/concepts/search/",
    ],
    "ollama": [
        "https://raw.githubusercontent.com/ollama/ollama/main/docs/api.md",
        "https://raw.githubusercontent.com/ollama/ollama/main/docs/troubleshooting.md",
    ],
    "huggingface": [
        "https://huggingface.co/docs/transformers/quicktour",
        "https://huggingface.co/docs/transformers/training",
    ],
}


# ─── Helpers ───────────────────────────────────────────────────────
def log(msg, level="info"):
    ts = time.strftime("%H:%M:%S")
    prefix = {"info": "  ", "warn": "⚠ ", "error": "✗ "}.get(level, "  ")
    print(f"[{ts}] {prefix}{msg}", flush=True)


def fetch(url):
    """Download URL, return raw bytes. Saves to disk for caching."""
    parsed = urlparse(url)
    fname = parsed.path.strip("/").replace("/", "_") or "index"
    if not Path(fname).suffix:
        fname += ".html"
    save_path = DATA_DIR / parsed.netloc / fname
    save_path.parent.mkdir(parents=True, exist_ok=True)

    if save_path.exists():
        log(f"cache hit: {save_path.name}")
        return save_path.read_bytes()

    log(f"downloading: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (AI-Engineer-Portfolio/1.0)"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    save_path.write_bytes(r.content)
    return r.content


def extract_text(url, content):
    """Extract clean text from HTML or markdown."""
    text = content.decode("utf-8", errors="ignore")
    if url.endswith(".md") or url.endswith(".txt"):
        return text
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return "\n".join(lines)


def chunk_text(text, chunk_words=CHUNK_WORDS, overlap=CHUNK_OVERLAP):
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if len(words) <= chunk_words:
        return [text] if len(words) > MIN_CHUNK_WORDS else []
    chunks = []
    step = chunk_words - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_words])
        if len(chunk.split()) > MIN_CHUNK_WORDS:
            chunks.append(chunk)
    return chunks


# ─── Main ──────────────────────────────────────────────────────────
def main():
    # 1. Fetch & parse
    all_chunks = []
    for category, urls in SOURCES.items():
        log(f"── {category} ({len(urls)} URLs)")
        for url in urls:
            try:
                content = fetch(url)
                text = extract_text(url, content)
                chunks = chunk_text(text)
                log(f"  → {len(chunks)} chunks de {url[:60]}...")
                for c in chunks:
                    all_chunks.append({"text": c, "source": url, "category": category})
            except Exception as e:
                log(f"  ERROR {url}: {e}", "warn")

    log(f"Total chunks: {len(all_chunks)}")
    if not all_chunks:
        log("No hay chunks. Abortando.", "error")
        sys.exit(1)

    # 2. Embed
    log(f"Cargando modelo {EMBED_MODEL} (puede tardar 1-2 min la primera vez)...")
    model = SentenceTransformer(EMBED_MODEL)
    log(f"Embedding {len(all_chunks)} chunks...")
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # importante para cosine
    )
    log(f"Embeddings shape: {embeddings.shape}")

    # 3. Qdrant
    log(f"Conectando a Qdrant {QDRANT_URL}...")
    client = QdrantClient(QDRANT_URL)
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
        log(f"Colección '{COLLECTION}' eliminada (re-run)")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )
    log(f"Colección '{COLLECTION}' creada")

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=emb.tolist(),
            payload={
                "text": c["text"],
                "source": c["source"],
                "category": c["category"],
            },
        )
        for emb, c in zip(embeddings, all_chunks)
    ]
    log(f"Upsert {len(points)} puntos en batches de 50...")
    BATCH = 50
    for i in range(0, len(points), BATCH):
        client.upsert(collection_name=COLLECTION, points=points[i:i + BATCH], wait=True)
        log(f"  batch {i // BATCH + 1}/{(len(points) + BATCH - 1) // BATCH} OK")
    log("Upsert OK")

    # 4. Verificar
    info = client.get_collection(COLLECTION)
    log(f"✓ Colección: {info.points_count} puntos, dim={info.config.params.vectors.size}")
    counts = {}
    for c in all_chunks:
        counts[c["category"]] = counts.get(c["category"], 0) + 1
    for cat, n in counts.items():
        log(f"  {cat}: {n} chunks")


if __name__ == "__main__":
    main()
