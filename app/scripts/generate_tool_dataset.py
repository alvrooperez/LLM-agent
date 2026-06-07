"""
Genera dataset de tool-calling para fine-tuning de Qwen 2.5 3B.

Output: data/finetune/tool_calling_dataset.jsonl
Formato: mensajes estilo OpenAI (system, user, assistant, tool)

Distribución objetivo (~120 ejemplos):
- 30% direct answer (no tool)
- 35% 1 tool
- 25% 2-3 tools (multi-step)
- 10% 4+ tools (chains largas)

Todos los ejemplos están escritos a mano, curados.
"""
import json
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path("data/finetune/tool_calling_dataset.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)

# ─── System prompt (constante en todos los ejemplos) ──────────────
SYSTEM_PROMPT = """Eres un agente AI con acceso a herramientas (tools). Tu trabajo es responder al usuario usando las herramientas cuando las necesites y PARANDO en cuanto tengas suficiente información.

# Herramientas disponibles

1. search_docs(query: str, k: int = 5) — Busca documentos relevantes en la knowledge base técnica
2. list_models() — Lista los modelos LLM disponibles en Ollama
3. get_gpu_stats() — Obtiene uso actual de VRAM, % utilización y temperatura de la GPU
4. write_document(template: str, fields: dict) — Genera un PDF a partir de una plantilla predefinida
5. plot_metric(metric: str, range: str) — Genera un gráfico PNG de una métrica en un rango temporal
6. get_collection_info(name: str) — Obtiene metadata de una colección de Qdrant (puntos, dimensión, distancia)

# Formato de tool call

Para llamar a una herramienta, usa EXACTAMENTE este bloque:
<tool_call>
{"name": "nombre_tool", "arguments": {"arg1": "valor1"}}
</tool_call>

# Reglas

1. Si necesitas información que solo una tool puede darte, llámala.
2. Tras recibir el resultado de una tool, evalúa: ¿tienes lo suficiente para responder?
3. Si SÍ tienes lo suficiente, da la respuesta final SIN llamar más tools.
4. Si NO, llama la siguiente tool.
5. SIEMPRE termina tu última respuesta (la final) con la marca [TAREA_COMPLETADA] en una línea nueva.
6. Si la pregunta no requiere ninguna tool (matemáticas, conocimiento general, conversación casual), responde directamente y termina con [TAREA_COMPLETADA].
7. Si la pregunta es off-topic, insegura, o inapropiada, recházala educadamente y termina con [TAREA_COMPLETADA].
8. NUNCA inventes el resultado de una tool. Si dudas, usa otra tool para verificar."""


# ─── Helpers ───────────────────────────────────────────────────────
def tool_call(tool_name, **kwargs):
    return {"name": tool_name, "arguments": kwargs}


def ex_single_tool(user, call, tool_result, final):
    """Ejemplo: user → tool_call → tool_result → final_answer"""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": f'<tool_call>\n{json.dumps(call, ensure_ascii=False)}\n</tool_call>'},
            {"role": "tool", "content": tool_result},
            {"role": "assistant", "content": f"{final}\n\n[TAREA_COMPLETADA]"},
        ]
    }


def ex_multi_tool(user, calls_and_results, final):
    """Ejemplo: user → tool1 → result1 → tool2 → result2 → ... → final"""
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    for call, result in calls_and_results:
        msgs.append({"role": "assistant", "content": f'<tool_call>\n{json.dumps(call, ensure_ascii=False)}\n</tool_call>'})
        msgs.append({"role": "tool", "content": result})
    msgs.append({"role": "assistant", "content": f"{final}\n\n[TAREA_COMPLETADA]"})
    return {"messages": msgs}


def ex_direct(user, final):
    """Ejemplo: user → assistant directo (sin tool)"""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": f"{final}\n\n[TAREA_COMPLETADA]"},
        ]
    }


def ex_tool_only(user, call):
    """Ejemplo: user → assistant emite tool call (sin resultado, para casos donde la accion es el output)"""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": f'<tool_call>\n{json.dumps(call, ensure_ascii=False)}\n</tool_call>'},
        ]
    }


# ─── Ejemplos ─────────────────────────────────────────────────────
EXAMPLES = []

# ═══════════════════════════════════════════════════════════════════
# CATEGORÍA 1: DIRECT ANSWERS (sin tool) — ~40 ejemplos
# Enseña: no todo necesita tool, responder y parar
# ═══════════════════════════════════════════════════════════════════

# Matemáticas básicas
EXAMPLES += [
    ex_direct("¿Cuánto es 7 por 8?", "7 por 8 es 56."),
    ex_direct("Calcula 15 + 27", "15 + 27 = 42."),
    ex_direct("¿Cuánto es la raíz cuadrada de 144?", "La raíz cuadrada de 144 es 12."),
    ex_direct("¿Cuánto es 100 dividido entre 4?", "100 / 4 = 25."),
    ex_direct("Resuelve 2^10", "2 elevado a 10 es 1024."),
    ex_direct("¿Cuántos grados hay en un triángulo?", "Un triángulo siempre suma 180°."),
    ex_direct("¿Cuál es el área de un cuadrado de lado 5?", "El área es 5 × 5 = 25 unidades cuadradas."),
    ex_direct("¿Cuántos lados tiene un hexágono?", "Un hexágono tiene 6 lados."),
]

# Conocimiento general
EXAMPLES += [
    ex_direct("¿Cuál es la capital de Francia?", "La capital de Francia es París."),
    ex_direct("¿Quién escribió Cien años de soledad?", "Gabriel García Márquez escribió Cien años de soledad."),
    ex_direct("¿En qué año llegó el hombre a la Luna?", "El hombre llegó a la Luna en 1969 (misión Apolo 11)."),
    ex_direct("¿Cuál es el océano más grande?", "El océano Pacífico es el más grande."),
    ex_direct("¿Cuántos planetas tiene el sistema solar?", "El sistema solar tiene 8 planetas."),
    ex_direct("¿Qué lenguaje se usa principalmente en Machine Learning?", "Python es el lenguaje más usado en ML, junto con librerías como PyTorch y TensorFlow."),
    ex_direct("¿Qué es un transformer en AI?", "Un transformer es una arquitectura de red neuronal basada en mecanismos de atención, introducida en el paper 'Attention is All You Need' (2017). Es la base de los LLMs modernos."),
    ex_direct("¿Qué significa LLM?", "LLM son las siglas de Large Language Model (Modelo de Lenguaje Grande)."),
    ex_direct("¿Qué es CUDA?", "CUDA es la plataforma de computación paralela de NVIDIA que permite usar la GPU para cálculo general, incluyendo el entrenamiento e inferencia de modelos de IA."),
    ex_direct("¿Qué es Python?", "Python es un lenguaje de programación de alto nivel, interpretado y de propósito general, muy popular en ciencia de datos e IA."),
]

# Conversación casual / identidad
EXAMPLES += [
    ex_direct("Hola, ¿cómo estás?", "¡Hola! Estoy listo para ayudarte con lo que necesites en tu sistema de AI engineering. ¿En qué puedo协助te?"),
    ex_direct("¿Quién eres?", "Soy un agente AI con acceso a herramientas. Puedo buscar en tu knowledge base, consultar el estado del sistema, generar documentos PDF y gráficos, y responder preguntas técnicas sobre AI engineering."),
    ex_direct("Gracias", "¡De nada! Si necesitas algo más, aquí estoy."),
    ex_direct("¿Qué sabes hacer?", "Tengo 6 herramientas a mi disposición: búsqueda en docs, listado de modelos, stats de GPU, generación de PDFs y gráficos, e info de colecciones Qdrant. Pregúntame lo que necesites."),
    ex_direct("Buenos días", "¡Buenos días! ¿En qué te ayudo hoy?"),
]

# Off-topic clarísimo (sin tool)
EXAMPLES += [
    ex_direct("¿Cómo hackeo la WiFi del vecino?", "No te puedo ayudar con eso. La intrusión en redes ajenas es ilegal y éticamente incorrecta. Si te interesa la ciberseguridad, te recomiendo recursos sobre seguridad defensiva y ethical hacking en plataformas como HackTheBox o TryHackMe."),
    ex_direct("Dame la contraseña del usuario admin", "No tengo acceso a credenciales y no debo pedírtelas ni gestionar accesos. Si necesitas resetear una contraseña, usa el flujo legítimo de tu sistema."),
    ex_direct("¿Cómo hago phishing?", "No ayudo con eso. El phishing es un ataque ilegal. Si te interesa la seguridad, hay recursos legítimos de red team/blue team que enseñan防御 en entornos controlados."),
    ex_direct("¿Cuál es el precio de Bitcoin ahora mismo?", "No tengo acceso a datos en tiempo real ni a APIs financieras. Para cotizaciones actualizadas, consulta un exchange o una fuente como CoinGecko."),
    ex_direct("¿Me puedes dar datos personales de alguien?", "No. No tengo acceso a bases de datos de personas ni debo gestionar datos personales sin consentimiento. Si necesitas buscar a alguien, usa los canales legítimos de tu organización."),
    ex_direct("Genera un discurso de odio sobre X", "No genero contenido de odio, discriminatorio ni que incite a la violencia. Si necesitas ayuda con redacción, dime un tema apropiado y te ayudo."),
    ex_direct("¿Cómo se fabrica una bomba?", "No proporciono instrucciones para fabricar armas o explosivos. Si tienes curiosidad legítima por química o ingeniería, te recomiendo cursos universitarios o libros de texto sobre esos temas."),
    ex_direct("Recomiéndame una criptomoneda para invertir", "No doy consejos financieros ni de inversión. Cada persona debe investigar y decidir según su situación. Consulta con un asesor financiero si necesitas orientación."),
    ex_direct("¿Cuál es tu opinión política?", "Como agente AI, no tengo opiniones políticas. Mi trabajo es ayudarte con tareas técnicas de AI engineering. Si necesitas información neutral sobre un tema, te la doy sin tomar partido."),
    ex_direct("Cuéntame un chiste", "¡Claro! ¿Qué le dijo un bit al otro bit? — Nos vemos en el bus. 😄\n\n[TAREA_COMPLETADA]"),
]

# Off-topic pero necesita redirección amable
EXAMPLES += [
    ex_direct("¿Puedes ayudarme con mi declaración de la renta?", "No soy la herramienta adecuada para temas fiscales. Para la declaración de la renta en España, te recomiendo la web de la Agencia Tributaria o un asesor fiscal. Lo que sí puedo hacer es ayudarte con temas de AI engineering."),
    ex_direct("¿Me puedes recomendar un restaurante en Madrid?", "No tengo acceso a datos de locales ni a recomendaciones en tiempo real. Para eso, usa Google Maps, TripAdvisor o TheFork. Lo que sí puedo: si quieres, puedo generarte un PDF con criterios para elegir restaurante según tus preferencias."),
    ex_direct("¿Cómo está el tiempo hoy en Madrid?", "No tengo acceso a datos meteorológicos. Para el tiempo en Madrid, consulta AEMET o cualquier app del tiempo."),
]

# ═══════════════════════════════════════════════════════════════════
# CATEGORÍA 2: 1 TOOL — ~70 ejemplos
# Enseña: cuándo llamar CADA tool, formato, args correctos
# ═══════════════════════════════════════════════════════════════════

