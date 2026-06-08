FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces has limited resources; CPU-only mode for inference
# (no Ollama, no GPU). We serve a "demo" version with a pre-canned
# response generator. For real inference, deploy elsewhere with GPU.

COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the chat app
COPY app/scripts/ /app/scripts/
COPY app/chat_static/ /app/scripts/chat_static/
COPY app/data/ /app/data/ 2>/dev/null || true

# Hugging Face Spaces expects port 7860 by default
ENV PORT=7860
ENV HOST=0.0.0.0

EXPOSE 7860

# For HF demo: serve the chat UI but with a stub backend that
# returns pre-canned responses (no Ollama available in HF Spaces)
RUN echo "Demo mode: pre-canned responses" > /app/MODE

CMD ["python", "-m", "uvicorn", "scripts.chat_app_hf:app", "--host", "0.0.0.0", "--port", "7860"]
