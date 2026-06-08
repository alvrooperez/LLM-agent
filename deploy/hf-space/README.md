# Hugging Face Spaces deployment

This folder contains everything needed to deploy a **demo** of the AI Engineering
Portfolio to [Hugging Face Spaces](https://huggingface.co/spaces).

## What this demo shows vs. the real thing

| Feature | Local (real) | HF Spaces (demo) |
|---|---|---|
| Web UI (Claude-like SPA) | Yes | Yes (same) |
| Multi-tool chaining | Yes (5/5 eval) | **Simulated** (canned responses) |
| Real Ollama inference | Yes (qwen2.5-rag-ft) | No |
| RAG over real docs | Yes (62 chunks) | No |
| PDF generation | Yes (real ReportLab) | Simulated |
| Streaming from Ollama | Yes (real SSE) | Yes (real SSE, but pre-canned text) |
| Tools (6) with backends | Real (GPU, Qdrant, RAG API) | Simulated (pre-canned responses) |

The demo **shows the architecture and UX** but doesn't run real inference (HF Spaces
free tier has no GPU).

## Deploy in 5 minutes

1. **Create a new Space** at https://huggingface.co/new-space
   - Name: `ai-engineering-portfolio` (or whatever)
   - SDK: **Docker**
   - Hardware: **CPU basic** (free)
   - Visibility: Public (for portfolio)

2. **Clone the Space locally**:
   ```bash
   git clone https://huggingface.co/spaces/YOUR-USER/ai-engineering-portfolio
   cd ai-engineering-portfolio
   ```

3. **Copy this folder's contents** to the Space:
   ```bash
   cp -r ../ai-engineer-portfolio/deploy/hf-space/* .
   ```

   This gives you:
   - `Dockerfile` (HF Spaces compatible)
   - `chat_app_hf.py` (demo backend with canned responses)
   - `requirements.txt` (copy from `app/requirements.txt`)

4. **Push to HF**:
   ```bash
   git add .
   git commit -m "Deploy demo to HF Spaces"
   git push
   ```

5. **Wait ~5 min** for the Space to build. The Space will be at:
   `https://huggingface.co/spaces/YOUR-USER/ai-engineering-portfolio`

## Why Docker SDK on HF Spaces?

HF Spaces supports Gradio, Streamlit, and Docker. Docker is the most flexible —
you can use any framework, and the `Dockerfile` in this folder uses FastAPI directly.

## For real inference (not this demo)

To run the real system publicly, you need a GPU. Options:
- **Hugging Face Spaces with GPU** (paid, ~$0.60/hr for T4)
- **fly.io** with GPU machines
- **Modal** (serverless, pay per second)
- A VPS with a rented GPU (RunPod, Vast.ai, etc.)

For real inference deployment, use the `app/scripts/chat_app.py` (not the HF demo)
and add a sidecar Ollama container.