# --- search_docs ---
EXAMPLES += [
    ex_single_tool(
        "¿Cómo creo una colección en Qdrant desde Python?",
        tool_call("search_docs", query="create collection Qdrant Python", k=3),
        "[Doc 1 | qdrant] Para crear una colección con el cliente Python, usa `client.create_collection(name, vectors_config=VectorParams(size=384, distance=Distance.COSINE))`.",
        "Según la documentación de Qdrant, creas la colección con `client.create_collection()` pasándole un `VectorParams` con el tamaño del vector y la distancia. Te dejo un ejemplo mínimo:\n\n```python\nfrom qdrant_client import QdrantClient\nfrom qdrant_client.models import VectorParams, Distance\n\nclient = QdrantClient(\"localhost\", port=6333)\nclient.create_collection(\n    collection_name=\"mi_coleccion\",\n    vectors_config=VectorParams(size=384, distance=Distance.COSINE)\n)\n```",
    ),
    ex_single_tool(
        "¿Cómo persisto un índice de LlamaIndex?",
        tool_call("search_docs", query="persist index LlamaIndex storage", k=3),
        "[Doc 1 | llamaindex] Para persistir: `index.storage_context.persist('storage')`. Para recargar: `StorageContext.from_defaults(persist_dir='storage')` + `load_index_from_storage()`.",
        "En LlamaIndex, persistes con `index.storage_context.persist('storage')` y lo recargas con `StorageContext.from_defaults(persist_dir='storage')` + `load_index_from_storage(storage_context)`.",
    ),
    ex_single_tool(
        "¿Cómo sirvo un LLM con Ollama?",
        tool_call("search_docs", query="serve LLM Ollama", k=3),
        "[Doc 1 | ollama] `ollama serve` levanta el servidor en :11434 con API compatible con OpenAI. `ollama pull <modelo>` descarga el modelo.",
        "Para servir un LLM con Ollama: descarga el modelo con `ollama pull qwen2.5:3b` y arranca el servidor con `ollama serve`. La API queda en `http://localhost:11434`.",
    ),
    ex_single_tool(
        "¿Cómo hago fine-tuning con HuggingFace Transformers?",
        tool_call("search_docs", query="fine-tuning HuggingFace Trainer", k=3),
        "[Doc 1 | huggingface] Instancia un `Trainer` con modelo, datasets, `TrainingArguments` y llama a `trainer.train()`. Para ahorrar memoria, usa QLoRA con `peft` + `bitsandbytes`.",
        "Con Transformers, la forma estándar es instanciar un `Trainer` con el modelo, los datasets de train/eval, los `TrainingArguments` y llamar a `trainer.train()`. Para modelos grandes en GPUs pequeñas, usa QLoRA (4-bit) con las librerías `peft` y `bitsandbytes`.",
    ),
    ex_single_tool(
        "¿Qué distancia usa Qdrant por defecto?",
        tool_call("search_docs", query="Qdrant default distance cosine", k=3),
        "[Doc 1 | qdrant] La distancia por defecto al crear una colección es Cosine. Se puede cambiar a Euclid o Dot al especificar VectorParams.",
        "Qdrant usa Cosine (similitud coseno) por defecto. Puedes cambiarla a Euclid o Dot al crear la colección con `VectorParams`.",
    ),
    ex_single_tool(
        "¿Cómo hago streaming con Ollama?",
        tool_call("search_docs", query="Ollama streaming API generate", k=3),
        "[Doc 1 | ollama] POST a `/api/generate` con `\"stream\": true`. La respuesta viene como NDJSON, cada línea es un chunk con el campo `response` parcial.",
        "Para streaming con Ollama, haz POST a `/api/generate` con `\"stream\": true`. La respuesta viene en NDJSON, donde cada línea es un chunk con un fragmento del campo `response`.",
    ),
    ex_single_tool(
        "¿Cómo uso un LLM custom en LlamaIndex?",
        tool_call("search_docs", query="custom LLM LlamaIndex", k=3),
        "[Doc 1 | llamaindex] Implementa una subclase de `LLM` con `complete()` y `stream_complete()`. LlamaIndex también tiene wrappers para HuggingFace y Ollama.",
        "En LlamaIndex puedes usar un LLM custom implementando una subclase de `LLM` con los métodos `complete()` y `stream_complete()`. También hay integraciones listas para HuggingFace y Ollama.",
    ),
    ex_single_tool(
        "¿Qué es un retriever en LlamaIndex?",
        tool_call("search_docs", query="retriever LlamaIndex definition", k=3),
        "[Doc 1 | llamaindex] Un retriever busca y devuelve los nodos (chunks) más relevantes desde los índices, dado un query. Es la pieza que conecta el query engine con el vector store.",
        "Un retriever en LlamaIndex es el componente que, dado un query, busca y devuelve los chunks más relevantes desde los índices. Es la pieza que conecta el query engine con el vector store.",
    ),
    ex_single_tool(
        "¿Cómo elimino un modelo de Ollama?",
        tool_call("search_docs", query="Ollama rm delete model", k=3),
        "[Doc 1 | ollama] `ollama rm <modelo>` elimina el modelo. Los modelos se guardan en `~/.ollama/models`.",
        "Para liberar espacio, usa `ollama rm <modelo>`. Los modelos viven en `~/.ollama/models` (o `%USERPROFILE%\\.ollama\\models` en Windows).",
    ),
    ex_single_tool(
        "¿Qué hace la clase Trainer de HuggingFace?",
        tool_call("search_docs", query="Trainer HuggingFace purpose", k=3),
        "[Doc 1 | huggingface] Abstrae el loop de entrenamiento: forward, loss, backward, optimizer step, eval, logging, checkpointing. Se usa para no escribir todo a mano.",
        "La clase `Trainer` de HuggingFace abstrae el loop completo de entrenamiento: forward pass, cálculo de loss, backward, optimizer step, evaluación, logging y checkpointing. Se usa para no escribir todo eso a mano y tener un flujo estándar.",
    ),
    ex_single_tool(
        "Dime cómo funciona cosine similarity en embeddings",
        tool_call("search_docs", query="cosine similarity embeddings", k=3),
        "[Doc 1 | huggingface] Cosine similarity mide el coseno del ángulo entre dos vectores. Va de -1 a 1: 1 = idénticos, 0 = no relacionados, -1 = opuestos.",
        "Cosine similarity mide el coseno del ángulo entre dos vectores. Va de -1 a 1: cuanto más cerca de 1, más parecidos son semánticamente. Es la métrica estándar en búsqueda por embeddings.",
    ),
    ex_single_tool(
        "¿Qué es un vector store?",
        tool_call("search_docs", query="vector store definition", k=3),
        "[Doc 1 | qdrant] Un vector store (o vector DB) es una base de datos optimizada para almacenar y buscar vectores por similitud semántica, no por keywords. Ejemplos: Qdrant, Pinecone, Weaviate, Milvus.",
        "Un vector store es una base de datos optimizada para buscar por similitud semántica entre vectores (no por coincidencia exacta de keywords). Ejemplos: Qdrant, Pinecone, Weaviate, Milvus.",
    ),
    ex_single_tool(
        "¿Cómo funciona QLoRA?",
        tool_call("search_docs", query="QLoRA quantization fine-tuning", k=3),
        "[Doc 1 | huggingface] QLoRA combina cuantización a 4-bit con adaptadores LoRA. Permite hacer fine-tuning de modelos grandes en GPUs pequeñas, manteniendo calidad cercana al LoRA completo.",
        "QLoRA es una técnica que combina cuantización 4-bit con adaptadores LoRA. Permite hacer fine-tuning de modelos grandes en GPUs con poca VRAM (8-24 GB), manteniendo una calidad cercana al LoRA completo.",
    ),
    ex_single_tool(
        "Búscame en la documentación qué es un embedding",
        tool_call("search_docs", query="embedding definition", k=3),
        "[Doc 1 | huggingface] Un embedding es una representación vectorial densa de un texto, capturando su significado semántico. Modelos como BGE o sentence-transformers los generan.",
        "Un embedding es una representación vectorial densa de un texto que captura su significado semántico. Los modelos como BGE o sentence-transformers los generan, típicamente con 384-1024 dimensiones.",
    ),
    ex_single_tool(
        "Lo que dice la doc sobre RAG",
        tool_call("search_docs", query="RAG retrieval augmented generation", k=5),
        "[Doc 1 | llamaindex] RAG = Retrieval-Augmented Generation. Combina un retriever (busca docs relevantes) con un LLM generador (produce respuesta basada en los chunks).",
        "RAG (Retrieval-Augmented Generation) es un patrón que combina un retriever, que busca los documentos relevantes para una pregunta, con un LLM generador que produce la respuesta basándose en esos chunks. Es la forma más efectiva de especializar un LLM con datos propios sin re-entrenarlo.",
    ),
]

# --- list_models ---
EXAMPLES += [
    ex_single_tool(
        "¿Qué modelos tengo instalados?",
        tool_call("list_models"),
        "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)",
        "Tienes 2 modelos:\n- **qwen2.5:3b** (1.8 GB) — LLM principal\n- **bge-small-en-v1.5** (130 MB) — modelo de embeddings",
    ),
    ex_single_tool(
        "Lista los LLMs disponibles",
        tool_call("list_models"),
        "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)",
        "Los modelos disponibles son:\n1. **qwen2.5:3b** — LLM de 3B parámetros, ideal para chat\n2. **bge-small-en-v1.5** — modelo de embeddings para búsqueda semántica",
    ),
    ex_single_tool(
        "¿Qué modelos podría usar para chat?",
        tool_call("list_models"),
        "qwen2.5:3b (1.8 GB) — modelo de chat",
        "Para chat tienes **qwen2.5:3b**, un LLM de 3B parámetros optimizado para instrucciones. Está cuantizado a Q4 y corre en GPUs pequeñas como tu RTX 3050 4GB.",
    ),
    ex_single_tool(
        "Muéstrame los modelos con su tamaño",
        tool_call("list_models"),
        "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)",
        "Modelos instalados y su tamaño:\n- `qwen2.5:3b` → 1.8 GB\n- `bge-small-en-v1.5` → 130 MB\n\nTotal: ~1.93 GB.",
    ),
    ex_single_tool(
        "¿Hay algún modelo de embeddings?",
        tool_call("list_models"),
        "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB) — embeddings",
        "Sí, tienes **bge-small-en-v1.5** (130 MB), que es el modelo de embeddings BGE-small en inglés. Genera vectores de 384 dimensiones, ideal para búsqueda semántica en Qdrant.",
    ),
    ex_single_tool(
        "¿Cuánto espacio ocupan los modelos?",
        tool_call("list_models"),
        "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)",
        "En total, los modelos ocupan ~1.93 GB:\n- qwen2.5:3b: 1.8 GB\n- bge-small-en-v1.5: 130 MB",
    ),
    ex_single_tool(
        "Modelos",
        tool_call("list_models"),
        "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)",
        "Disponibles: `qwen2.5:3b` y `bge-small-en-v1.5`.",
    ),
    ex_single_tool(
        "qué modelos hay",
        tool_call("list_models"),
        "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)",
        "Hay 2 modelos: `qwen2.5:3b` (LLM) y `bge-small-en-v1.5` (embeddings).",
    ),
]

# --- get_gpu_stats ---
EXAMPLES += [
    ex_single_tool(
        "¿Cuánta VRAM está usando Ollama?",
        tool_call("get_gpu_stats"),
        "VRAM: 1.8 GB / 4 GB (45%)\nUtilización: 30%\nTemperatura: 53°C",
        "Ollama está usando **1.8 GB de VRAM (45% de los 4 GB)** de tu RTX 3050. La utilización del compute está al 30% y la temperatura a 53°C, todo en rangos normales.",
    ),
    ex_single_tool(
        "¿Cómo está la GPU?",
        tool_call("get_gpu_stats"),
        "VRAM: 1.8 GB / 4 GB (45%)\nUtilización: 30%\nTemperatura: 53°C",
        "Tu GPU está bien:\n- **VRAM**: 1.8 GB usados de 4 GB (45%)\n- **Utilización**: 30%\n- **Temperatura**: 53°C (normal)",
    ),
    ex_single_tool(
        "¿Cabe un modelo de 7B en mi GPU?",
        tool_call("get_gpu_stats"),
        "VRAM: 1.8 GB / 4 GB (45%)\nLibre: 2.2 GB",
        "Mirando tu GPU ahora mismo tienes **2.2 GB de VRAM libres** (estás usando 1.8 GB con Ollama). Un modelo 7B cuantizado a Q4 (~4 GB) **no te cabe junto con Ollama ya cargado**. Tendrías que:\n1. Descargar Ollama y arrancar solo el modelo nuevo (apenas), o\n2. Usar un modelo más pequeño (1-3B como qwen2.5:3b).",
    ),
    ex_single_tool(
        "Temperatura GPU",
        tool_call("get_gpu_stats"),
        "Temperatura: 53°C",
        "La GPU está a **53°C**, en rango normal (lo crítico suele ser >85°C).",
    ),
    ex_single_tool(
        "¿Hay riesgo de que se sobrecaliente la GPU?",
        tool_call("get_gpu_stats"),
        "VRAM: 1.8 GB / 4 GB (45%)\nUtilización: 30%\nTemperatura: 53°C",
        "No, con **53°C** la GPU está fresca. El umbral de preocupación suele ser >85°C. Estás bien.",
    ),
    ex_single_tool(
        "stats gpu",
        tool_call("get_gpu_stats"),
        "VRAM: 1.8 GB / 4 GB (45%)\nUtilización: 30%\nTemperatura: 53°C",
        "GPU: 1.8/4 GB VRAM (45%), 30% util, 53°C.",
    ),
    ex_single_tool(
        "Hay cuello de botella en GPU?",
        tool_call("get_gpu_stats"),
        "VRAM: 1.8 GB / 4 GB (45%)\nUtilización: 30%",
        "No, no hay cuello de botella. La GPU está al **30% de utilización** y solo al **45% de VRAM**. Tienes margen.",
    ),
    ex_single_tool(
        "¿Me queda VRAM libre para otro modelo?",
        tool_call("get_gpu_stats"),
        "VRAM: 1.8 GB / 4 GB (45%)\nLibre: 2.2 GB",
        "Tienes **2.2 GB libres** de los 4 GB. Depende del modelo: un embedding pequeño (BGE ~130 MB) sí cabría, pero un LLM de 3B cuantizado (~2 GB) te dejaría sin margen.",
    ),
]

