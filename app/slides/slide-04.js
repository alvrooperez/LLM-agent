function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  slide.addText("System Architecture", {
    x: 0.5, y: 0.25, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: theme.primary, fontFace: "Segoe UI"
  });

  // LEFT: Hardware card
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.2, h: 4.2,
    fill: { color: theme.light }, rectRadius: 0.1
  });
  slide.addText("Hardware", {
    x: 0.7, y: 1.15, w: 3.8, h: 0.4,
    fontSize: 13, bold: true, color: theme.accent, fontFace: "Segoe UI"
  });
  const hwRows = [
    ["Laptop", "MSI Katana GF66 11UC"],
    ["GPU", "NVIDIA RTX 3050 - 4GB VRAM"],
    ["RAM", "16GB DDR4"],
    ["OS", "Windows 11"],
    ["GPU CUDA", "12.8 / Driver 572.61"],
  ];
  hwRows.forEach(([k, v], i) => {
    slide.addText(k, { x: 0.7, y: 1.6 + i * 0.52, w: 1.2, h: 0.4, fontSize: 11, bold: true, color: theme.secondary, fontFace: "Segoe UI" });
    slide.addText(v, { x: 1.9, y: 1.6 + i * 0.52, w: 2.6, h: 0.4, fontSize: 11, color: theme.primary, fontFace: "Segoe UI" });
  });

  // RIGHT: Components grid
  const comps = [
    { name: "Ollama", port: ":11434", note: "qwen2.5:3b + qwen2.5-rag-ft", color: theme.accent },
    { name: "Qdrant", port: ":6333", note: "62 chunks, dim 384, cosine", color: theme.accent },
    { name: "RAG API", port: ":8000", note: "sentence-transformers + FastAPI", color: theme.accent },
    { name: "Chat App", port: ":8090", note: "FastAPI SPA, dark mode, markdown", color: theme.accent },
  ];
  comps.forEach((c, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 5.0 + col * 2.35;
    const y = 1.0 + row * 2.1;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 2.2, h: 1.85,
      fill: { color: theme.light }, rectRadius: 0.08
    });
    slide.addText(c.name, { x: x + 0.15, y: y + 0.12, w: 1.9, h: 0.35, fontSize: 14, bold: true, color: theme.primary, fontFace: "Segoe UI" });
    slide.addShape(pres.shapes.RECTANGLE, { x: x + 0.15, y: y + 0.5, w: 1.9, h: 0.03, fill: { color: c.color } });
    slide.addText(c.port, { x: x + 0.15, y: y + 0.65, w: 1.9, h: 0.35, fontSize: 18, bold: true, color: c.color, fontFace: "Segoe UI" });
    slide.addText(c.note, { x: x + 0.15, y: y + 1.1, w: 1.9, h: 0.6, fontSize: 10, color: theme.secondary, fontFace: "Segoe UI" });
  });

  // Bottom bar
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 5.1, w: 9, h: 0.02, fill: { color: theme.light } });
  slide.addText("All services containerized with Docker  |  No cloud APIs  |  Full local inference", {
    x: 0.5, y: 5.15, w: 9, h: 0.3, fontSize: 10, color: theme.secondary, fontFace: "Segoe UI"
  });
  slide.addText("04", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Segoe UI" });
}
module.exports = { createSlide };
