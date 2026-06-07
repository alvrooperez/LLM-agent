# Arquitectura del proyecto AI Engineer Portfolio

Guía de referencia de cómo está montado todo y por qué. Pensado para releer cuando vuelvas, para usar en entrevistas, o para defender decisiones técnicas.

---

## 1. Visión general en 30 segundos

Tienes un sistema completo de **AI engineering corriendo en tu portátil**, con tres piezas principales que se hablan entre sí:

- **Ollama** sirve un modelo de IA (Qwen 2.5 3B) en tu GPU
- **Open WebUI** te da una interfaz web tipo ChatGPT para hablar con ese modelo
- **Qdrant** es una base de datos de "búsqueda por significado" donde, en la siguiente fase, vamos a meter conocimiento técnico para que el modelo sepa cosas concretas

Todo está containerizado salvo Ollama, que va en host porque así usa la GPU directamente sin configuraciones raras.

---

## 2. Mapa de servicios

| Servicio | Qué hace | Dónde corre | Puerto | Por qué así |
|---|---|---|---|---|
| **Ollama** | Motor de inferencia LLM | Host Windows (nativo) | 11434 | Necesita acceso directo a la GPU; instalarlo en Docker añade fricción sin beneficio |
| **Qwen 2.5 3B** | El modelo de lenguaje | Descargado por Ollama, vive en GPU | — | Modelo pequeño (3B parámetros) que cabe en 4GB de VRAM con cuantización Q4 |
| **Open WebUI** | Interfaz chat tipo ChatGPT | Docker | 3000 | Es la mejor UI open source para Ollama; corre containerizada para aislar dependencias |
| **Qdrant** | Base de datos vectorial | Docker | 6333 (REST), 6334 (gRPC) | Necesaria para RAG; corre en Docker porque es solo un servicio stateless de datos |
| **BGE-small** | Modelo de embeddings (CPU) | Proceso Python (próximamente) | — | Convierte texto en vectores para Qdrant; corre en CPU porque es pequeño y rápido |
| **FastAPI + LlamaIndex** | Servicio RAG | Docker o proceso local (próximamente) | 8000 | El "cerebro" que une Ollama + Qdrant + embeddings; pendiente en Fase 2 |

---

## 3. Flujo end-to-end (lo que pasa cuando chateas)

### Escenario: le preguntas a Open WebUI "¿Qué es QLoRA?"

```
1. Tu navegador (http://localhost:3000)
   │  "Envía pregunta a Open WebUI"
   ▼
2. Open WebUI (contenedor Docker)
   │  Recibe la pregunta por HTTP interno
   │  La reenvía a Ollama (con prompt formateado)
   ▼
3. Ollama (host Windows)
   │  Carga qwen2.5:3b en la VRAM (~2.5GB de los 4GB)
   │  Tokeniza tu texto (lo convierte en números)
   │  Pasa los tokens por la red neuronal (17 capas de transformer)
   │  Genera tokens uno a uno, ~68 tokens/segundo
   ▼
4. Ollama devuelve los tokens a Open WebUI
   │  Open WebUI los muestra letra a letra (streaming)
   ▼
5. Tu navegador renderiza la respuesta
```

**Tiempo total típico**: 200-500ms para empezar, 1-3 segundos para respuestas cortas.

### Lo que el modelo hace internamente (sin联网)

Cuando Ollama recibe tu pregunta:

1. **Tokenización**: tu texto se parte en "tokens" (pedazos de palabra). "QLoRA" → `["Q", "Lo", "RA"]` o similar. Cada token es un número entero.
2. **Embeddings internos**: cada token se convierte en un vector de 4096 dimensiones (el "lenguaje interno" del modelo).
3. **Forward pass**: los vectores pasan por **17 capas de transformer** (atención multi-cabeza + feed-forward). Cada capa refina la representación.
4. **Decodificación**: el último vector se proyecta sobre el vocabulario (~150k tokens) y sale una distribución de probabilidad. Se escoge el token más probable (o se samplea).
5. **Repetir** desde el paso 4 con el nuevo token, hasta que el modelo emita un token de fin o alcance el límite.

**No hay internet. No hay "búsqueda".** El modelo solo hace matemáticas con números, muy rápido, miles de millones de operaciones.

---

## 4. Conceptos clave de AI (lo que necesitas entender)

### 4.1 ¿Qué es un LLM?