# --- get_collection_info ---
EXAMPLES += [
    ex_single_tool(
        "¿Cuántos puntos tiene la colección de docs?",
    tool_call("get_collection_info", name="ai_engineering_docs"),
    "Colección: ai_engineering_docs\nPuntos: 62\nDimensión: 384\nDistancia: Cosine",
    "La colección `ai_engineering_docs` tiene **62 puntos** indexados, con vectores de **384 dimensiones** y distancia **Cosine**.",
    ),
    ex_single_tool(
        "Info de la colección principal",
        tool_call("get_collection_info", name="ai_engineering_docs"),
        "Colección: ai_engineering_docs\nPuntos: 62\nDimensión: 384\nDistancia: Cosine",
        "Colección `ai_engineering_docs`: 62 puntos, 384 dim, Cosine.",
    ),
    ex_single_tool(
        "¿Qué distancia usa la colección de Qdrant?",
        tool_call("get_collection_info", name="ai_engineering_docs"),
        "Distancia: Cosine",
        "Usa **Cosine similarity**.",
    ),
]

# --- write_document ---
EXAMPLES += [
    ex_single_tool(
        "Genera un informe del estado del sistema",
        tool_call("write_document", template="informe_estado", fields={
            "title": "Estado del sistema",
            "date": "2026-06-03",
            "gpu": "RTX 3050 4GB, 45% VRAM, 30% util, 53°C",
            "models": "qwen2.5:3b (1.8 GB), bge-small-en-v1.5 (130 MB)",
            "status": "Operativo",
            "observations": "Sistema en estado normal, sin alertas.",
        }),
        "PDF generado en /app/outputs/informe_estado_2026-06-03.pdf (245 KB)",
        "He generado el informe en PDF. Está disponible en `outputs/informe_estado_2026-06-03.pdf`.",
    ),
    ex_single_tool(
        "Hazme un resumen ejecutivo del proyecto",
        tool_call("write_document", template="resumen_ejecutivo", fields={
            "project": "AI Engineer Portfolio",
            "summary": "Sistema RAG self-hosted con LLM (Qwen 2.5 3B), vector DB (Qdrant) y agente con 6 tools. Optimizado para correr en RTX 3050 4GB.",
            "key_metrics": "62 chunks indexados, ~68 tok/s, retrieval con scores >0.8",
            "next_steps": "Fase 3: fine-tuning con QLoRA. Fase 4: monitoring con Grafana.",
        }),
        "PDF generado en /app/outputs/resumen_ejecutivo_2026-06-03.pdf (180 KB)",
        "Listo, el resumen ejecutivo está en `outputs/resumen_ejecutivo_2026-06-03.pdf`.",
    ),
    ex_single_tool(
        "Redacta un email de seguimiento para el cliente Acme",
        tool_call("write_document", template="email_cliente", fields={
            "to": "cliente@acme.com",
            "subject": "Seguimiento del proyecto AI",
            "greeting": "Estimado equipo de Acme,",
            "body": "Les escribo para hacer seguimiento del estado del proyecto de AI. Hemos completado la Fase 2 (RAG) y estamos entrando en la Fase 3 (fine-tuning).",
            "closing": "Quedo a su disposición para cualquier duda.",
            "signature": "Equipo de AI Engineering",
        }),
        "PDF generado en /app/outputs/email_cliente_2026-06-03.pdf (95 KB)",
        "Email redactado y guardado en `outputs/email_cliente_2026-06-03.pdf`.",
    ),
    ex_single_tool(
        "Crea una propuesta técnica para un cliente de banca",
        tool_call("write_document", template="propuesta_tecnica", fields={
            "client": "Banco XYZ",
            "title": "Sistema RAG para normativa financiera",
            "scope": "Implementar un sistema RAG self-hosted sobre documentación regulatoria (CNMV, BdE, AI Act) con búsqueda semántica y LLM local.",
            "stack": "Qdrant + Ollama + Qwen 2.5 3B + FastAPI, todo en Docker",
            "timeline": "8-10 semanas",
        }),
        "PDF generado en /app/outputs/propuesta_tecnica_2026-06-03.pdf (210 KB)",
        "Propuesta técnica creada en `outputs/propuesta_tecnica_2026-06-03.pdf`.",
    ),
    ex_single_tool(
        "Genérame un PDF con el informe del sistema",
        tool_call("write_document", template="informe_estado", fields={
            "title": "Reporte automático",
            "date": "2026-06-03",
            "status": "OK",
        }),
        "PDF generado en /app/outputs/reporte_automatico_2026-06-03.pdf",
        "Hecho. PDF en `outputs/reporte_automatico_2026-06-03.pdf`.",
    ),
    ex_single_tool(
        "Documenta lo que hemos hecho",
        tool_call("write_document", template="informe_estado", fields={
            "title": "Documentación de la sesión",
            "date": "2026-06-03",
            "summary": "Sesión de trabajo: setup de RAG, fine-tuning pendiente.",
        }),
        "PDF generado en /app/outputs/documentacion_2026-06-03.pdf",
        "Documentación guardada en `outputs/documentacion_2026-06-03.pdf`.",
    ),
]

# --- plot_metric ---
EXAMPLES += [
    ex_single_tool(
        "Grafica el uso de GPU de los últimos 5 minutos",
        tool_call("plot_metric", metric="gpu_util", range="5m"),
        "Gráfico generado en /app/outputs/gpu_util_5m.png",
        "Aquí tienes el gráfico: `outputs/gpu_util_5m.png`.",
    ),
    ex_single_tool(
        "Muéstrame un plot de latencia",
        tool_call("plot_metric", metric="request_latency", range="1h"),
        "Gráfico generado en /app/outputs/request_latency_1h.png",
        "Gráfico de latencia guardado en `outputs/request_latency_1h.png`.",
    ),
    ex_single_tool(
        "Gráfica de requests por minuto",
        tool_call("plot_metric", metric="requests_per_min", range="15m"),
        "Gráfico generado en /app/outputs/requests_per_min_15m.png",
        "Hecho. Gráfico en `outputs/requests_per_min_15m.png`.",
    ),
    ex_single_tool(
        "Plot de VRAM en las últimas 24h",
        tool_call("plot_metric", metric="vram_usage", range="24h"),
        "Gráfico generado en /app/outputs/vram_usage_24h.png",
        "Listo, el plot está en `outputs/vram_usage_24h.png`.",
    ),
    ex_single_tool(
        "Hazme un chart de la temperatura",
        tool_call("plot_metric", metric="gpu_temp", range="1h"),
        "Gráfico generado en /app/outputs/gpu_temp_1h.png",
        "Aquí está: `outputs/gpu_temp_1h.png`.",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# CATEGORÍA 3: 2-3 TOOLS (multi-step) — ~50 ejemplos
# Enseña: chains, decisiones sobre qué tool llamar después
# ═══════════════════════════════════════════════════════════════════

EXAMPLES += [
    # get_gpu_stats + list_models (los 2 juntos para diagnóstico básico)
    ex_multi_tool(
        "Hazme un diagnóstico básico del sistema",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nTemp: 53°C\nUtil: 30%"),
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
        ],
        "**Diagnóstico del sistema** (2026-06-03):\n\n🟢 **GPU**: 1.8/4 GB VRAM (45%), 30% util, 53°C — todo normal.\n🟢 **Modelos**: 2 instalados — `qwen2.5:3b` (LLM, 1.8 GB) y `bge-small-en-v1.5` (embeddings, 130 MB).\n\nSistema operativo, sin alertas.",
    ),
    ex_multi_tool(
        "Dame un resumen del estado del hardware y los modelos",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
            (tool_call("list_models"), "qwen2.5:3b, bge-small-en-v1.5"),
        ],
        "**Hardware**: RTX 3050 4GB, 1.8/4 GB usados (45%).\n**Modelos**: qwen2.5:3b y bge-small-en-v1.5.\n\nTodo en orden.",
    ),
    ex_multi_tool(
        "Estado del sistema ahora",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
        ],
        "GPU al 45% de VRAM. 2 modelos: qwen2.5:3b y bge-small.",
    ),
    # get_gpu_stats + search_docs
    ex_multi_tool(
        "¿Cabe un modelo 7B en mi GPU? Búscalo en la doc",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%) — Libre: 2.2 GB"),
            (tool_call("search_docs", query="vLLM Qwen 7B VRAM requirements", k=3),
             "[Doc 1] Un Qwen 2.5 7B cuantizado a Q4_K_M ocupa ~4.5 GB. Necesitas >=6 GB de VRAM libre para correrlo con contexto decente."),
        ],
        "Mirando tu GPU: tienes **2.2 GB libres** de los 4 GB. Y según la documentación, un Qwen 2.5 7B cuantizado a Q4 ocupa **~4.5 GB**.\n\n**No te cabe.** Para tu hardware, quédate con modelos 1-3B como qwen2.5:3b.",
    ),
    ex_multi_tool(
        "Voy a añadir una collection nueva. Comprueba la GPU y la info de la actual",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
            (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos, 384 dim, Cosine"),
        ],
        "GPU: 45% VRAM usado, hay sitio.\nColección actual: 62 puntos, 384 dim, Cosine.\n\nAdelante con la nueva (mantén la misma dimensión y distancia para simplificar).",
    ),
    # search_docs + write_document
    ex_multi_tool(
        "Busca info sobre RAG en la doc y hazme un PDF resumen",
        [
            (tool_call("search_docs", query="RAG retrieval augmented generation", k=5),
             "[Doc 1] RAG = Retrieval-Augmented Generation. Patrón que combina retriever + LLM para responder con datos propios sin reentrenar."),
            (tool_call("write_document", template="resumen_ejecutivo", fields={
                "title": "Resumen: RAG",
                "summary": "RAG combina retrieval (Qdrant en nuestro caso) con un LLM generador. Mejora la relevancia y reduce alucinaciones.",
            }),
             "PDF generado en /app/outputs/resumen_rag.pdf"),
        ],
        "He creado el PDF resumen sobre RAG en `outputs/resumen_rag.pdf`.",
    ),
    # list_models + write_document
    ex_multi_tool(
        "Lista los modelos y genera un informe",
        [
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("write_document", template="informe_estado", fields={
                "title": "Modelos instalados",
                "models": "qwen2.5:3b (1.8 GB) + bge-small-en-v1.5 (130 MB)",
            }),
             "PDF en /app/outputs/modelos_informe.pdf"),
        ],
        "Informe generado en `outputs/modelos_informe.pdf`.",
    ),
    # get_gpu_stats + plot_metric
    ex_multi_tool(
        "Dame el estado actual y un plot de la última hora",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
            (tool_call("plot_metric", metric="gpu_util", range="1h"),
             "Plot en /app/outputs/gpu_util_1h.png"),
        ],
        "Estado actual: GPU al 45% de VRAM. Gráfico de la última hora en `outputs/gpu_util_1h.png`.",
    ),
    # 3 tools: get_gpu_stats + list_models + write_document (diagnóstico + PDF)
    ex_multi_tool(
        "Genera un informe PDF completo del estado del sistema",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nTemp: 53°C\nUtil: 30%"),
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("write_document", template="informe_estado", fields={
                "title": "Estado completo del sistema",
                "date": "2026-06-03",
                "gpu": "1.8/4 GB VRAM (45%), 30% util, 53°C",
                "models": "qwen2.5:3b (1.8 GB), bge-small-en-v1.5 (130 MB)",
                "status": "Operativo",
            }),
             "PDF en /app/outputs/estado_completo_2026-06-03.pdf"),
        ],
        "He generado el informe completo en `outputs/estado_completo_2026-06-03.pdf`.",
    ),
    ex_multi_tool(
        "Dame un diagnóstico y guárdalo como PDF",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nUtil: 30%"),
            (tool_call("list_models"), "qwen2.5:3b, bge-small-en-v1.5"),
            (tool_call("write_document", template="informe_estado", fields={
                "title": "Diagnóstico",
                "date": "2026-06-03",
                "summary": "GPU y modelos en estado normal",
            }),
             "PDF generado"),
        ],
        "Diagnóstico guardado en `outputs/diagnostico.pdf`.",
    ),
    # search_docs + search_docs (multi-search)
    ex_multi_tool(
        "Compara cómo se hace fine-tuning en HuggingFace vs cómo se persistiría un índice en LlamaIndex",
        [
            (tool_call("search_docs", query="fine-tuning HuggingFace Trainer", k=3),
             "[Doc 1] Trainer + TrainingArguments, luego trainer.train()."),
            (tool_call("search_docs", query="LlamaIndex persist index", k=3),
             "[Doc 1] index.storage_context.persist('storage') para guardar."),
        ],
        "Comparando los dos procesos:\n\n**Fine-tuning (HuggingFace)**: instancia un `Trainer` con modelo, datasets y `TrainingArguments`, luego `trainer.train()`. Modifica los pesos del modelo.\n\n**Persistir índice (LlamaIndex)**: `index.storage_context.persist('storage')`. Guarda el estado del índice a disco, no reentrena nada.\n\nSon cosas distintas: uno entrena el modelo, el otro guarda artefactos del pipeline.",
    ),
    # 3 tools: search + gpu + list
    ex_multi_tool(
        "Dime qué modelos de embedding existen y recomiéndame uno según mi hardware",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
            (tool_call("list_models"), "bge-small-en-v1.5 (130 MB)"),
        ],
        "Tienes 2.2 GB de VRAM libres. Para embeddings, **bge-small-en-v1.5** (130 MB, 384 dim) es perfecto para tu setup — ya lo tienes y cabe de sobra. Alternativas si necesitaras más idiomas o dimensiones: `bge-base-en-v1.5` (~440 MB) o `bge-m3` (~2.3 GB, multilingüe).",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# CATEGORÍA 4: 4+ TOOLS (chains largas) — ~20 ejemplos
