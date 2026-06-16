// Slide 1 — Cover
// Light, editorial: white background, navy serif title, thin accent rule
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  // White background
  slide.background = { color: theme.bg };

  // Subtle top-left accent block (small, not full-width)
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 5.625,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });

  // Small all-caps eyebrow
  slide.addText("AI ENGINEERING PORTFOLIO  ·  2025", {
    x: 0.7, y: 0.7, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });

  // Thin divider line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.05, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });

  // Big serif title
  slide.addText("A self-hosted LLM agent,", {
    x: 0.7, y: 1.5, w: 8.6, h: 0.8,
    fontSize: 38, bold: false, color: theme.text,
    fontFace: "Georgia", italic: true
  });
  slide.addText("running on a 4GB laptop GPU.", {
    x: 0.7, y: 2.25, w: 8.6, h: 0.8,
    fontSize: 38, bold: true, color: theme.text,
    fontFace: "Georgia"
  });

  // Subtitle
  slide.addText("RAG, fine-tuning, tool calling, and JWT auth — all local, MIT-licensed.", {
    x: 0.7, y: 3.25, w: 8.6, h: 0.5,
    fontSize: 16, color: theme.textSoft,
    fontFace: "Segoe UI"
  });

  // Specs row at the bottom
  const specs = ["RTX 3050 4GB", "qwen2.5:3b", "Unsloth LoRA", "Ollama + Qdrant", "93 tests"];
  specs.forEach((s, i) => {
    const x = 0.7 + i * 1.7;
    slide.addText(s, {
      x: x, y: 4.5, w: 1.6, h: 0.3,
      fontSize: 10, color: theme.textSoft, fontFace: "Segoe UI"
    });
    // Tiny underline accent
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 4.82, w: 0.3, h: 0.02,
      fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
    });
  });

  // Footer
  slide.addText("Alvaro  ·  Madrid  ·  github.com/alvrooperez/LLM-agent", {
    x: 0.7, y: 5.2, w: 8.6, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI"
  });
}
module.exports = { createSlide };
