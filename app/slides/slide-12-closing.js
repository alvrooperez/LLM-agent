// Slide 12 — Closing / takeaways
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Subtle top accent
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.18,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });

  // Eyebrow
  slide.addText("THANK YOU", {
    x: 0.7, y: 0.7, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.05, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });

  // Big closing message
  slide.addText("Engineering under real constraints.", {
    x: 0.7, y: 1.3, w: 8.6, h: 0.8,
    fontSize: 36, bold: true, color: theme.text, fontFace: "Georgia"
  });
  slide.addText("4GB VRAM, no cloud APIs, 93 tests, MIT-licensed.", {
    x: 0.7, y: 2.15, w: 8.6, h: 0.5,
    fontSize: 16, color: theme.textSoft, fontFace: "Segoe UI", italic: true
  });

  // 3 takeaway columns
  const items = [
    { h: "Defensible decisions", b: "Every choice has a tested 'why'. A/B evals, held-out tests, load profiles." },
    { h: "Honest reporting", b: "Fine-tuning didn't add new capability. The base model already knew. I wrote that down." },
    { h: "Production patterns", b: "JWT auth, rate limiting, scanner block, contextvars, regression runner — from day 1." },
  ];
  items.forEach((it, i) => {
    const x = 0.7 + i * 3.0;
    const y = 3.1;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 2.8, h: 1.4,
      fill: { color: theme.surface }, line: { color: theme.border, width: 0.5 }
    });
    slide.addText(it.h, {
      x: x + 0.2, y: y + 0.15, w: 2.5, h: 0.35,
      fontSize: 14, bold: true, color: theme.text, fontFace: "Segoe UI"
    });
    slide.addText(it.b, {
      x: x + 0.2, y: y + 0.55, w: 2.5, h: 0.8,
      fontSize: 10, color: theme.textSoft, fontFace: "Segoe UI"
    });
  });

  // Footer with links
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 4.85, w: 10, h: 0.78,
    fill: { color: theme.surface }, line: { color: theme.border, width: 0 }
  });
  slide.addText("Demo", {
    x: 0.7, y: 4.95, w: 1.0, h: 0.25,
    fontSize: 9, bold: true, color: theme.textSoft, charSpacing: 2, fontFace: "Segoe UI"
  });
  slide.addText("http://localhost:8090", {
    x: 0.7, y: 5.2, w: 3.0, h: 0.3,
    fontSize: 11, color: theme.accent, fontFace: "Segoe UI"
  });
  slide.addText("Source", {
    x: 3.5, y: 4.95, w: 1.5, h: 0.25,
    fontSize: 9, bold: true, color: theme.textSoft, charSpacing: 2, fontFace: "Segoe UI"
  });
  slide.addText("github.com/alvrooperez/LLM-agent", {
    x: 3.5, y: 5.2, w: 3.5, h: 0.3,
    fontSize: 11, color: theme.accent, fontFace: "Segoe UI"
  });
  slide.addText("Default login", {
    x: 7.0, y: 4.95, w: 2.0, h: 0.25,
    fontSize: 9, bold: true, color: theme.textSoft, charSpacing: 2, fontFace: "Segoe UI"
  });
  slide.addText("admin / admin123", {
    x: 7.0, y: 5.2, w: 2.5, h: 0.3,
    fontSize: 11, color: theme.accent, fontFace: "Consolas"
  });

  // Page number
  slide.addText("12", {
    x: 9.3, y: 0.7, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