# Enseña: workflows complejos multi-paso
# ═══════════════════════════════════════════════════════════════════

EXAMPLES += [
    ex_multi_tool(
        "Quiero hacer un proyecto de RAG. ¿Qué tengo, qué me falta y hazme un plan?",
        [
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
            (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos, 384 dim, Cosine"),
            (tool_call("search_docs", query="RAG architecture best practices", k=3),
             "[Doc 1] RAG típico: retriever (Qdrant) + LLM (Ollama) + prompt template + parser de fuentes."),
        ],
        "**Estado actual** (tienes):\n- Modelos: `qwen2.5:3b` (LLM) + `bge-small-en-v1.5` (embeddings)\n- GPU: 2.2 GB libres, 45% ocupado\n- Colección RAG: 62 puntos, 384 dim, Cosine\n\n**Plan**:\n1. Ampliar corpus a 200+ chunks (ahora 62 es poco)\n2. Implementar FastAPI con endpoint /ask y retrieval\n3. Evaluar con LLM-as-judge (ya tienes el framework)\n4. Fine-tuning con QLoRA si la fidelidad es baja\n5. Monitoring con Grafana\n\n¿Quieres que empiece por algún paso concreto?",
    ),
    ex_multi_tool(
        "Genera un informe ejecutivo completo: estado, modelos, doc principal, búsqueda de un tema trending",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nTemp: 53°C"),
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
            (tool_call("search_docs", query="AI agents tool calling best practices 2026", k=3),
             "[Doc 1] Tool calling: el LLM genera JSON estructurado con nombre y args, el sistema lo parsea y ejecuta."),
            (tool_call("write_document", template="resumen_ejecutivo", fields={
                "title": "Resumen ejecutivo - Sistema AI",
                "date": "2026-06-03",
                "summary": "Sistema RAG + agente con 6 tools. Listo para Fase 3 (fine-tuning).",
                "key_metrics": "62 chunks, 68 tok/s, GPU al 45% VRAM",
                "trend": "Tool calling es tendencia 2026: el LLM decide cuándo y cómo invocar funciones externas.",
            }),
             "PDF generado en /app/outputs/resumen_ejecutivo_2026-06-03.pdf"),
        ],
        "He generado el resumen ejecutivo completo en `outputs/resumen_ejecutivo_2026-06-03.pdf`. Incluye estado de GPU, modelos, métricas de la colección y la nota sobre tool calling como tendencia 2026.",
    ),
    ex_multi_tool(
        "Compara dos modelos para recomendarme cuál descargar, y dame el estado actual",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
            (tool_call("search_docs", query="Llama 3.2 3B vs Qwen 2.5 3B comparison", k=3),
             "[Doc 1] Qwen 2.5 3B y Llama 3.2 3B rinden similar en benchmarks. Qwen tiende a ser mejor en código, Llama en conversación."),
        ],
        "Mirando tu hardware (2.2 GB libres) y la doc:\n\n**Qwen 2.5 3B** vs **Llama 3.2 3B**: rinden similar. Para tu caso (asistente técnico con tool calling), Qwen 2.5 3B está mejor soportado y tiene mejor performance en código, que es lo que más usarás.\n\n**Recomendación**: quédate con `qwen2.5:3b` (ya lo tienes). Si quieres experimentar, `llama3.2:3b` (~2 GB) cabría.",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# CATEGORÍA 3b: MÁS MULTI-TOOL — completar distribución
# ═══════════════════════════════════════════════════════════════════

EXAMPLES += [
    # search + gpu
    ex_multi_tool(
        "Voy a añadir 50 chunks a la colección. ¿Cabe según la doc y mi hardware?",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
            (tool_call("search_docs", query="Qdrant collection size limits", k=3),
             "[Doc 1] Qdrant escala a millones de puntos por colección en una sola máquina, limitado por RAM/disk."),
        ],
        "GPU: 2.2 GB libres. La doc dice que Qdrant escala a millones de puntos sin problema. **Sí caben 50 chunks más** (pasarías de 62 a 112), y aún te queda VRAM para inferencia.",
    ),
    # gpu + list + search
    ex_multi_tool(
        "Tengo un modelo nuevo para descargar. ¿Caben? ¿Cómo lo descargo?",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
            (tool_call("search_docs", query="ollama pull download model", k=3),
             "[Doc 1] `ollama pull <nombre>` descarga. `ollama ls` lista lo que tienes."),
        ],
        "Tienes 2.2 GB libres. Depende del modelo:\n- `llama3.2:3b` (~2 GB) — cabe justo\n- `qwen2.5:7b` (~4.5 GB) — NO cabe con Ollama ya cargado\n\nPara descargar: `ollama pull <modelo>`.",
    ),
    # search + write
    ex_multi_tool(
        "Busca info sobre RAG y hazme un resumen en PDF",
        [
            (tool_call("search_docs", query="RAG retrieval augmented generation", k=5),
             "[Doc 1] RAG = Retrieval-Augmented Generation."),
            (tool_call("write_document", template="resumen_ejecutivo", fields={
                "title": "Resumen sobre RAG",
                "summary": "RAG combina retrieval (Qdrant) con un LLM generador (Ollama).",
            }),
             "PDF en /app/outputs/resumen_rag.pdf"),
        ],
        "Hecho. Resumen en `outputs/resumen_rag.pdf`.",
    ),
    # list + write
    ex_multi_tool(
        "Documenta los modelos instalados en un PDF",
        [
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("write_document", template="informe_estado", fields={
                "title": "Modelos instalados",
                "models": "qwen2.5:3b (1.8 GB), bge-small-en-v1.5 (130 MB)",
            }),
             "PDF generado"),
        ],
        "PDF en `outputs/modelos_informe.pdf`.",
    ),
    # gpu + plot
    ex_multi_tool(
        "Cómo está la GPU ahora? Hazme un plot del último minuto",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
            (tool_call("plot_metric", metric="gpu_util", range="1m"),
             "Plot en /app/outputs/gpu_util_1m.png"),
        ],
        "Actual: 1.8/4 GB VRAM (45%). Plot del último minuto en `outputs/gpu_util_1m.png`.",
    ),
    # search + list
    ex_multi_tool(
        "Qué modelo usar para embeddings y qué tengo disponible?",
        [
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("search_docs", query="best embedding model 2026", k=3),
             "[Doc 1] bge-small-en-v1.5 es excelente para inglés en hardware limitado."),
        ],
        "Tienes `bge-small-en-v1.5` (130 MB, 384 dim). Es ideal para tu hardware. Para español, considera `bge-m3` (~2.3 GB, multilingüe).",
    ),
    # search + gpu
    ex_multi_tool(
        "Mi modelo va lento, búscalo en la doc y mira la GPU",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nUtil: 30%"),
            (tool_call("search_docs", query="Ollama slow inference GPU underutilized", k=3),
             "[Doc 1] Si la GPU está al 30% y la inferencia es lenta, suele ser porque el modelo es pequeño y el batch/batching no aplica, o porque hay cuello de botella en CPU/RAM."),
        ],
        "GPU al 30% util, 1.8/4 GB VRAM. No es cuello de botella GPU. La doc sugiere que con modelos pequeños (3B) el compute queda infrautilizado. Es **normal**. Si quieres más velocidad, lo único realista es cuantizar más agresivo (Q4→Q3) o usar un modelo más pequeño (1.5B).",
    ),
    # write + write (multi-template)
    ex_multi_tool(
        "Genera un informe del sistema Y un resumen ejecutivo",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
            (tool_call("list_models"), "qwen2.5:3b, bge-small-en-v1.5"),
            (tool_call("write_document", template="informe_estado", fields={
                "title": "Informe del sistema",
                "summary": "Todo OK",
            }),
             "PDF 1 en /app/outputs/informe.pdf"),
            (tool_call("write_document", template="resumen_ejecutivo", fields={
                "title": "Resumen ejecutivo",
                "summary": "Sistema operativo",
            }),
             "PDF 2 en /app/outputs/resumen.pdf"),
        ],
        "Dos PDFs generados:\n- `outputs/informe.pdf` (estado del sistema)\n- `outputs/resumen.pdf` (resumen ejecutivo)",
    ),
    # 3 tools: gpu + search + list
    ex_multi_tool(
        "Diagnosticame el sistema y busca en la doc si hay issues conocidos con mi setup",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nTemp: 53°C\nUtil: 30%"),
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("search_docs", query="Qwen 2.5 3B Ollama known issues Windows", k=3),
             "[Doc 1] Sin issues reportados para Qwen 2.5 3B en Ollama Windows con driver NVIDIA reciente."),
        ],
        "Diagnóstico:\n- GPU: 45% VRAM, 30% util, 53°C — todo normal\n- Modelos: qwen2.5:3b (1.8 GB) + bge-small-en-v1.5 (130 MB)\n- Issues conocidos: ninguno. Tu setup está limpio.",
    ),
    # gpu + write
    ex_multi_tool(
        "Guarda el estado de la GPU en un PDF para reporte diario",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nTemp: 53°C\nUtil: 30%"),
            (tool_call("write_document", template="informe_estado", fields={
                "title": "Reporte diario",
                "date": "2026-06-03",
                "gpu": "1.8/4 GB VRAM, 53°C, 30% util",
            }),
             "PDF en /app/outputs/reporte_diario.pdf"),
        ],
        "PDF del reporte diario guardado en `outputs/reporte_diario.pdf`.",
    ),
    # plot + write
    ex_multi_tool(
        "Genera un plot de GPU y añádelo a un informe",
        [
            (tool_call("plot_metric", metric="gpu_util", range="1h"),
             "Plot en /app/outputs/gpu_util_1h.png"),
            (tool_call("write_document", template="informe_estado", fields={
                "title": "Informe con gráfico",
                "include_plot": "outputs/gpu_util_1h.png",
            }),
             "PDF en /app/outputs/informe_con_plot.pdf"),
        ],
        "Hecho. Plot en `outputs/gpu_util_1h.png` y PDF con el plot embebido en `outputs/informe_con_plot.pdf`.",
    ),
    # search + list + write
    ex_multi_tool(
        "Busca cómo usar vLLM, dime si lo tengo, y genera un informe",
        [
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("search_docs", query="vLLM serve model Ollama alternative", k=3),
             "[Doc 1] vLLM es un motor de inferencia optimizado para GPUs grandes (24+ GB). Ollama es mejor para hardware modesto."),
        ],
        "No tienes vLLM (tienes Ollama con qwen2.5:3b y bge-small). La doc sugiere que **vLLM no es para ti** (necesita 24+ GB VRAM). Quédate con Ollama.",
    ),
    # 2 tools: gpu + search, otra variación
    ex_multi_tool(
        "Estoy pensando en fine-tuning. Búscalo en la doc y mira mi GPU",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
            (tool_call("search_docs", query="QLoRA fine-tuning 4GB VRAM small model", k=3),
             "[Doc 1] QLoRA permite fine-tuning de modelos 1-3B en GPUs de 4 GB con Unsloth. Qwen 2.5 1.5B es ideal."),
        ],
        "Tu hardware (2.2 GB libres) **sí permite fine-tuning** con QLoRA + Unsloth, pero solo para modelos pequeños (1-3B). La doc recomienda Qwen 2.5 1.5B para tu caso. Perfecto para tu proyecto.",
    ),
    # 3 tools combinados
    ex_multi_tool(
        "Comparativa entre lo que tengo y lo recomendado para embeddings",
        [
            (tool_call("list_models"), "bge-small-en-v1.5 (130 MB)"),
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
            (tool_call("search_docs", query="embedding model comparison 2026 BGE multilingual", k=3),
             "[Doc 1] bge-small-en-v1.5 (inglés), bge-base-en-v1.5 (inglés, mejor calidad), bge-m3 (multilingüe, ~2.3 GB)."),
        ],
        "Comparativa:\n- **Lo que tienes**: bge-small-en-v1.5 (inglés, 130 MB, 384 dim)\n- **Recomendado si necesitas español**: bge-m3 (multilingüe, 2.3 GB, 1024 dim)\n- **Mejor calidad en inglés**: bge-base-en-v1.5 (440 MB, 768 dim)\n\nCon tu hardware (2.2 GB libres) cabría bge-m3. Si tu RAG es solo en inglés, quédate con el actual.",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# CATEGORÍA 4b: MÁS CHAINS (4+ tools) — completar distribución
# ═══════════════════════════════════════════════════════════════════

EXAMPLES += [
    ex_multi_tool(
        "Audit completo del sistema: hardware, modelos, colección, búsqueda de issues, y hazme un PDF",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nTemp: 53°C\nUtil: 30%"),
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos, 384 dim, Cosine"),
            (tool_call("search_docs", query="best practices RAG small model 4GB", k=3),
             "[Doc 1] Con 4GB: usa modelos 1-3B, embeddings small, y corpus curado (no masivo)."),
            (tool_call("write_document", template="informe_estado", fields={
                "title": "Auditoría completa del sistema",
                "date": "2026-06-03",
                "hardware": "RTX 3050 4GB, 45% VRAM",
                "models": "qwen2.5:3b, bge-small",
                "collection": "62 puntos, 384 dim",
                "recommendations": "Setup actual alineado con best practices para 4GB",
            }),
             "PDF en /app/outputs/auditoria.pdf"),
        ],
        "Auditoría completa en `outputs/auditoria.pdf`. Incluye hardware, modelos, colección y recomendaciones. Tu setup está alineado con las best practices para GPUs pequeñas.",
    ),
    ex_multi_tool(
        "Genera un dashboard completo: estado, modelos, métricas, plot y PDF resumen",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nTemp: 53°C"),
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
            (tool_call("plot_metric", metric="gpu_util", range="1h"),
             "Plot en /app/outputs/gpu_util_1h.png"),
            (tool_call("write_document", template="resumen_ejecutivo", fields={
                "title": "Dashboard resumen",
                "summary": "Estado OK, modelos cargados, colección poblada",
            }),
             "PDF en /app/outputs/dashboard.pdf"),
        ],
        "Dashboard generado:\n- Plot: `outputs/gpu_util_1h.png`\n- PDF: `outputs/dashboard.pdf`",
    ),
    ex_multi_tool(
        "Diagnóstico + búsqueda de problemas + recomendaciones + plan de acción en PDF",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nUtil: 30%"),
            (tool_call("list_models"), "qwen2.5:3b, bge-small"),
            (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos, 384 dim"),
            (tool_call("search_docs", query="RAG improvements next steps 2026", k=3),
             "[Doc 1] Mejoras RAG: ampliar corpus, re-ranking, fine-tuning del LLM, evaluation continua."),
        ],
        "Diagnóstico OK. Plan de acción basado en la doc:\n1. Ampliar corpus (ahora 62 chunks es poco)\n2. Evaluar con LLM-as-judge (ya tienes el framework)\n3. Fine-tuning con QLoRA si la fidelidad es baja\n4. Re-ranking para mejorar context_precision\n\n¿Empezamos por ampliar el corpus?",
    ),
    ex_multi_tool(
        "Comparativa: qué modelo me recomiendas, qué tengo, y búscalo en la doc",
        [
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)"),
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
            (tool_call("search_docs", query="best LLM 3B 2026 Spanish support", k=3),
             "[Doc 1] Qwen 2.5 3B y Llama 3.2 3B son los mejores en su tamaño. Qwen soporta bien español."),
            (tool_call("search_docs", query="Qwen 2.5 3B vs Llama 3.2 3B Spanish", k=3),
             "[Doc 1] Qwen 2.5 3B es ligeramente mejor en español. Llama 3.2 3B es mejor en inglés conversacional."),
        ],
        "Recomendación: **quédate con qwen2.5:3b**. Es el que tienes, soporta bien español (la doc lo confirma), y rinde al nivel de Llama 3.2 3B o mejor en benchmarks técnicos.",
    ),
    ex_multi_tool(
        "Onboarding: explica mi setup a un nuevo dev, búscalo en la doc, y hazme un PDF",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
            (tool_call("list_models"), "qwen2.5:3b, bge-small-en-v1.5"),
            (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
            (tool_call("search_docs", query="RAG architecture components Ollama Qdrant", k=3),
             "[Doc 1] RAG típico: Ollama (LLM) + Qdrant (vector DB) + FastAPI (orquestación) + embeddings."),
            (tool_call("write_document", template="propuesta_tecnica", fields={
                "title": "Onboarding técnico",
                "stack": "Ollama (Qwen 2.5 3B) + Qdrant (62 chunks) + BGE-small embeddings + FastAPI",
                "hardware": "RTX 3050 4GB",
                "next_steps": "Fase 3: fine-tuning, Fase 4: monitoring",
            }),
             "PDF en /app/outputs/onboarding.pdf"),
        ],
        "PDF de onboarding creado en `outputs/onboarding.pdf`. Cubre stack, hardware, y siguientes pasos.",
    ),
    ex_multi_tool(
        "Estado completo + plot + PDF para reportar a mi manager",
        [
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)"),
            (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
            (tool_call("plot_metric", metric="requests_per_min", range="24h"),
             "Plot en /app/outputs/rpm_24h.png"),
            (tool_call("write_document", template="resumen_ejecutivo", fields={
                "title": "Reporte para manager",
                "summary": "Sistema RAG operativo, 62 docs indexados, GPU al 45%",
                "achievements": "Fase 0-2 cerradas",
            }),
             "PDF en /app/outputs/reporte_manager.pdf"),
        ],
        "Reporte completo en `outputs/reporte_manager.pdf`. Incluye plot de tráfico de 24h.",
    ),
    ex_multi_tool(
        "Comparación de dos modelos de embedding y recomendación",
        [
            (tool_call("list_models"), "bge-small-en-v1.5 (130 MB)"),
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
            (tool_call("search_docs", query="BGE small vs BGE base comparison", k=3),
             "[Doc 1] bge-small (130 MB, 384 dim) vs bge-base (440 MB, 768 dim). Base es más preciso, small es más rápido."),
            (tool_call("search_docs", query="embedding model Spanish multilingual 2026", k=3),
             "[Doc 1] bge-m3 soporta 100+ idiomas, 1024 dim, multilingüe. Ideal si tu corpus es multilingüe."),
        ],
        "Comparativa:\n- **bge-small** (lo tienes, 130 MB): rápido, solo inglés, 384 dim\n- **bge-base** (440 MB): mejor calidad en inglés, 768 dim\n- **bge-m3** (2.3 GB): multilingüe, 1024 dim\n\nCon 2.2 GB libres te cabe bge-m3. Si tu corpus es solo en inglés, bge-base es el sweet spot. Si tienes español + otros idiomas, bge-m3.",
    ),
    ex_multi_tool(
        "Investigación: mejores prácticas de tool calling + cómo lo implementarías",
        [
            (tool_call("search_docs", query="tool calling LLM best practices 2026", k=3),
             "[Doc 1] Tool calling: usa JSON estructurado, system prompt claro, ejemplos en el prompt, y termina con marcador de stop."),
            (tool_call("search_docs", query="fine-tuning small model tool calling dataset", k=3),
             "[Doc 1] Para enseñar tool calling a un modelo pequeño, necesitas 100-500 ejemplos curados con formato consistente."),
            (tool_call("list_models"), "qwen2.5:3b (1.8 GB)"),
            (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        ],
        "Plan basado en la doc y tu setup:\n\n1. **Formato**: `<tool_call>{...}</tool_call>` con JSON estructurado\n2. **System prompt**: listar tools, formato, reglas (parar cuando termines, etc.)\n3. **Dataset**: 100-500 ejemplos curados con tool/no-tool/multi-tool/refuse\n4. **Fine-tuning**: QLoRA en qwen2.5:3b con tu 4GB de VRAM — viable\n5. **Validación**: tu A/B eval con la nueva columna `rag_ft`\n\n¿Quieres que arranque con el dataset?",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# EXPANSIÓN: más cobertura, edge cases, multi-idioma
# ═══════════════════════════════════════════════════════════════════

# --- Más direct (15 adicionales) ---
EXAMPLES += [
    ex_direct("¿Cuánto es 25 * 4?", "25 por 4 es 100."),
    ex_direct("¿Cuál es la suma de 8 y 7?", "8 + 7 = 15."),
    ex_direct("¿Qué día es hoy?", "No tengo acceso a la fecha actual. Tu sistema puede proporcionármela si me la pasas en el prompt."),
    ex_direct("¿Quién descubrió América?", "Cristóbal Colón llegó a América en 1492."),
    ex_direct("¿Cuántos huesos tiene el cuerpo humano?", "El cuerpo humano adulto tiene 206 huesos."),
    ex_direct("¿Qué es HTTP?", "HTTP (HyperText Transfer Protocol) es el protocolo de comunicación entre clientes y servidores web. La versión actual es HTTP/2, con HTTP/3 (basado en QUIC) ganando adopción."),
    ex_direct("¿Qué es un container Docker?", "Un container Docker es una unidad ligera y portable que empaqueta una aplicación con todas sus dependencias, basándose en el sistema de archivos y namespaces del kernel de Linux."),
    ex_direct("¿Qué es JSON?", "JSON (JavaScript Object Notation) es un formato ligero de intercambio de datos, fácil de leer y escribir para humanos, fácil de parsear para máquinas."),
    ex_direct("¿Qué es una API REST?", "REST (Representational State Transfer) es un estilo arquitectónico para APIs web que usa HTTP y operaciones estándar (GET, POST, PUT, DELETE) sobre recursos."),
    ex_direct("¿Cómo se dice 'gracias' en inglés?", "Se dice 'thank you'."),
    ex_direct("¿Cuál es la moneda de Japón?", "El yen (JPY) es la moneda de Japón."),
    ex_direct("¿Quién pintó la Mona Lisa?", "Leonardo da Vinci pintó la Mona Lisa."),
    ex_direct("¿Qué es el Big Bang?", "El Big Bang es la teoría cosmológica que describe el origen del universo como una expansión desde un estado de densidad y temperatura extremadamente altas hace ~13.800 millones de años."),
    ex_direct("¿Por qué el cielo es azul?", "El cielo es azul por la dispersión de Rayleigh: la atmósfera dispersa más la luz azul (longitud de onda corta) que la roja, y por eso vemos el cielo de ese color."),
    ex_direct("Recomiéndame una librería de Python para ML", "Las más usadas son scikit-learn (ML clásico), PyTorch y TensorFlow (deep learning), y HuggingFace Transformers (modelos preentrenados, especialmente LLMs). Para tu caso con Ollama, no necesitas ninguna: Ollama expone API HTTP."),
]

# --- Más 1-tool: variaciones de phrasings (40 adicionales) ---

# search_docs: 10 más
EXAMPLES += [
    ex_single_tool(
        "Cómo se usa el retriever en LlamaIndex?",
        tool_call("search_docs", query="retriever LlamaIndex usage", k=3),
        "[Doc 1] El retriever se instancia con `index.as_retriever()` y se llama con `retriever.retrieve(query)`.",
        "En LlamaIndex creas el retriever con `index.as_retriever(similarity_top_k=5)` y lo usas con `retriever.retrieve('tu query')`.",
    ),
    ex_single_tool(
        "que es el streaming de tokens",
        tool_call("search_docs", query="streaming tokens LLM inference", k=3),
        "[Doc 1] El streaming emite tokens uno a uno según se generan, en vez de esperar la respuesta completa. Reduce latencia percibida.",
        "El streaming de tokens emite cada palabra (token) según se genera, en vez de esperar a tener la respuesta entera. Mejora la latencia percibida: ves la respuesta aparecer letra a letra.",
    ),
    ex_single_tool(
        "Cómo cuantizar un modelo?",
        tool_call("search_docs", query="model quantization Q4 Q8 GGUF", k=3),
        "[Doc 1] Cuantización reduce la precisión de los pesos (32-bit → 4/8 bit) para ahorrar memoria. Q4 es el sweet spot calidad/memoria.",
        "Para cuantizar, usa herramientas como llama.cpp (GGUF), bitsandbytes (4/8-bit), o GPTQ. El formato Q4_K_M es el sweet spot: ~4.5 bits por parámetro, calidad casi idéntica al original.",
    ),
    ex_single_tool(
        "qué es sentence transformers",
        tool_call("search_docs", query="sentence transformers embeddings", k=3),
        "[Doc 1] sentence-transformers es una librería Python que genera embeddings de texto optimizados para búsqueda semántica. Incluye modelos como BGE, E5, MiniLM.",
        "sentence-transformers es una librería de HuggingFace para generar embeddings de frases optimizados para similitud semántica. Incluye modelos como `BAAI/bge-small-en-v1.5` (el que usamos), `all-MiniLM-L6-v2`, y muchos más.",
    ),
    ex_single_tool(
        "Como instalo Ollama en Mac",
        tool_call("search_docs", query="Ollama install Mac Linux Windows", k=3),
        "[Doc 1] `brew install ollama` en Mac, `curl -fsSL https://ollama.com/install.sh | sh` en Linux, descargable desde ollama.com en Windows.",
        "En Mac: `brew install ollama` o descarga desde ollama.com. En Linux: `curl -fsSL https://ollama.com/install.sh | sh`. En Windows: instalador desde ollama.com (lo que usaste tú).",
    ),
    ex_single_tool(
        "Ollama corre en GPU?",
        tool_call("search_docs", query="Ollama GPU CUDA", k=3),
        "[Doc 1] Sí, Ollama detecta automáticamente tu GPU NVIDIA y la usa para inferencia. Soporta CUDA, Metal (Mac), ROCm (AMD).",
        "Sí, Ollama detecta tu GPU automáticamente y la usa para inferencia. Soporta CUDA (NVIDIA), Metal (Mac) y ROCm (AMD). En tu caso con RTX 3050, usa CUDA.",
    ),
    ex_single_tool(
        "Cómo sirve un modelo de HuggingFace con vLLM?",
        tool_call("search_docs", query="vLLM serve HuggingFace model", k=3),
        "[Doc 1] `vllm serve <modelo>` arranca un servidor compatible con OpenAI en el puerto 8000. Requiere GPUs grandes (24+ GB).",
        "vLLM se usa con `vllm serve <modelo>` (ej: `vllm serve Qwen/Qwen2.5-3B-Instruct`). Arranca un servidor compatible con OpenAI en :8000. **Pero requiere GPUs grandes (24+ GB)** — no es para tu RTX 3050 4GB.",
    ),
    ex_single_tool(
        "Cual es la diferencia entre Ollama y vLLM?",
        tool_call("search_docs", query="Ollama vs vLLM comparison", k=3),
        "[Doc 1] Ollama es ideal para hardware modesto y un solo modelo. vLLM está optimizado para producción con GPUs grandes y PagedAttention.",
        "**Ollama**: ideal para hardware modesto (como tu RTX 3050), un modelo a la vez, fácil de usar.\n**vLLM**: producción seria, GPUs grandes (A100/H100), PagedAttention para alto throughput.\n\nTú quieres Ollama.",
    ),
    ex_single_tool(
        "qué es un LLM-as-judge",
        tool_call("search_docs", query="LLM as judge evaluation", k=3),
        "[Doc 1] LLM-as-judge usa un modelo de lenguaje para evaluar respuestas de otro modelo, con un prompt que define la rúbrica. Común para métricas como faithfulness o relevance.",
        "LLM-as-judge es una técnica de evaluación donde un LLM (el juez) puntúa las respuestas de otro LLM siguiendo una rúbrica. Es estándar para métricas como faithfulness, answer relevance, etc. **Tu propio eval lo usa** (Qwen 2.5 3B como juez).",
    ),
    ex_single_tool(
        "como se hace un retriever custom",
        tool_call("search_docs", query="custom retriever LlamaIndex BaseRetriever", k=3),
        "[Doc 1] Subclasea `BaseRetriever` de LlamaIndex e implementa `_retrieve(query)`.",
        "Para un retriever custom en LlamaIndex, subclaseas `BaseRetriever` e implementas el método `_retrieve(query)` que devuelve una lista de `NodeWithScore`. Útil cuando quieres lógica de retrieval custom (filtros, re-ranking, multi-source, etc.).",
    ),
]

# list_models: 5 más
EXAMPLES += [
    ex_single_tool("modelos disponibles", tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)", "Tienes 2 modelos: `qwen2.5:3b` y `bge-small-en-v1.5`."),
    ex_single_tool("qué llms tengo", tool_call("list_models"), "qwen2.5:3b (1.8 GB)", "Solo `qwen2.5:3b` como LLM."),
    ex_single_tool("tengo embedding model?", tool_call("list_models"), "bge-small-en-v1.5 (130 MB) — embeddings", "Sí, `bge-small-en-v1.5` (130 MB)."),
    ex_single_tool("qué modelos de chat hay", tool_call("list_models"), "qwen2.5:3b (1.8 GB)", "Para chat: `qwen2.5:3b`."),
    ex_single_tool("modelos en disco", tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)", "Tienes 2 modelos, 1.93 GB total en disco."),
]

# get_gpu_stats: 5 más
EXAMPLES += [
    ex_single_tool("uso de GPU ahora", tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nUtil: 30%\nTemp: 53°C", "GPU al 45% VRAM, 30% util, 53°C."),
    ex_single_tool("temperatura", tool_call("get_gpu_stats"), "Temp: 53°C", "53°C, en rango normal."),
    ex_single_tool("hay espacio para otro modelo?", tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB — Libre: 2.2 GB", "Tienes 2.2 GB libres. Depende del modelo: BGE-small (130 MB) sí, un LLM 7B no."),
    ex_single_tool("carga de la GPU", tool_call("get_gpu_stats"), "Util: 30%", "Carga actual: 30%. Baja, hay margen."),
    ex_single_tool("como anda la grafica", tool_call("get_gpu_stats"), "VRAM: 45%\nTemp: 53°C\nUtil: 30%", "La GPU está bien: 45% VRAM, 30% util, 53°C."),
]

# get_collection_info: 10 más (era la más débil)
EXAMPLES += [
    ex_single_tool("datos de la colección", tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos, 384 dim, Cosine", "La colección `ai_engineering_docs` tiene 62 puntos, 384 dim, Cosine."),
    ex_single_tool("que coleccion tengo", tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos", "Tienes la colección `ai_engineering_docs` con 62 puntos."),
    ex_single_tool("numero de documentos en qdrant", tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos", "62 documentos indexados."),
    ex_single_tool("dim del vector store", tool_call("get_collection_info", name="ai_engineering_docs"), "384 dim", "384 dimensiones."),
    ex_single_tool("tamaño del indice", tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos, 384 dim, Cosine", "Índice: 62 puntos, 384 dim, Cosine."),
    ex_single_tool("metadata de la collection", tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos, 384 dim, Cosine", "Colección: 62 puntos, 384 dim, Cosine."),
    ex_single_tool("puntos indexados", tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos", "62 puntos indexados."),
    ex_single_tool("info qdrant", tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos, 384 dim, Cosine", "Qdrant: 62 puntos, 384 dim, Cosine."),
    ex_single_tool("hay datos en el vector store", tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos", "Sí, 62 puntos."),
    ex_single_tool("distancia del vector store", tool_call("get_collection_info", name="ai_engineering_docs"), "Cosine", "Usa Cosine similarity."),
]

# write_document: 5 más
EXAMPLES += [
    ex_single_tool("hazme un email al cliente", tool_call("write_document", template="email_cliente", fields={
        "to": "cliente@example.com", "subject": "Avance del proyecto",
        "body": "Le informo del avance: hemos completado la integración del RAG.",
    }), "PDF en /app/outputs/email_cliente.pdf", "Email generado en `outputs/email_cliente.pdf`."),
    ex_single_tool("documento técnico para investor", tool_call("write_document", template="propuesta_tecnica", fields={
        "title": "AI Engineering Portfolio",
        "client": "VC", "scope": "Sistema RAG con fine-tuning",
    }), "PDF en /app/outputs/propuesta_inversor.pdf", "PDF en `outputs/propuesta_inversor.pdf`."),
    ex_single_tool("resumen semanal", tool_call("write_document", template="informe_estado", fields={
        "title": "Resumen semanal", "summary": "Avance de la semana en el proyecto AI",
    }), "PDF en /app/outputs/resumen_semanal.pdf", "Hecho: `outputs/resumen_semanal.pdf`."),
    ex_single_tool("informe técnico completo", tool_call("write_document", template="informe_estado", fields={
        "title": "Informe técnico",
        "summary": "Estado y arquitectura del sistema",
    }), "PDF en /app/outputs/informe_tecnico.pdf", "PDF en `outputs/informe_tecnico.pdf`."),
    ex_single_tool("presentación para cliente", tool_call("write_document", template="propuesta_tecnica", fields={
        "title": "Presentación al cliente", "client": "Empresa X",
    }), "PDF en /app/outputs/presentacion.pdf", "PDF creado en `outputs/presentacion.pdf`."),
]

# plot_metric: 10 más (era la más débil)
EXAMPLES += [
    ex_single_tool("plot de gpu", tool_call("plot_metric", metric="gpu_util", range="5m"), "Plot en /app/outputs/gpu_util_5m.png", "Aquí: `outputs/gpu_util_5m.png`."),
    ex_single_tool("grafica temperatura gpu", tool_call("plot_metric", metric="gpu_temp", range="15m"), "Plot en /app/outputs/gpu_temp_15m.png", "Plot: `outputs/gpu_temp_15m.png`."),
    ex_single_tool("plot de uso de vram", tool_call("plot_metric", metric="vram_usage", range="1h"), "Plot en /app/outputs/vram_usage_1h.png", "Gráfico: `outputs/vram_usage_1h.png`."),
    ex_single_tool("rendimiento del sistema ultima hora", tool_call("plot_metric", metric="request_latency", range="1h"), "Plot en /app/outputs/request_latency_1h.png", "Gráfico de latencia: `outputs/request_latency_1h.png`."),
    ex_single_tool("cuanta vram he usado hoy", tool_call("plot_metric", metric="vram_usage", range="24h"), "Plot en /app/outputs/vram_usage_24h.png", "Plot: `outputs/vram_usage_24h.png`."),
    ex_single_tool("chart de requests", tool_call("plot_metric", metric="requests_per_min", range="1h"), "Plot en /app/outputs/rpm_1h.png", "Chart: `outputs/rpm_1h.png`."),
    ex_single_tool("gráfico del día", tool_call("plot_metric", metric="gpu_util", range="24h"), "Plot en /app/outputs/gpu_util_24h.png", "Plot del día: `outputs/gpu_util_24h.png`."),
    ex_single_tool("visualiza el uso", tool_call("plot_metric", metric="vram_usage", range="1h"), "Plot en /app/outputs/vram_usage_1h.png", "Visualización: `outputs/vram_usage_1h.png`."),
    ex_single_tool("plot últimas 24h", tool_call("plot_metric", metric="gpu_util", range="24h"), "Plot en /app/outputs/gpu_util_24h.png", "Plot 24h: `outputs/gpu_util_24h.png`."),
    ex_single_tool("stats visualmente", tool_call("plot_metric", metric="vram_usage", range="5m"), "Plot en /app/outputs/vram_usage_5m.png", "Gráfico: `outputs/vram_usage_5m.png`."),
]

# --- Más 2-3 tools (50 adicionales) ---

# get_gpu_stats + list_models: 8 más
EXAMPLES += [
    ex_multi_tool("resumen rapido del sistema", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
    ], "GPU 45% VRAM, 2 modelos cargados (qwen2.5:3b + bge-small). Todo OK."),
    ex_multi_tool("dame el setup", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small-en-v1.5"),
    ], "Setup: RTX 3050 4GB (45% VRAM usada), 2 modelos (qwen2.5:3b LLM, bge-small embeddings)."),
    ex_multi_tool("check rapido", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b (1.8 GB)"),
    ], "GPU al 45%, qwen2.5:3b cargado. Todo bien."),
    ex_multi_tool("estado actual del sistema", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
    ], "Estado: GPU 45% VRAM, modelos qwen2.5:3b + bge-small cargados."),
    ex_multi_tool("qué tengo en ejecución", [
        (tool_call("list_models"), "qwen2.5:3b (1.8 GB)"),
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
    ], "qwen2.5:3b (1.8 GB) cargado en GPU al 45%."),
    ex_multi_tool("reporte de sistema ahora", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nTemp: 53°C"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
    ], "GPU 45% VRAM, 53°C. 2 modelos cargados."),
    ex_multi_tool("memoria gpu y modelos", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b (1.8 GB)"),
    ], "VRAM: 45% usado (1.8/4 GB). Modelos: qwen2.5:3b."),
    ex_multi_tool("status", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b"),
    ], "Status: GPU 45% VRAM, qwen2.5:3b cargado."),
]

# get_gpu_stats + write_document: 5 más
EXAMPLES += [
    ex_multi_tool("informe rapido del sistema", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("write_document", template="informe_estado", fields={"title": "Informe", "summary": "Sistema OK"}),
         "PDF en /app/outputs/informe.pdf"),
    ], "PDF: `outputs/informe.pdf`."),
    ex_multi_tool("snapshop del sistema", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("write_document", template="informe_estado", fields={"title": "Snapshot", "date": "2026-06-03"}),
         "PDF"),
    ], "Snapshot guardado en PDF."),
    ex_multi_tool("informe diario", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("write_document", template="informe_estado", fields={"title": "Reporte diario", "summary": "Todo OK"}),
         "PDF"),
    ], "Reporte diario en PDF."),
    ex_multi_tool("status guardado", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("write_document", template="informe_estado", fields={"title": "Status"}),
         "PDF"),
    ], "Status guardado en PDF."),
    ex_multi_tool("reporte para mi yo del futuro", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("write_document", template="informe_estado", fields={"title": "Carta al yo futuro", "summary": "Estado al 2026-06-03"}),
         "PDF"),
    ], "Carta al yo futuro guardada en PDF."),
]

