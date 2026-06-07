"""
Herramientas del agente Phase 4.
Cada función va con @tool y se registra automáticamente en TOOL_REGISTRY.

Ejecutar las tools:
  - search_docs -> llama a RAG API en :8000
  - list_models -> llama a Ollama API en :11434
  - get_gpu_stats -> subprocess a nvidia-smi
  - get_collection_info -> llama a Qdrant REST API en :6333
  - plot_metric -> matplotlib genera PNG, guarda en data/metrics/
  - write_document -> usa ReportLab para generar PDF, guarda en data/docs/

Todas las tools devuelven un string. Si fallan, devuelven un string de error
(para que el modelo pueda responder con algo en lugar de silenciarse).
"""
import os
import sys
import json
import re
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# Asegurar UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── API helpers ────────────────────────────────────────────────────────────────

def _ollama_request(path: str, body: dict = None, timeout: int = 30, retries: int = 2) -> str:
    """Llama a Ollama con retry exponencial. Devuelve body como string o [ERROR]."""
    url = f"http://localhost:11434{path}"
    data = json.dumps(body).encode() if body else None
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s, 2s
                continue
        except Exception as e:
            # Errores no-recuperables (no retry)
            return f"[ERROR] No se pudo conectar a Ollama ({url}): {e}"
    return f"[ERROR] Ollama no responde tras {retries+1} intentos ({url}): {last_err}"


def _rag_request(query: str, k: int = 3, timeout: int = 60, retries: int = 1) -> str:
    """Llama a RAG API con retry. Parsea respuesta y formatea con fuentes."""
    url = "http://localhost:8000/ask"
    payload = json.dumps({"question": query, "k": k}).encode()
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                answer = result.get("answer", "")
                sources = result.get("sources", [])
                out = answer
                if sources:
                    out += "\n\n__Fuentes:__"
                    for s in sources:
                        out += f"\n- {s.get('title', 'doc')}: {s.get('snippet', '')[:100]}..."
                return out
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return f"[ERROR] RAG API HTTP {e.code}: {body[:200]}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
                continue
        except Exception as e:
            return f"[ERROR] RAG API no disponible: {e}"
    return f"[ERROR] RAG API no responde tras {retries+1} intentos: {last_err}"


def _qdrant_get(path: str, timeout: int = 5, retries: int = 1) -> dict:
    url = f"http://localhost:6333{path}"
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.3 * (2 ** attempt))
                continue
        except Exception as e:
            return {"error": str(e)}
    return {"error": f"Qdrant no responde tras {retries+1} intentos: {last_err}"}


# ─── Tool implementations ────────────────────────────────────────────────────────

from tools.registry import tool


@tool(
    name="search_docs",
    description="Busca documentos relevantes en la knowledge base técnica del proyecto. Úsala para responder preguntas sobre Ollama, Qdrant, RAG, fine-tuning, o cualquier tecnología del stack AI.",
    params={
        "query": {
            "type": "string",
            "description": "Consulta de búsqueda en lenguaje natural",
            "required": True,
        },
        "k": {
            "type": "integer",
            "description": "Número máximo de documentos a devolver (default 3)",
            "default": 3,
            "required": False,
        },
    },
)
def search_docs(query: str, k: int = 3) -> str:
    return _rag_request(query, k=k)


@tool(
    name="list_models",
    description="Lista los modelos LLM disponibles en Ollama. Devuelve nombre, tamaño, y fecha de modificación de cada modelo.",
    params={},
)
def list_models() -> str:
    raw = _ollama_request("/api/tags")
    try:
        models = json.loads(raw).get("models", [])
        if not models:
            return "No hay modelos cargados en Ollama."
        lines = []
        for m in models:
            size_gb = m.get("size", 0) / (1024**3)
            lines.append(f"- {m['name']}: {size_gb:.1f} GB")
        return "Modelos disponibles:\n" + "\n".join(lines)
    except Exception as e:
        return f"[ERROR] list_models falló: {e}\nRaw: {raw[:200]}"


