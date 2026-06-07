function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  // Title
  slide.addText("Contents", {
    x: 0.5, y: 0.35, w: 9, h: 0.7,
    fontSize: 36, bold: true, color: theme.primary, fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.0, w: 1.5, h: 0.04, fill: { color: theme.accent } });

  const sections = [
    { num: "01", title: "Hardware & Architecture", desc: "RTX 3050, Ollama, Qdrant, Docker" },
    { num: "02", title: "RAG Pipeline", desc: "Vector DB, sentence-transformers, +83% improvement" },
    { num: "03", title: "Fine-tuning", desc: "Unsloth LoRA, 230 train / 15 test, GGUF Q4_K_M" },
    { num: "04", title: "Tool Calling Agent", desc: "6 tools, agent loop, 4/4 E2E tasks" },
    { num: "05", title: "Performance & Capacity", desc: "Load test, multi-tool chaining, max concurrency" },
  ];

  sections.forEach((s, i) => {
    const y = 1.3 + i * 0.78;
    // Number
    slide.addText(s.num, {
      x: 0.5, y: y, w: 0.7, h: 0.6,
      fontSize: 28, bold: true, color: theme.accent, fontFace: "Segoe UI"
    });
    // Line
    slide.addShape(pres.shapes.RECTANGLE, { x: 1.3, y: y + 0.28, w: 0.4, h: 0.03, fill: { color: theme.light } });
    // Title
    slide.addText(s.title, {
      x: 1.85, y: y, w: 7, h: 0.38,
      fontSize: 18, bold: true, color: theme.primary, fontFace: "Segoe UI"
    });
    // Desc
    slide.addText(s.desc, {
      x: 1.85, y: y + 0.36, w: 7, h: 0.3,
      fontSize: 12, color: theme.secondary, fontFace: "Segoe UI"
    });
  });

  // Page number
  slide.addText("02", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Segoe UI" });
}
module.exports = { createSlide };
