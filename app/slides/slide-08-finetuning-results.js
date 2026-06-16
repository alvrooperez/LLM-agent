// Slide 8 — Fine-tuning results (honest)
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow
  slide.addText("FINE-TUNING RESULTS", {
    x: 0.7, y: 0.5, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.85, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("What 230 examples actually did.", {
    x: 0.7, y: 1.0, w: 8.6, h: 0.7,
    fontSize: 24, bold: true, color: theme.text, fontFace: "Georgia"
  });

  // A/B comparison table
  const tableData = [
    [
      { text: "Metric", options: { bold: true, color: theme.textSoft, fontSize: 10 } },
      { text: "Base qwen2.5:3b", options: { bold: true, color: theme.textSoft, fontSize: 10 } },
      { text: "Fine-tuned", options: { bold: true, color: theme.textSoft, fontSize: 10 } },
      { text: "Delta", options: { bold: true, color: theme.textSoft, fontSize: 10 } },
    ],
    [
      { text: "Tool call rate", options: { color: theme.text, fontSize: 11 } },
      { text: "7%", options: { color: theme.text, fontSize: 11 } },
      { text: "7%", options: { color: theme.text, fontSize: 11 } },
      { text: "no change", options: { color: theme.textSoft, fontSize: 11 } },
    ],
    [
      { text: "Iterations / task", options: { color: theme.text, fontSize: 11 } },
      { text: "2.2", options: { color: theme.text, fontSize: 11 } },
      { text: "2.0", options: { color: theme.text, fontSize: 11 } },
      { text: "−9%", options: { color: theme.success, fontSize: 11, bold: true } },
    ],
    [
      { text: "Response length", options: { color: theme.text, fontSize: 11 } },
      { text: "315 chars", options: { color: theme.text, fontSize: 11 } },
      { text: "279 chars", options: { color: theme.text, fontSize: 11 } },
      { text: "−11%", options: { color: theme.success, fontSize: 11, bold: true } },
    ],
    [
      { text: "RAG relevance", options: { color: theme.text, fontSize: 11 } },
      { text: "baseline", options: { color: theme.text, fontSize: 11 } },
      { text: "baseline", options: { color: theme.text, fontSize: 11 } },
      { text: "no change", options: { color: theme.textSoft, fontSize: 11 } },
    ],
  ];
  slide.addTable(tableData, {
    x: 0.7, y: 2.0, w: 5.5, h: 2.5,
    colW: [1.7, 1.4, 1.3, 1.1],
    rowH: 0.5,
    border: { type: 'solid', pt: 0.5, color: theme.border },
    fill: { color: theme.bg },
    fontFace: "Segoe UI",
    valign: "middle",
  });

  // Honest finding callout
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.4, y: 2.0, w: 2.9, h: 2.5,
    fill: { color: theme.surface }, line: { color: theme.border, width: 0.75 }
  });
  slide.addText("HONEST FINDING", {
    x: 6.6, y: 2.15, w: 2.6, h: 0.25,
    fontSize: 9, bold: true, color: theme.accent, charSpacing: 3, fontFace: "Segoe UI"
  });
  slide.addText("The base model already knew tool-calling format.", {
    x: 6.6, y: 2.45, w: 2.6, h: 0.7,
    fontSize: 13, bold: true, color: theme.text, fontFace: "Georgia"
  });
  slide.addText("LoRA didn't add new capability — it shortened responses and reduced iteration count. Zero regression.", {
    x: 6.6, y: 3.2, w: 2.6, h: 1.2,
    fontSize: 10, color: theme.textSoft, fontFace: "Segoe UI"
  });

  // Bottom takeaway
  slide.addText("This is the right outcome to report. Inflating 'capability gains' would be lying about the data.", {
    x: 0.7, y: 4.85, w: 8.6, h: 0.3,
    fontSize: 10, color: theme.text, fontFace: "Segoe UI", italic: true
  });

  // Page number
  slide.addText("08", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