Un **Large Language Model** es una red neuronal enorme (en nuestro caso, 3 mil millones de parámetros) entrenada con cantidades masivas de texto. "Parámetros" son los números que la red ajusta durante el entrenamiento; son los "knowledge" del modelo.

El nuestro es **Qwen 2.5 3B**:
- 3 mil millones de parámetros
- 17 capas de transformer
- Vocabulario de ~150k tokens
- Entrenado por Alibaba en textos multilingües
- Versión "Instruct": fine-tuneado para seguir instrucciones

### 4.2 ¿Qué es cuantización?

Los parámetros originalmente están en **float32** (32 bits por número = 4 bytes). Eso es mucho. La **cuantización** los comprime a menos bits:

- Q8_0: 8 bits por parámetro → 1.5GB para 3B (calidad casi idéntica al original)
- **Q4_K_M** (lo que usamos): ~4.5 bits por parámetro → ~1.8GB para 3B (ligera pérdida de calidad, gran ahorro)
- Q2_K: 2 bits → ~1GB (calidad notablemente peor)

Trade-off: a menos bits, menos memoria y más rápido, pero más tonto. **Q4_K_M es el sweet spot** para 4GB de VRAM.

### 4.3 ¿Qué es el context window?

Es la cantidad de texto que el modelo puede "ver" de una vez. Para Qwen 2.5 es **32k tokens** (unas 24.000 palabras en español). Si tu conversación + el system prompt + los documentos que le pasas suman más, se recorta lo más viejo.

Por eso en RAG es importante **no pasar todo el documento**, sino solo los chunks relevantes.

### 4.4 ¿Qué son los embeddings?

Un embedding es una **lista de números** que representa el significado de un texto. Lo genera un modelo (nosotros usamos BGE-small, 384 dimensiones).

Ejemplo simplificado (3 dimensiones en vez de 384 para visualizar):

```
"Ollama sirve LLMs"      → [0.8, 0.2, 0.1]
"vLLM sirve LLMs"        → [0.7, 0.3, 0.1]   (parecido, hablan de lo mismo)
"Receta de paella"       → [0.1, 0.9, 0.8]   (muy diferente)
```

Los embeddings **similares** están **cerca** en este espacio de números. Esto permite búsqueda por significado: tu pregunta también se convierte en vector, y buscamos los documentos cuyos vectores estén más cerca.

### 4.5 ¿Qué es cosine similarity?

Es la fórmula que usamos para medir "cercanía" entre dos vectores. Va de -1 a 1:
- 1.0 = idénticos en significado
- 0.0 = no relacionados
- -1.0 = opuestos (raro en embeddings reales)

Qdrant internamente usa cosine similarity (o distancia, que es 1 - cosine) para ranking.

### 4.6 ¿Qué es RAG (Retrieval-Augmented Generation)?

Es **darle al LLM documentos relevantes como contexto** antes de que genere la respuesta. En vez de confiar solo en lo que el modelo "sabe" de su entrenamiento, le pasamos la información exacta que necesita.

**Sin RAG**: "¿Cómo configuro Qdrant para producción?" → el modelo puede inventar (alucinar) o no saber.

**Con RAG**:
1. Buscamos en nuestra base de conocimiento chunks relevantes a esa pregunta
2. Le pasamos al modelo: "Basándote en ESTOS documentos: [...], responde: ¿Cómo configuro Qdrant para producción?"
3. El modelo responde con información real y podemos citar las fuentes

**RAG no entrena al modelo**. Solo le pasa información extra en cada pregunta. Es la forma más barata y efectiva de especializar un LLM.

---

## 5. Cómo se comunican los servicios (networking)

### Desde tu navegador
- `http://localhost:3000` → Docker Desktop lo mapea al puerto 8080 del contenedor Open WebUI
- Open WebUI escucha en 0.0.0.0:8080 dentro del contenedor; Docker Desktop hace NAT al 3000 del host

### Desde Open WebUI a Ollama
- Open WebUI (en Docker) necesita hablar con Ollama (en el host Windows)
- Usa `host.docker.internal:11434` — Docker Desktop inyecta esta IP que apunta al host
- Configurado en `phase-1-llm-serving/docker-compose.yml` con `extra_hosts: host.docker.internal:host-gateway`

### Entre contenedores
- Open WebUI y (futuro) FastAPI comparten la red por defecto de docker-compose
- Se hablan por nombre de servicio: `http://qdrant:6333`, `http://open-webui:8080`

