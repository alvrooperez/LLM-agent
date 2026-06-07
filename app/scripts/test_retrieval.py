"""
Test del retrieval: dada una pregunta, devuelve los top-k chunks de Qdrant.

Uso:
  python scripts/test_retrieval.py "How do I create a collection in Qdrant?"
  python scripts/test_retrieval.py "How do I create a collection in Qdrant?" --k 5
"""
import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

COLLECTION = "ai_engineering_docs"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Pregunta en texto libre")
    parser.add_argument("--k", type=int, default=3, help="Número de resultados (default 3)")
    args = parser.parse_args()

    print(f"Cargando modelo de embeddings...")
    model = SentenceTransformer(EMBED_MODEL)
    client = QdrantClient("http://localhost:6333")

    q_emb = model.encode(args.query, normalize_embeddings=True).tolist()
    res = client.query_points(collection_name=COLLECTION, query=q_emb, limit=args.k)

    print(f"\nQuery: {args.query}\n")
    for i, r in enumerate(res.points, 1):
        print(f"[{i}] score={r.score:.3f} | {r.payload['category']}")
        print(f"    source: {r.payload['source']}")
        text = r.payload['text'].replace('\n', ' ')[:300]
        print(f"    text: {text}...")
        print()


if __name__ == "__main__":
    main()
