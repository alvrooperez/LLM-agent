// Slide 3 — The project (hero with screenshot)
const path = require('path');
const SCREENSHOTS = 'C:/Users/aborb/.minimax-agent/projects/ai-engineer-portfolio/docs/screenshots/';

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow
  slide.addText("THE PROJECT", {
    x: 0.7, y: 0.5, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.85, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });

  // Title
  slide.addText("A local LLM agent that runs entirely on a laptop GPU.", {
    x: 0.7, y: 1.0, w: 8.6, h: 0.7,
    fontSize: 24, bold: true, color: theme.text, fontFace: "Georgia"
  });

  // LEFT: text
  const bullets = [
    { h: "Inference", b: "Ollama serves qwen2.5:3b at 68 tok/s, Q4_K_M quantized to 1.9 GB." },
    { h: "RAG", b: "Qdrant vector DB + sentence-transformers. +83% answer relevance vs no-RAG." },
    { h: "Fine-tuning", b: "Unsloth LoRA on 230 tool-calling examples. GGUF Q4_K_M export, no quality regression." },
    { h: "Agent", b: "80-line tool-calling loop, 6 real tools, multi-tool chaining, native Ollama tool calling." },
  ];
  bullets.forEach((bl, i) => {
    const y = 1.95 + i * 0.7;
    // Tiny accent square
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: y + 0.08, w: 0.08, h: 0.08,
      fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
    });
    slide.addText(bl.h, {
      x: 0.95, y: y, w: 4.0, h: 0.25,
      fontSize: 12, bold: true, color: theme.text, fontFace: "Segoe UI"
    });
    slide.addText(bl.b, {
      x: 0.95, y: y + 0.26, w: 4.0, h: 0.45,
      fontSize: 10, color: theme.textSoft, fontFace: "Segoe UI"
    });
  });

  // RIGHT: Screenshot
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.4, y: 1.85, w: 4.0, h: 2.85,
    fill: { color: theme.surface }, line: { color: theme.border, width: 0.75 }
  });
  slide.addImage({
    path: SCREENSHOTS + '02-welcome.png',
    x: 5.5, y: 1.93, w: 3.8, h: 2.69,
    sizing: { type: 'contain', w: 3.8, h: 2.69 }
  });
  // Caption
  slide.addText("Chat welcome screen — login required, JWT auth", {
    x: 5.4, y: 4.75, w: 4.0, h: 0.25,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", italic: true
  });

  // Page number
  slide.addText("03", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
