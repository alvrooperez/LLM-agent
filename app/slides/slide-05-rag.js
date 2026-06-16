// Slide 5 — RAG pipeline explanation
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow
  slide.addText("RAG PIPELINE", {
    x: 0.7, y: 0.5, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.85, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("Retrieval-Augmented Generation over 62 doc chunks.", {
    x: 0.7, y: 1.0, w: 8.6, h: 0.7,
    fontSize: 24, bold: true, color: theme.text, fontFace: "Georgia"
  });

  // Pipeline steps (horizontal)
  const steps = [
    { num: "1", title: "Embed", body: "sentence-transformers/all-MiniLM-L6-v2 · 384 dim" },
    { num: "2", title: "Store", body: "Qdrant cosine similarity · 62 chunks ingested" },
    { num: "3", title: "Query", body: "Top-3 docs by cosine similarity" },
    { num: "4", title: "Augment", body: "Inject context into the prompt" },
    { num: "5", title: "Generate", body: "Ollama answers using retrieved context" },
  ];

  const boxW = 1.65;
  const boxH = 1.4;
  const startX = 0.7;
  const gap = 0.2;

  steps.forEach((s, i) => {
    const x = startX + i * (boxW + gap);
    const y = 2.4;
    // Card
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: boxW, h: boxH,
      fill: { color: theme.surface }, line: { color: theme.border, width: 0.75 }
    });
    // Number (top, accent)
    slide.addText(s.num, {
      x: x, y: y + 0.15, w: boxW, h: 0.4,
      fontSize: 22, color: theme.accent, fontFace: "Georgia", italic: true, align: "center"
    });
    // Title
    slide.addText(s.title, {
      x: x, y: y + 0.6, w: boxW, h: 0.3,
      fontSize: 12, bold: true, color: theme.text, fontFace: "Segoe UI", align: "center"
    });
    // Body
    slide.addText(s.body, {
      x: x + 0.1, y: y + 0.9, w: boxW - 0.2, h: 0.45,
      fontSize: 8, color: theme.textSoft, fontFace: "Segoe UI", align: "center"
    });
    // Arrow
    if (i < steps.length - 1) {
      slide.addShape(pres.shapes.LINE, {
        x: x + boxW + 0.02, y: y + boxH/2, w: gap - 0.04, h: 0,
        line: { color: theme.divider, width: 1, endArrowType: "triangle" }
      });
    }
  });

  // Bottom: key insight
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 4.2, w: 8.6, h: 0.85,
    fill: { color: theme.accentSoft }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("Why it matters", {
    x: 0.9, y: 4.3, w: 8.2, h: 0.25,
    fontSize: 10, bold: true, color: theme.accent, fontFace: "Segoe UI"
  });
  slide.addText("A 3B model hallucinates specifics. Grounding its answers in retrieved docs (Ollama, Qdrant, Unsloth, LlamaIndex) cuts hallucinations and lets me ask 'how do I configure X?' without it guessing.", {
    x: 0.9, y: 4.55, w: 8.2, h: 0.45,
    fontSize: 11, color: theme.text, fontFace: "Segoe UI"
  });

  // Page number
  slide.addText("05", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
