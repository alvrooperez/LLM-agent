function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: theme.accent } });
  slide.addText("Key Takeaways", {
    x: 0.5, y: 0.3, w: 9, h: 0.7,
    fontSize: 36, bold: true, color: theme.primary, fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.95, w: 1.8, h: 0.05, fill: { color: theme.accent } });

  const takeaways = [
    {
      icon: "01",
      title: "Full local AI stack",
      body: "Ollama, Qdrant, RAG API, FastAPI agent - all on RTX 3050 4GB. No cloud APIs, no subscriptions."
    },
    {
      icon: "02",
      title: "Rigorous evaluation",
      body: "Held-out test sets, A/B comparisons, load tests. Engineering decisions backed by data, not intuition."
    },
    {
      icon: "03",
      title: "Honest reporting",
      body: "Fine-tuning on 230 examples did not add capability - base model already knew tool calling. Documented and validated."
    },
    {
      icon: "04",
      title: "Real agent capability",
      body: "Multi-tool chaining in a single iteration: 3 tools in parallel, no user re-prompts. 5/5 PASS on chaining eval."
    },
    {
      icon: "05",
      title: "Capacity known",
      body: "Up to 4 concurrent users at acceptable latency. RTX 3050 is the bottleneck - not the software stack."
    },
  ];

  takeaways.forEach((t, i) => {
    const y = 1.15 + i * 0.82;
    // Number circle
    slide.addShape(pres.shapes.OVAL, {
      x: 0.5, y: y + 0.08, w: 0.5, h: 0.5,
      fill: { color: theme.accent }
    });
    slide.addText(t.icon, {
      x: 0.5, y: y + 0.08, w: 0.5, h: 0.5,
      fontSize: 12, bold: true, color: theme.bg, align: "center", valign: "middle", fontFace: "Segoe UI"
    });
    slide.addText(t.title, {
      x: 1.15, y: y + 0.05, w: 8.3, h: 0.32,
      fontSize: 14, bold: true, color: theme.primary, fontFace: "Segoe UI"
    });
    slide.addText(t.body, {
      x: 1.15, y: y + 0.38, w: 8.3, h: 0.38,
      fontSize: 11, color: theme.secondary, fontFace: "Segoe UI"
    });
  });

  // Bottom links
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.2, w: 10, h: 0.425, fill: { color: theme.light } });
  slide.addText("Demo: http://localhost:8090  |  Architecture: http://localhost:8090/architecture  |  Source: phase-2-rag/", {
    x: 0.5, y: 5.2, w: 9, h: 0.425,
    fontSize: 10, color: theme.secondary, valign: "middle", fontFace: "Segoe UI"
  });
}
module.exports = { createSlide };
