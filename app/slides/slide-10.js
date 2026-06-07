function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  slide.addText("6 Tools with Real Backends", {
    x: 0.5, y: 0.25, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: theme.primary, fontFace: "Arial"
  });

  const tools = [
    { name: "search_docs", backend: "RAG API :8000", desc: "Vector search in knowledge base" },
    { name: "list_models", backend: "Ollama :11434", desc: "List available LLM models" },
    { name: "get_gpu_stats", backend: "nvidia-smi", desc: "VRAM, utilization, temperature" },
    { name: "get_collection_info", backend: "Qdrant :6333", desc: "Collection metadata & stats" },
    { name: "plot_metric", backend: "matplotlib", desc: "Generate PNG charts from CSV" },
    { name: "write_document", backend: "ReportLab", desc: "Generate PDF reports" },
  ];

  tools.forEach((t, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.5 + col * 3.1;
    const y = 0.95 + row * 1.55;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 2.9, h: 1.35,
      fill: { color: theme.light }, rectRadius: 0.08
    });
    // Tool name
    slide.addText(t.name, {
      x: x + 0.15, y: y + 0.12, w: 2.6, h: 0.35,
      fontSize: 12, bold: true, color: theme.accent, fontFace: "Arial"
    });
    // Backend badge
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.15, y: y + 0.48, w: 1.6, h: 0.3,
      fill: { color: theme.bg }, rectRadius: 0.04
    });
    slide.addText(t.backend, {
      x: x + 0.15, y: y + 0.48, w: 1.6, h: 0.3,
      fontSize: 9, bold: true, color: theme.primary, align: "center", valign: "middle", fontFace: "Arial"
    });
    slide.addText(t.desc, {
      x: x + 0.15, y: y + 0.85, w: 2.6, h: 0.4,
      fontSize: 10, color: theme.secondary, fontFace: "Arial"
    });
  });

  // Agent loop diagram
  slide.addText("Agent Loop", {
    x: 0.5, y: 4.15, w: 9, h: 0.3,
    fontSize: 13, bold: true, color: theme.accent, fontFace: "Arial"
  });
  const loop = ["Ollama", "Parse tools", "Execute", "Feedback", "Repeat"];
  loop.forEach((s, i) => {
    const x = 0.5 + i * 1.85;
    slide.addShape(pres.shapes.RECTANGLE, { x: x, y: 4.5, w: 1.6, h: 0.45, fill: { color: theme.light }, rectRadius: 0.06 });
    slide.addText(s, { x: x, y: 4.5, w: 1.6, h: 0.45, fontSize: 10, bold: true, color: theme.primary, align: "center", valign: "middle", fontFace: "Arial" });
    if (i < loop.length - 1) {
      slide.addText("->", { x: x + 1.6, y: 4.5, w: 0.25, h: 0.45, fontSize: 12, color: theme.accent, align: "center", valign: "middle", fontFace: "Arial" });
    }
  });
  slide.addText("10", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Arial" });
}
module.exports = { createSlide };
