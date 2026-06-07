FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code
COPY scripts/ ./scripts/
COPY chat_static/ ./scripts/chat_static/

# Default data dir (mounted as volume in compose)
RUN mkdir -p /app/data

EXPOSE 8000 8090

# Default command (overridden in compose per service)
CMD ["python", "-m", "uvicorn", "scripts.chat_app:app", "--host", "0.0.0.0", "--port", "8090"]