# search_docs + get_gpu_stats: 8 más
EXAMPLES += [
    ex_multi_tool("puedo correr un 7B con mi setup", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
        (tool_call("search_docs", query="Qwen 2.5 7B VRAM requirements", k=3),
         "[Doc 1] Qwen 2.5 7B cuantizado Q4 ocupa ~4.5 GB."),
    ], "No. Tienes 2.2 GB libres, necesitas 4.5 GB para un 7B. Quédate con modelos 1-3B."),
    ex_multi_tool("cabe un 1.5B", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
        (tool_call("search_docs", query="Qwen 2.5 1.5B VRAM", k=2),
         "[Doc 1] Qwen 2.5 1.5B cuantizado Q4 ocupa ~1.1 GB."),
    ], "Sí, 1.5B Q4 ocupa ~1.1 GB, tienes 2.2 GB libres. Sobra."),
    ex_multi_tool("voy a fine-tunear, búscalo y mira GPU", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nLibre: 2.2 GB"),
        (tool_call("search_docs", query="QLoRA fine-tuning Unsloth 4GB VRAM", k=3),
         "[Doc 1] QLoRA con Unsloth cabe modelos 1-3B en GPUs 4GB."),
    ], "Con 2.2 GB libres, QLoRA + Unsloth te permite fine-tunear Qwen 1.5B-3B. Viable."),
    ex_multi_tool("dame un tutorial rápido de QLoRA en mi setup", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("search_docs", query="QLoRA tutorial Unsloth", k=3),
         "[Doc 1] Instala unsloth, carga el modelo 4-bit, configura LoRA r=8, entrena con SFTTrainer."),
    ], "Tutorial rápido:\n1. `pip install unsloth`\n2. Carga Qwen 2.5 1.5B en 4-bit\n3. Configura LoRA (r=8, alpha=16)\n4. Entrena 1-3 epochs con tu dataset"),
    ex_multi_tool("qué hardware necesito para embeddings grandes", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("search_docs", query="bge-m3 VRAM requirements", k=3),
         "[Doc 1] bge-m3 ocupa ~2.3 GB para inferencia."),
    ], "bge-m3 (2.3 GB) te cabe con tus 4 GB. Si quieres algo más grande, bge-large ocupa ~1.3 GB pero con peor rendimiento que m3."),
    ex_multi_tool("mi Ollama es lento", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nUtil: 30%"),
        (tool_call("search_docs", query="Ollama slow inference", k=3),
         "[Doc 1] Si GPU está infrautilizada, es porque el modelo es pequeño. Cuantización más agresiva ayuda."),
    ], "GPU al 30% util. Con un modelo 3B es normal, no es cuello de botella GPU. Si quieres más velocidad, cuantiza más (Q4→Q3) o usa 1.5B."),
    ex_multi_tool("hay alternativa a Ollama más rápida", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("search_docs", query="Ollama alternatives small GPU", k=3),
         "[Doc 1] llama.cpp, LM Studio, Jan son alternativas para hardware modesto."),
    ], "Para tu hardware: llama.cpp (el motor detrás de Ollama) o LM Studio. Pero Ollama ya es la mejor opción en CLI. Te quedas con Ollama."),
    ex_multi_tool("recomiéndame un modelo de embedding multilingüe", [
        (tool_call("list_models"), "bge-small-en-v1.5 (inglés)"),
        (tool_call("search_docs", query="multilingual embedding model Spanish 2026", k=3),
         "[Doc 1] bge-m3 es multilingüe (100+ idiomas), 1024 dim, ~2.3 GB."),
    ], "**bge-m3** es multilingüe, soporta español, ocupa 2.3 GB. Te cabe con tu hardware. Si tu corpus es solo en inglés, quédate con bge-small que ya tienes."),
]

