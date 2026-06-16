// Slide 2 — Table of Contents
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow + title
  slide.addText("CONTENTS", {
    x: 0.7, y: 0.7, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.05, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("What's inside", {
    x: 0.7, y: 1.25, w: 8.6, h: 0.7,
    fontSize: 32, bold: false, color: theme.text, fontFace: "Georgia"
  });

  // Sections
  const sections = [
    { num: "01", title: "The project", desc: "What I built, why, and the constraints" },
    { num: "02", title: "Architecture", desc: "Browser · FastAPI · Agent loop · Ollama · Qdrant" },
    { num: "03", title: "RAG pipeline", desc: "Vector search over AI engineering docs (+83% relevance)" },
    { num: "04", title: "Fine-tuning", desc: "Unsloth LoRA, 230 examples, honest evaluation" },
    { num: "05", title: "Tool-calling agent", desc: "6 tools, 80-line loop, multi-tool chaining" },
    { num: "06", title: "Performance", desc: "Load test, capacity, RAG latency, fixes" },
    { num: "07", title: "Authentication", desc: "JWT login, scrypt, rate limiting, security" },
    { num: "08", title: "What this demonstrates", desc: "Engineering under real constraints" },
  ];

  // Two columns
  sections.forEach((s, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.7 + col * 4.5;
    const y = 2.4 + row * 0.65;

    // Section number (serif, accent)
    slide.addText(s.num, {
      x: x, y: y, w: 0.5, h: 0.5,
      fontSize: 22, color: theme.accent, fontFace: "Georgia", italic: true
    });
    // Title
    slide.addText(s.title, {
      x: x + 0.6, y: y, w: 3.8, h: 0.3,
      fontSize: 14, bold: true, color: theme.text, fontFace: "Segoe UI"
    });
    // Description
    slide.addText(s.desc, {
      x: x + 0.6, y: y + 0.3, w: 3.8, h: 0.25,
      fontSize: 10, color: theme.textSoft, fontFace: "Segoe UI"
    });
  });

  // Page number
  slide.addText("02", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
