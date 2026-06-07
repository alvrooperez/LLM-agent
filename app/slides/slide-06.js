function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  slide.addText("RAG Pipeline - Results", {
    x: 0.5, y: 0.25, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: theme.primary, fontFace: "Arial"
  });

  // Big stat callouts
  const stats = [
    { val: "62", label: "Chunks indexed", sub: "AI engineering docs" },
    { val: "384", label: "Vector dim", sub: "all-MiniLM-L6-v2" },
    { val: "+83%", label: "Answer relevance", sub: "vs no-RAG baseline" },
    { val: "68", label: "tok/s throughput", sub: "on RTX 3050" },
  ];
  stats.forEach((s, i) => {
    const x = 0.5 + i * 2.35;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.0, w: 2.15, h: 1.7,
      fill: { color: theme.light }, rectRadius: 0.08
    });
    slide.addText(s.val, {
      x: x, y: 1.05, w: 2.15, h: 0.85,
      fontSize: 40, bold: true, color: theme.accent, align: "center", fontFace: "Arial"
    });
    slide.addText(s.label, {
      x: x + 0.1, y: 1.9, w: 1.95, h: 0.35,
      fontSize: 12, bold: true, color: theme.primary, align: "center", fontFace: "Arial"
    });
    slide.addText(s.sub, {
      x: x + 0.1, y: 2.22, w: 1.95, h: 0.35,
      fontSize: 10, color: theme.secondary, align: "center", fontFace: "Arial"
    });
  });

  // Pipeline flow
  slide.addText("Pipeline", {
    x: 0.5, y: 2.9, w: 9, h: 0.35,
    fontSize: 13, bold: true, color: theme.accent, fontFace: "Arial"
  });
  const steps = ["Docs", "Scrape", "Embed", "Qdrant", "Retrieve", "Generate"];
  steps.forEach((s, i) => {
    const x = 0.5 + i * 1.55;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 3.3, w: 1.35, h: 0.55,
      fill: { color: theme.light }, rectRadius: 0.06
    });
    slide.addText(s, {
      x: x, y: 3.3, w: 1.35, h: 0.55,
      fontSize: 11, bold: true, color: theme.primary, align: "center", valign: "middle", fontFace: "Arial"
    });
    if (i < steps.length - 1) {
      slide.addText("->", {
        x: x + 1.35, y: 3.3, w: 0.2, h: 0.55,
        fontSize: 14, color: theme.accent, align: "center", valign: "middle", fontFace: "Arial"
      });
    }
  });

  // Bottom info
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.1, w: 9, h: 1.2, fill: { color: theme.light }, rectRadius: 0.08 });
  slide.addText("Golden Q&A Dataset + LLM-as-Judge", {
    x: 0.7, y: 4.2, w: 8.6, h: 0.35,
    fontSize: 13, bold: true, color: theme.primary, fontFace: "Arial"
  });
  slide.addText("Curated question-answer pairs from real technical documentation. LLM judges answer quality on a 1-5 scale. RAG pipeline evaluated against baseline (no retrieval) using the same judge model.", {
    x: 0.7, y: 4.55, w: 8.6, h: 0.65,
    fontSize: 11, color: theme.secondary, fontFace: "Arial"
  });
  slide.addText("06", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Arial" });
}
module.exports = { createSlide };