@tool(
    name="get_gpu_stats",
    description="Obtiene estadísticas de la GPU NVIDIA: uso de VRAM (MB), porcentaje de utilización, y temperatura (°C). Útil para monitorizar recursos durante fine-tuning o inference.",
    params={},
)
def get_gpu_stats() -> str:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return f"[ERROR] nvidia-smi falló: {result.stderr.strip()}"
        parts = [p.strip() for p in result.stdout.strip().split(",")]
        used_mb, total_mb, util_pct, temp_c = parts[0], parts[1], parts[2], parts[3]
        used_gb = float(used_mb) / 1024
        total_gb = float(total_mb) / 1024
        return (f"GPU: {used_gb:.1f}/{total_gb:.1f} GB VRAM "
                f"({100*used_gb/total_gb:.0f}% usados), "
                f"Utilización: {util_pct}%, "
                f"Temperatura: {temp_c}°C")
    except FileNotFoundError:
        return "[ERROR] nvidia-smi no encontrado. ¿Está NVIDIA driver instalado?"
    except Exception as e:
        return f"[ERROR] get_gpu_stats falló: {e}"


@tool(
    name="get_collection_info",
    description="Obtiene metadata de una colección de Qdrant: número de puntos, dimensión de los vectores, tipo de distancia, y estado. Útil para saber qué hay indexado en la knowledge base.",
    params={
        "name": {
            "type": "string",
            "description": "Nombre de la colección (default: ai_engineering_docs)",
            "default": "ai_engineering_docs",
            "required": False,
        },
    },
)
def get_collection_info(name: str = "ai_engineering_docs") -> str:
    result = _qdrant_get(f"/collections/{name}")
    if "error" in result:
        return f"[ERROR] Colección '{name}' no encontrada: {result['error']}"
    info = result.get("result", result)  # raw response if no .result wrapper
    status = info.get("status", "unknown")
    # Try both field names (Qdrant version differences)
    points = (info.get("vectors_count")
              or info.get("vectors_count_count")  # nested inside result
              or info.get("points_count", "unknown"))
    config = info.get("config", {})
    params = config.get("params", {})
    vec_conf = params.get("vectors", {})
    vec_size = vec_conf.get("size", "unknown")
    dist = vec_conf.get("distance", "unknown")
    return (f"Colección '{name}': {points} puntos, "
            f"vectores de dimensión {vec_size}, "
            f"distancia {dist}, estado: {status}")


@tool(
    name="plot_metric",
    description="Genera un gráfico PNG de una métrica en un rango temporal. Los datos se leen desde data/metrics/metrics.csv. El PNG se guarda en data/metrics/plots/ y se devuelve el path.",
    params={
        "metric": {
            "type": "string",
            "description": "Nombre de la métrica a graficar (columna del CSV): loss, accuracy, tokens_per_sec, gpu_memory_mb",
            "required": True,
        },
        "range": {
            "type": "string",
            "description": "Rango temporal (last_1h, last_24h, last_7d, all)",
            "default": "last_24h",
            "required": False,
        },
    },
)
def plot_metric(metric: str, range: str = "last_24h") -> str:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import pandas as pd
        from datetime import datetime, timedelta

        metrics_dir = Path("data/metrics")
        metrics_dir.mkdir(parents=True, exist_ok=True)
        plots_dir = metrics_dir / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)

        csv_path = metrics_dir / "metrics.csv"
        if not csv_path.exists():
            return f"[ERROR] metrics.csv no existe en {csv_path}. Genera datos primero."

        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        df = df.sort_values("timestamp")

        # Filtrar rango
        now = datetime.now()
        if range == "last_1h":
            df = df[df["timestamp"] >= now - timedelta(hours=1)]
        elif range == "last_24h":
            df = df[df["timestamp"] >= now - timedelta(days=1)]
        elif range == "last_7d":
            df = df[df["timestamp"] >= now - timedelta(days=7)]

        if metric not in df.columns:
            available = list(df.columns)
            return f"[ERROR] Métrica '{metric}' no disponible. Disponibles: {available}"

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df["timestamp"], df[metric], marker="o", markersize=2, linewidth=1)
        ax.set_title(f"{metric} — {range}")
        ax.set_xlabel("Tiempo")
        ax.set_ylabel(metric)
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        plt.tight_layout()

        out_path = plots_dir / f"{metric}_{range}.png"
        fig.savefig(str(out_path), dpi=100)
        plt.close(fig)

        return f"Gráfico guardado en {out_path}"
    except ImportError as e:
        return f"[ERROR] plot_metric necesita matplotlib: {e}"
    except Exception as e:
        return f"[ERROR] plot_metric falló: {e}"