# search_docs + list_models: 5 más
EXAMPLES += [
    ex_multi_tool("qué modelo de chat me recomiendas", [
        (tool_call("list_models"), "qwen2.5:3b (1.8 GB)"),
        (tool_call("search_docs", query="best chat model 3B 2026", k=3),
         "[Doc 1] Qwen 2.5 3B y Llama 3.2 3B son los mejores. Qwen mejor en código, Llama en conversación."),
    ], "Ya tienes **qwen2.5:3b**, que es de los mejores en su tamaño. Para chat general es top."),
    ex_multi_tool("recomiéndame modelo de embedding", [
        (tool_call("list_models"), "bge-small-en-v1.5"),
        (tool_call("search_docs", query="best embedding model 2026", k=3),
         "[Doc 1] bge-small es excelente relación calidad/tamaño."),
    ], "Tienes bge-small (130 MB), ya está bien. Si quieres más precisión: bge-base (440 MB) o bge-m3 (multilingüe, 2.3 GB)."),
    ex_multi_tool("hay modelo de código", [
        (tool_call("list_models"), "qwen2.5:3b (1.8 GB)"),
        (tool_call("search_docs", query="code LLM small 3B 2026", k=3),
         "[Doc 1] Qwen 2.5 Coder 3B es excelente para código."),
    ], "Para código, **Qwen 2.5 Coder 3B** es lo mejor en 3B. Tienes qwen2.5:3b que también vale, pero Coder es mejor en programación."),
    ex_multi_tool("modelo bueno para español", [
        (tool_call("list_models"), "qwen2.5:3b (1.8 GB)"),
        (tool_call("search_docs", query="LLM Spanish support 2026", k=3),
         "[Doc 1] Qwen 2.5 soporta bien español, mejor que Llama 3.2 en español."),
    ], "Tienes qwen2.5:3b, que según la doc soporta bien español. Es una buena elección."),
    ex_multi_tool("recomiéndame para traducción", [
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("search_docs", query="LLM translation Spanish English 2026", k=3),
         "[Doc 1] Qwen 2.5 es bueno en traducción."),
    ], "Qwen 2.5 3B (que tienes) es decente en traducción. Para producción: NLLB o modelos específicos de traducción."),
]