### Modelo de seguridad actual
- Todo en localhost, sin exposición a la red
- No hay TLS (estamos en dev)
- Open WebUI tiene autenticación local (usuario/password que creaste al entrar)
- Ollama NO tiene auth (porque solo escucha en localhost, no accesible desde fuera)

---

## 6. El constraint de 4GB — qué significa, qué hacemos con él

Tu **RTX 3050 4GB** es limitada. Decisiones que tomamos:

| Decisión | Por qué |
|---|---|
| Modelos 1B-3B nada más | 7B cuantizado a Q4 no cabe en 4GB con contexto decente |
| Cuantización Q4_K_M | Mejor ratio calidad/memoria |
| Embeddings en CPU | BGE-small son 130MB, no vale la pena gastar VRAM |
| Un solo modelo cargado a la vez | No podemos tener 2 LLMs en GPU simultáneos |
| Ollama en host (no Docker) | Evita overhead de GPU passthrough, más simple |

**Esto es una feature, no un bug.** En entrevista, demuestra que entiendes los tradeoffs reales de hardware y que optimizas para constraints.

---

## 7. Lo que viene (Fase 2)

Cuando esté el script de ingestión + FastAPI:

```
Usuario hace pregunta
    ↓
FastAPI recibe por HTTP
    ↓
LlamaIndex orquesta:
    ├── 1. Embedding de la pregunta (BGE-small, CPU)
    ├── 2. Búsqueda en Qdrant: top-5 chunks más similares
    ├── 3. Construcción del prompt: contexto + pregunta
    └── 4. Llamada a Ollama con streaming
    ↓
Respuesta al usuario con fuentes citadas
```

Tiempo objetivo: 1-3 segundos end-to-end en una pregunta típica.

---

## 8. Glosario rápido

- **LLM**: Large Language Model. Red neuronal entrenada con texto.
- **Token**: Pedazo de palabra. El LLM no trabaja con letras sino con tokens.
- **Embedding**: Vector de números que representa significado de un texto.
- **Vector DB**: Base de datos optimizada para buscar vectores similares (Qdrant, Pinecone, Weaviate).
- **Quantization**: Comprimir los pesos del modelo a menos bits para ahorrar memoria.
- **RAG**: Retrieval-Augmented Generation. Darle al LLM contexto externo antes de generar.
- **Inference**: Cuando el modelo ya entrenado genera respuestas (lo que hace Ollama).
- **Fine-tuning**: Re-entrenar un modelo existente con datos nuevos para especializarlo.
- **VRAM**: Memoria de la GPU. Los modelos cargados tienen que caber ahí.
- **Context window**: Cantidad máxima de tokens que el modelo "ve" de una vez.
- **Cosine similarity**: Medida de "parecido" entre dos vectores, de -1 a 1.
- **Top-k**: Los k resultados más relevantes de una búsqueda.
- **Hallucination**: Cuando el LLM inventa información con confianza.
- **Prompt**: El texto que le pasas al LLM. System prompt + user prompt + assistant prompt.

---

## 9. Para explicar en entrevista

**"¿Qué es lo que has montado?"**
"Un sistema end-to-end de LLM engineering: sirvo un modelo open source en local con Ollama, lo expongo vía API compatible con OpenAI, le pongo una UI con Open WebUI detrás de un reverse proxy planeado, una base de datos vectorial con Qdrant, y un pipeline RAG que responde preguntas técnicas sobre el propio stack usando LlamaIndex y embeddings. Todo en Docker salvo el motor de inferencia, optimizado para correr en una GPU de 4GB mediante cuantización Q4."

**"¿Por qué Ollama y no vLLM?"**
"vLLM asume GPUs de 24GB o más y su PagedAttention está optimizado para eso. Ollama está pensado para correr bien en hardware modesto y maneja la cuantización de forma transparente. Para 4GB, Ollama es la opción correcta."

**"¿Por qué Qdrant y no Pinecone/Weaviate?"**
"Pinecone es SaaS only, no encaja con self-hosted. Weaviate es más pesado de operar. Qdrant tiene la mejor combinación de: open source, single-binary deploy, API limpia, y rendimiento en hardware modesto. Encaja con el principio de 'simple y operativo' del proyecto."

**"¿Qué demuestra el RAG?"**
"Que no solo consumo APIs de OpenAI: sé construir un sistema donde el LLM se convierte en una herramienta precisa sobre datos propios, citando fuentes, y funcionando en local. Es el patrón que el 80% de productos de AI en empresa necesita."