@tool(
    name="write_document",
    description="Genera un documento PDF a partir de una plantilla predefinida. Rellena los campos especificados y lo guarda en data/docs/. Devuelve el path del PDF generado.",
    params={
        "template": {
            "type": "string",
            "description": "Nombre de la plantilla: project_report, tech_summary, eval_report, dataset_card",
            "required": True,
        },
        "fields": {
            "type": "object",
            "description": "Diccionario de campos a rellenar en la plantilla. Varían según la plantilla.",
            "required": True,
        },
    },
)
def write_document(template: str, fields: dict) -> str:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib import colors
        from datetime import datetime
        from xml.sax.saxutils import escape as xml_escape

        # Sanitize: solo allowlist de templates, fields limitados en tamaño
        ALLOWED_TEMPLATES = {"project_report", "tech_summary", "eval_report", "dataset_card"}
        if template not in ALLOWED_TEMPLATES:
            return f"[ERROR] Plantilla '{template}' no reconocida. Disponibles: {sorted(ALLOWED_TEMPLATES)}"

        # Limitar tamaño total de fields para evitar DoS
        if not isinstance(fields, dict):
            return "[ERROR] fields debe ser un objeto/dict"
        total_size = sum(len(str(k)) + len(str(v)) for k, v in fields.items())
        if total_size > 50_000:  # 50KB de contenido
            return f"[ERROR] Contenido demasiado largo ({total_size} chars, max 50000)"

        def safe(s) -> str:
            """Escapa HTML/XML para ReportLab Paragraph."""
            return xml_escape(str(s), entities={"'": "&apos;", '"': "&quot;"})

        docs_dir = Path("data/docs")
        docs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = docs_dir / f"{template}_{timestamp}.pdf"

        doc = SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=2*cm, rightMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # ── Plantillas ────────────────────────────────────────────

        if template == "project_report":
            story.append(Paragraph(safe(fields.get("title", "Project Report")), styles["Title"]))
            story.append(Spacer(1, 0.5*cm))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
            story.append(Spacer(1, 0.5*cm))
            for key, val in fields.items():
                if key not in ("title", "date"):
                    story.append(Paragraph(f"<b>{safe(key)}:</b> {safe(val)}", styles["Normal"]))
                    story.append(Spacer(1, 0.3*cm))

        elif template == "tech_summary":
            story.append(Paragraph(safe(fields.get("title", "Technical Summary")), styles["Title"]))
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph(f"<i>{safe(fields.get('subtitle', ''))}</i>", styles["Italic"]))
            story.append(Spacer(1, 0.5*cm))
            sections = fields.get("sections", [])
            for sec in sections:
                story.append(Paragraph(safe(sec.get("heading", "")), styles["Heading2"]))
                story.append(Paragraph(safe(sec.get("body", "")), styles["Normal"]))
                story.append(Spacer(1, 0.3*cm))

        elif template == "eval_report":
            story.append(Paragraph("Evaluation Report", styles["Title"]))
            story.append(Spacer(1, 0.5*cm))
            model_name = safe(fields.get("model", "unknown"))
            dataset_name = safe(fields.get("dataset", "unknown"))
            rows = [
                ["Métrica", "Valor"],
                ["Modelo", model_name],
                ["Dataset", dataset_name],
                ["Accuracy", safe(fields.get("accuracy", "N/A"))],
                ["F1-Score", safe(fields.get("f1", "N/A"))],
                ["Tool Call Rate", safe(fields.get("tool_call_rate", "N/A"))],
                ["Avg Response Length", safe(fields.get("avg_len", "N/A"))],
            ]
            t = Table(rows, colWidths=[6*cm, 9*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D7DD2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4FA")]),
            ]))
            story.append(t)

        elif template == "dataset_card":
            story.append(Paragraph("Dataset Card", styles["Title"]))
            story.append(Spacer(1, 0.5*cm))
            rows = [
                ["Campo", "Valor"],
                ["Nombre", safe(fields.get("name", "N/A"))],
                ["Entrenamiento", safe(fields.get("train_size", "N/A"))],
                ["Test", safe(fields.get("test_size", "N/A"))],
                ["Tools", safe(fields.get("tools", "N/A"))],
                ["Formato", safe(fields.get("format", "N/A"))],
            ]
            t = Table(rows, colWidths=[4*cm, 11*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#97CC04")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(t)

        doc.build(story)
        return f"PDF generado: {out_path}"

    except ImportError:
        return "[ERROR] write_document necesita reportlab. Instálalo: pip install reportlab"
    except Exception as e:
        return f"[ERROR] write_document falló: {e}"