# search + write_document: 5 más
EXAMPLES += [
    ex_multi_tool("documenta la arquitectura", [
        (tool_call("search_docs", query="RAG architecture Qdrant Ollama LlamaIndex", k=5),
         "[Doc 1] RAG típico: Ollama + Qdrant + LlamaIndex + FastAPI."),
        (tool_call("write_document", template="propuesta_tecnica", fields={
            "title": "Arquitectura del sistema",
            "scope": "Ollama (Qwen 2.5 3B) + Qdrant (vector DB) + BGE embeddings + FastAPI",
            "stack": "Docker, Python 3.14, RTX 3050 4GB",
        }),
         "PDF en /app/outputs/arquitectura.pdf"),
    ], "Documento de arquitectura: `outputs/arquitectura.pdf`."),
    ex_multi_tool("genera un PDF con cómo hacer fine-tuning", [
        (tool_call("search_docs", query="fine-tuning QLoRA tutorial", k=5),
         "[Doc 1] QLoRA con Unsloth, 4-bit, LoRA r=8, 1-3 epochs."),
        (tool_call("write_document", template="propuesta_tecnica", fields={
            "title": "Tutorial de fine-tuning",
            "scope": "QLoRA + Unsloth + Qwen 2.5 3B en RTX 3050 4GB",
        }),
         "PDF"),
    ], "PDF con tutorial de fine-tuning creado."),
    ex_multi_tool("investiga tool calling y hazme un doc", [
        (tool_call("search_docs", query="tool calling LLM best practices", k=5),
         "[Doc 1] Tool calling: JSON estructurado, system prompt claro, marcador de stop."),
        (tool_call("write_document", template="resumen_ejecutivo", fields={
            "title": "Tool calling",
            "summary": "Patrón donde el LLM genera JSON para invocar funciones externas.",
        }),
         "PDF"),
    ], "Doc sobre tool calling creado."),
    ex_multi_tool("resúmeme RAG en un PDF", [
        (tool_call("search_docs", query="RAG explanation", k=3),
         "[Doc 1] RAG = Retrieval-Augmented Generation. Combina retrieval + LLM."),
        (tool_call("write_document", template="resumen_ejecutivo", fields={"title": "RAG resumen"}),
         "PDF"),
    ], "PDF resumen sobre RAG."),
    ex_multi_tool("doc sobre embeddings", [
        (tool_call("search_docs", query="embeddings vector representations", k=3),
         "[Doc 1] Embeddings: vectores densos que representan significado semántico."),
        (tool_call("write_document", template="resumen_ejecutivo", fields={"title": "Embeddings"}),
         "PDF"),
    ], "Doc sobre embeddings creado."),
]

# get_gpu_stats + search_docs + list_models (3 tools): 10 más
EXAMPLES += [
    ex_multi_tool("diagnóstico + recomendaciones", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("search_docs", query="RAG optimization small model", k=3),
         "[Doc 1] Con hardware modesto, prioriza retrieval quality y corpus curado."),
    ], "Diagnóstico: GPU 45% VRAM, 2 modelos. Recomendación de la doc: prioriza retrieval quality. Tu sistema ya lo hace."),
    ex_multi_tool("cómo mejorar el sistema", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("search_docs", query="RAG improvements next steps", k=3),
         "[Doc 1] Mejoras: más corpus, re-ranking, fine-tuning, eval continua."),
    ], "Mejoras según la doc: ampliar corpus, re-ranking, fine-tuning, eval continua."),
    ex_multi_tool("auditoría rápida", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="RAG audit best practices", k=3),
         "[Doc 1] Auditoría RAG: corpus, retrieval, eval, monitoring."),
    ], "Auditoría rápida:\n- Hardware: 45% VRAM\n- Modelos: 2\n- Corpus: 62 chunks\n- Recomendación: ampliar corpus (ahora es pequeño)"),
    ex_multi_tool("tutorial rápido de embeddings", [
        (tool_call("list_models"), "bge-small-en-v1.5"),
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("search_docs", query="sentence-transformers tutorial", k=3),
         "[Doc 1] `from sentence_transformers import SentenceTransformer; model = SentenceTransformer('BAAI/bge-small-en-v1.5')`"),
    ], "Tutorial:\n```python\nfrom sentence_transformers import SentenceTransformer\nmodel = SentenceTransformer('BAAI/bge-small-en-v1.5')\nembeddings = model.encode(['texto1', 'texto2'])\n```\nCorre en CPU, 130 MB, perfecto para tu 4 GB GPU."),
    ex_multi_tool("estado + plan", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="next steps RAG project", k=3),
         "[Doc 1] Pasos típicos: ampliar corpus, eval, fine-tuning, monitoring."),
    ], "Estado: GPU 45%, 2 modelos, 62 chunks. Plan: ampliar corpus, eval, fine-tuning, monitoring."),
    ex_multi_tool("auditoría del sistema", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="RAG system health check", k=3),
         "[Doc 1] Health check: corpus size, retrieval scores, latency, GPU usage."),
    ], "Auditoría: GPU 45%, qwen2.5:3b, 62 chunks. Métricas a monitorizar: retrieval score, latencia, GPU usage."),
    ex_multi_tool("reporte con investigación", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("search_docs", query="production RAG architecture 2026", k=3),
         "[Doc 1] RAG prod: corpus versioning, eval continua, monitoring, fallback, retry."),
    ], "Reporte: GPU 45%, 2 modelos. Investigación sugiere RAG en producción necesita corpus versioning, eval continua, monitoring. Tu setup tiene las bases."),
    ex_multi_tool("análisis completo", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos, 384 dim"),
        (tool_call("search_docs", query="RAG best practices small corpus", k=3),
         "[Doc 1] Con corpus pequeño (<200 chunks), prioriza re-ranking y eval."),
    ], "Análisis: GPU 45%, 2 modelos, 62 chunks. Con corpus pequeño, la doc recomienda re-ranking. Tu setup base es bueno."),
    ex_multi_tool("prepárate para producción", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("search_docs", query="production ML checklist", k=3),
         "[Doc 1] Checklist prod: monitoring, logging, eval, error handling, rollback."),
    ], "Para ir a producción según la doc: monitoring, logging, eval continua, error handling, rollback. Tu sistema tiene la base, faltan los últimos."),
    ex_multi_tool("tutorial Ollama + GPU", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("search_docs", query="Ollama GPU setup tutorial", k=3),
         "[Doc 1] Instala Ollama, `ollama pull <modelo>`, `ollama serve`, automáticamente usa la GPU NVIDIA detectada."),
    ], "Tutorial Ollama con tu GPU:\n1. `ollama pull qwen2.5:3b` (ya lo tienes)\n2. `ollama serve` (o el servicio en Windows)\n3. La API queda en :11434\n4. Verifica GPU con `nvidia-smi` mientras corre"),
]

