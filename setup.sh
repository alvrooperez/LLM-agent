#!/usr/bin/env bash
# ============================================================================
# AI Engineering Portfolio — Setup script (Linux/Mac)
# Verifica prerequisitos y arranca el stack completo.
#
# Uso:
#   ./setup.sh                    (verificar + arrancar)
#   ./setup.sh check              (solo verificar)
#   ./setup.sh bootstrap          (verificar + arrancar + poblar Qdrant)
# ============================================================================

set -e

cd "$(dirname "$0")"

echo "============================================================"
echo " AI Engineering Portfolio — Setup"
echo "============================================================"
echo

ERRORS=0
WARNINGS=0

# -- Check Docker --------------------------------------------------------
echo "[1/6] Checking Docker..."
if ! command -v docker >/dev/null 2>&1; then
    echo "  FAIL: Docker not installed."
    echo "  Install from: https://www.docker.com/products/docker-desktop"
    ERRORS=$((ERRORS+1))
else
    echo "  OK: $(docker --version)"
fi

# -- Check Docker Compose ------------------------------------------------
echo "[2/6] Checking Docker Compose..."
if ! docker compose version >/dev/null 2>&1; then
    echo "  FAIL: Docker Compose not available."
    ERRORS=$((ERRORS+1))
else
    echo "  OK: $(docker compose version)"
fi

# -- Check NVIDIA driver + CUDA ----------------------------------------
echo "[3/6] Checking NVIDIA driver..."
if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "  FAIL: nvidia-smi not found."
    echo "  Update driver: https://www.nvidia.com/Download/index.aspx"
    ERRORS=$((ERRORS+1))
else
    GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    echo "  OK: GPU $GPU"
fi

# -- Check Python --------------------------------------------------------
echo "[4/6] Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "  FAIL: Python 3 not installed."
    echo "  Install from: https://www.python.org/downloads/"
    ERRORS=$((ERRORS+1))
else
    echo "  OK: $(python3 --version)"
fi

# -- Check Ollama reachable --------------------------------------------
echo "[5/6] Checking Ollama (if running already)..."
if curl -s --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "  OK: Ollama reachable at http://localhost:11434"
else
    echo "  INFO: Ollama not running yet. Will be started by docker compose."
fi

# -- Check Docker NVIDIA runtime ----------------------------------------
echo "[6/6] Checking Docker GPU passthrough..."
if docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi >/dev/null 2>&1; then
    echo "  OK: Docker can access GPU."
else
    echo "  WARN: Docker cannot access GPU. Stack will work but slower (CPU only)."
    WARNINGS=$((WARNINGS+1))
fi

echo
echo "============================================================"
if [ "$ERRORS" -gt 0 ]; then
    echo " SETUP FAILED — $ERRORS error(s), $WARNINGS warning(s)"
    echo "============================================================"
    echo
    echo "Fix the errors above and run setup.sh again."
    exit 1
else
    echo " SETUP OK — $WARNINGS warning(s)"
    echo "============================================================"
fi

# -- If only check, stop here -------------------------------------------
if [ "${1:-}" = "check" ]; then
    echo
    echo "Check-only mode. Not starting services."
    exit 0
fi

echo
echo "Starting stack with docker compose..."
docker compose up -d

if [ $? -ne 0 ]; then
    echo
    echo "FAIL: docker compose up failed."
    echo "Run 'docker compose logs' to debug."
    exit 1
fi

echo
echo "Stack started. Services:"
echo "  Ollama:    http://localhost:11434"
echo "  Qdrant:    http://localhost:6333"
echo "  RAG API:   http://localhost:8000"
echo "  Chat App:  http://localhost:8090"

if [ "${1:-}" = "bootstrap" ]; then
    echo
    echo "Populating Qdrant with knowledge base..."
    docker compose --profile bootstrap run --rm rag-bootstrap
fi

echo
echo "Next steps:"
echo "  1. Download Ollama models:"
echo "     docker exec aieng-ollama ollama pull qwen2.5:3b"
echo "     docker exec aieng-ollama ollama pull qwen2.5-rag-ft"
echo "  2. Open the chat: http://localhost:8090"
echo
