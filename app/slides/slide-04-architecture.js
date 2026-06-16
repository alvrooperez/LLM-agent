// Slide 4 — Architecture diagram
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow
  slide.addText("ARCHITECTURE", {
    x: 0.7, y: 0.5, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.85, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("Five services, one browser tab.", {
    x: 0.7, y: 1.0, w: 8.6, h: 0.7,
    fontSize: 24, bold: true, color: theme.text, fontFace: "Georgia"
  });

  // Architecture diagram — 4 boxes + arrows
  // Box: Browser (top center)
  const drawBox = (x, y, w, h, title, sub, port) => {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: w, h: h,
      fill: { color: theme.surface }, line: { color: theme.border, width: 0.75 }
    });
    slide.addText(title, {
      x: x, y: y + 0.05, w: w, h: 0.3,
      fontSize: 12, bold: true, color: theme.text, fontFace: "Segoe UI", align: "center"
    });
    if (port) {
      slide.addText(port, {
        x: x, y: y + 0.35, w: w, h: 0.25,
        fontSize: 9, color: theme.accent, fontFace: "Segoe UI", align: "center"
      });
    }
    if (sub) {
      slide.addText(sub, {
        x: x + 0.1, y: y + 0.6, w: w - 0.2, h: h - 0.6,
        fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "center"
      });
    }
  };

  // Top: Browser
  drawBox(3.5, 1.85, 3.0, 0.85, "Browser", "Vanilla JS SPA · dark/light", null);

  // Middle: Chat App
  drawBox(3.5, 3.0, 3.0, 0.85, "Chat App", "FastAPI + SSE streaming", ":8090");

  // Bottom 4: agent loop + tools
  // (Agent)
  drawBox(0.7, 4.1, 1.9, 0.9, "Agent loop", "80 lines", null);
  // Ollama
  drawBox(2.85, 4.1, 1.9, 0.9, "Ollama", "qwen2.5:3b FT", ":11434");
  // RAG
  drawBox(5.0, 4.1, 1.9, 0.9, "RAG API", "FastAPI + ST", ":8000");
  // Qdrant
  drawBox(7.15, 4.1, 2.15, 0.9, "Qdrant", "62 chunks, dim 384", ":6333");

  // Arrows (lines)
  // Browser -> Chat
  slide.addShape(pres.shapes.LINE, {
    x: 5.0, y: 2.7, w: 0, h: 0.3,
    line: { color: theme.divider, width: 1, endArrowType: "triangle" }
  });
  // Chat -> all 4
  slide.addShape(pres.shapes.LINE, {
    x: 5.0, y: 3.85, w: -3.35, h: 0.25,
    line: { color: theme.divider, width: 1, endArrowType: "triangle" }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 5.0, y: 3.85, w: -1.2, h: 0.25,
    line: { color: theme.divider, width: 1, endArrowType: "triangle" }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 5.0, y: 3.85, w: 0.95, h: 0.25,
    line: { color: theme.divider, width: 1, endArrowType: "triangle" }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 5.0, y: 3.85, w: 3.1, h: 0.25,
    line: { color: theme.divider, width: 1, endArrowType: "triangle" }
  });

  // Footer
  slide.addText("All services containerized. Bind mounts in dev, images in prod. No cloud APIs.", {
    x: 0.7, y: 5.2, w: 8.6, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI"
  });
  slide.addText("04", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