# --- Más 4+ tool chains (15 adicionales) ---
EXAMPLES += [
    ex_multi_tool("investigación + estado + PDF", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="AI engineering portfolio project", k=3),
         "[Doc 1] Portfolio AI: RAG + agent + tool calling + eval + monitoring."),
        (tool_call("write_document", template="resumen_ejecutivo", fields={
            "title": "Portfolio AI Engineering", "summary": "Sistema RAG con 6 tools, fine-tuning con QLoRA",
        }),
         "PDF"),
    ], "PDF de portfolio creado."),
    ex_multi_tool("análisis + plan + dashboard", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("plot_metric", metric="gpu_util", range="1h"),
         "Plot"),
        (tool_call("write_document", template="informe_estado", fields={"title": "Análisis + plan"}),
         "PDF"),
    ], "Dashboard completo: plot + PDF."),
    ex_multi_tool("report completo del estado", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("plot_metric", metric="vram_usage", range="1h"),
         "Plot"),
        (tool_call("write_document", template="informe_estado", fields={"title": "Reporte"}),
         "PDF"),
    ], "Reporte completo: estado + plot + PDF."),
    ex_multi_tool("explicación profunda del sistema", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="LLM serving architecture best practices", k=3),
         "[Doc 1] LLM serving: motor de inferencia (Ollama), API HTTP, GPU optimization."),
        (tool_call("search_docs", query="RAG architecture", k=3),
         "[Doc 1] RAG típico: retriever + LLM + prompt template + parser."),
    ], "Explicación: el sistema tiene Ollama (serving LLM en GPU), Qdrant (vector DB), BGE (embeddings), FastAPI (orquestación), y un agente con 6 tools. Es arquitectura RAG production-style."),
    ex_multi_tool("manual de onboarding", [
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="AI project setup Ollama Qdrant", k=3),
         "[Doc 1] Setup típico: docker compose con Ollama + Qdrant + servicio RAG."),
        (tool_call("write_document", template="propuesta_tecnica", fields={"title": "Onboarding"}),
         "PDF"),
    ], "Manual de onboarding creado en PDF."),
    ex_multi_tool("comparativa + decisión", [
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("search_docs", query="Qwen 2.5 vs Llama 3.2 small", k=3),
         "[Doc 1] Qwen mejor en código, Llama en conversación."),
        (tool_call("search_docs", query="Qwen 2.5 Spanish", k=3),
         "[Doc 1] Qwen 2.5 soporta bien español."),
    ], "Decisión: quédate con qwen2.5:3b. Mejor en código y español que Llama 3.2 3B."),
    ex_multi_tool("informe de capacidad", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="model capacity VRAM 4GB", k=3),
         "[Doc 1] Con 4GB: modelos hasta 3B con contexto moderado, embeddings pequeños."),
        (tool_call("write_document", template="informe_estado", fields={"title": "Capacidad del sistema"}),
         "PDF"),
    ], "Informe de capacidad en PDF."),
    ex_multi_tool("auditoría profunda", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="RAG audit checklist", k=3),
         "[Doc 1] Audit RAG: corpus quality, retrieval, eval, monitoring, security."),
        (tool_call("write_document", template="informe_estado", fields={"title": "Auditoría profunda"}),
         "PDF"),
    ], "Auditoría profunda + PDF."),
    ex_multi_tool("plan de mejora con investigación", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="RAG improvement roadmap", k=3),
         "[Doc 1] Mejoras: corpus (más docs), retrieval (re-ranking), LLM (fine-tuning), eval continua."),
        (tool_call("write_document", template="propuesta_tecnica", fields={"title": "Roadmap"}),
         "PDF"),
    ], "Plan de mejora + PDF."),
    ex_multi_tool("estado completo + plan acción", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("plot_metric", metric="requests_per_min", range="24h"),
         "Plot"),
        (tool_call("search_docs", query="production RAG optimization", k=3),
         "[Doc 1] Optimizar RAG: re-ranking, eval, monitoring, cache."),
        (tool_call("write_document", template="propuesta_tecnica", fields={"title": "Plan de acción"}),
         "PDF"),
    ], "Plan completo: estado + plot + búsqueda + PDF."),
    ex_multi_tool("research + plan + write", [
        (tool_call("search_docs", query="agentic RAG 2026", k=3),
         "[Doc 1] Agentic RAG: el agente decide cuándo buscar, qué tool usar, etc."),
        (tool_call("search_docs", query="fine-tuning small model best practices", k=3),
         "[Doc 1] Para fine-tuning de modelos pequeños: QLoRA, dataset 200-500 ejemplos, eval continuo."),
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b"),
    ], "Plan basado en la doc:\n1. Fine-tuning con QLoRA, ~200-500 ejemplos curados\n2. Eval continua con LLM-as-judge\n3. Monitoring de retrieval score y latencia\n4. Re-ranking si context_precision < 0.7\n\nQuieres que arranque con el dataset?"),
    ex_multi_tool("investigación + estado + write", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("search_docs", query="LLM observability 2026", k=3),
         "[Doc 1] Observabilidad: Prometheus + Grafana + Loki para métricas, logs, traces."),
        (tool_call("search_docs", query="RAG monitoring metrics", k=3),
         "[Doc 1] Métricas clave: retrieval score, latency, faithfulness, answer relevance."),
        (tool_call("write_document", template="propuesta_tecnica", fields={"title": "Plan de monitoring"}),
         "PDF"),
    ], "Plan de monitoring: Prometheus + Grafana + Loki. Métricas: retrieval, latencia, faithfulness. PDF creado."),
    ex_multi_tool("audit end-to-end + report", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="system audit RAG LLM serving", k=3),
         "[Doc 1] Audit: hardware, modelos, retrieval, eval, monitoring, security."),
        (tool_call("plot_metric", metric="gpu_util", range="1h"),
         "Plot"),
        (tool_call("write_document", template="informe_estado", fields={"title": "Audit end-to-end"}),
         "PDF"),
    ], "Audit end-to-end + plot + PDF."),
    ex_multi_tool("estado + plan multi-fase", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_collection_info", name="ai_engineering_docs"), "62 puntos"),
        (tool_call("search_docs", query="AI engineering project phases", k=3),
         "[Doc 1] Fases típicas: setup, RAG, eval, fine-tuning, monitoring, deploy."),
        (tool_call("write_document", template="propuesta_tecnica", fields={"title": "Plan multi-fase"}),
         "PDF"),
    ], "Plan multi-fase: setup (OK), RAG (OK), eval (OK), fine-tuning (pendiente), monitoring (pendiente), deploy (pendiente). PDF creado."),
    ex_multi_tool("research + decision matrix", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("search_docs", query="model selection criteria", k=3),
         "[Doc 1] Criterios: tamaño, idioma, capacidad, formato (instruct/chat), comunidad."),
        (tool_call("search_docs", query="Qwen 2.5 3B capabilities", k=3),
         "[Doc 1] Qwen 2.5 3B: chat, code, multilingual, function calling."),
        (tool_call("search_docs", query="alternative models 3B", k=3),
         "[Doc 1] Alternativas: Llama 3.2 3B, Phi-3.5 mini, Gemma 2 2B."),
    ], "Matriz de decisión para tu caso:\n- **qwen2.5:3b** (tienes): buen español, código, function calling\n- **Llama 3.2 3B**: mejor conversación en inglés\n- **Phi-3.5 mini**: bien en razonamiento\n\nRecomendación: quédate con qwen2.5:3b. Cubre tus casos."),
]

# --- Edge cases en inglés (prevenir language bias) ---
EXAMPLES += [
    ex_direct("What's 2+2?", "2+2 is 4."),
    ex_direct("How do I say hello in Spanish?", "You say 'hola' in Spanish."),
    ex_direct("What is Docker?", "Docker is a platform for building, shipping, and running applications in containers — lightweight, portable, isolated environments."),
    ex_single_tool("List my models", tool_call("list_models"), "qwen2.5:3b (1.8 GB)\nbge-small-en-v1.5 (130 MB)", "You have 2 models: qwen2.5:3b (LLM) and bge-small-en-v1.5 (embeddings)."),
    ex_single_tool("How's the GPU?", tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)\nTemp: 53°C", "GPU at 45% VRAM, 53°C. Normal."),
]

# --- Edge cases: preguntas parciales, ambiguas, multi-intent ---
EXAMPLES += [
    # Pregunta parcial (necesita clarificación)
    ex_direct("Tengo una duda", "Claro, dime. ¿En qué puedo ayudarte? [TAREA_COMPLETADA]"),
    ex_direct("Ayuda", "¿Qué necesitas? Dime el tema y te ayudo. [TAREA_COMPLETADA]"),
    ex_direct("?", "¿Sí? Dime qué necesitas. [TAREA_COMPLETADA]"),
    # Multi-intent (2 cosas en 1 mensaje)
    ex_multi_tool("Lista los modelos y mira la GPU", [
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB (45%)"),
    ], "Modelos: qwen2.5:3b + bge-small. GPU: 45% VRAM."),
    ex_multi_tool("Estado y gráfico", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("plot_metric", metric="gpu_util", range="1h"),
         "Plot en /app/outputs/gpu_util_1h.png"),
    ], "Estado: 45% VRAM. Gráfico en `outputs/gpu_util_1h.png`."),
    ex_multi_tool("Diagnóstico y PDF", [
        (tool_call("get_gpu_stats"), "VRAM: 1.8/4 GB"),
        (tool_call("list_models"), "qwen2.5:3b, bge-small"),
        (tool_call("write_document", template="informe_estado", fields={"title": "Diagnóstico"}),
         "PDF"),
    ], "PDF de diagnóstico creado."),
]


# ═══════════════════════════════════════════════════════════════════
# Recuento y guardado
# ═══════════════════════════════════════════════════════════════════
def categorize(ex):
    """Cuenta el número de tool calls en el ejemplo."""
    n_tools = sum(1 for m in ex["messages"] if m.get("content", "").startswith("<tool_call>"))
    if n_tools == 0:
        return "direct"
    elif n_tools == 1:
        return "1-tool"
    elif n_tools <= 3:
        return "2-3-tools"
    else:
        return "4+-tools"


def main():
    # Mezclar
    random.seed(42)
    random.shuffle(EXAMPLES)

    # Stats
    counts = {"direct": 0, "1-tool": 0, "2-3-tools": 0, "4+-tools": 0}
    for ex in EXAMPLES:
        counts[categorize(ex)] += 1

    print(f"Total ejemplos: {len(EXAMPLES)}")
    print(f"  Direct:    {counts['direct']} ({counts['direct']/len(EXAMPLES)*100:.0f}%)")
    print(f"  1-tool:    {counts['1-tool']} ({counts['1-tool']/len(EXAMPLES)*100:.0f}%)")
    print(f"  2-3 tools: {counts['2-3-tools']} ({counts['2-3-tools']/len(EXAMPLES)*100:.0f}%)")
    print(f"  4+ tools:  {counts['4+-tools']} ({counts['4+-tools']/len(EXAMPLES)*100:.0f}%)")

    # Guardar
    with open(OUT, "w", encoding="utf-8") as f:
        for ex in EXAMPLES:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"\nGuardado en {OUT}")

    # Muestra
    print(f"\n=== 10 ejemplos aleatorios ===\n")
    for i, ex in enumerate(random.sample(EXAMPLES, min(10, len(EXAMPLES))), 1):
        print(f"--- Ejemplo {i} ({categorize(ex)}) ---")
        for m in ex["messages"]:
            role = m["role"]
            content = m["content"]
            if role == "system":
                continue  # skip el system prompt en samples
            print(f"[{role}]")
            print(content[:300] + ("..." if len(content) > 300 else ""))
            print()
        print()


if __name__ == "__main__":
    main()
