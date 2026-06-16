// Slide 9 — Tool-calling agent with screenshot
const path = require('path');
const SCREENSHOTS = 'C:/Users/aborb/.minimax-agent/projects/ai-engineer-portfolio/docs/screenshots/';

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow
  slide.addText("TOOL-CALLING AGENT", {
    x: 0.7, y: 0.5, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.85, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("6 tools. 80-line loop. No LangChain.", {
    x: 0.7, y: 1.0, w: 8.6, h: 0.7,
    fontSize: 24, bold: true, color: theme.text, fontFace: "Georgia"
  });

  // LEFT: 6 tools grid
  const tools = [
    { name: "search_docs", desc: "RAG over docs" },
    { name: "list_models", desc: "Ollama inventory" },
    { name: "get_gpu_stats", desc: "VRAM / util" },
    { name: "get_collection_info", desc: "Qdrant metadata" },
    { name: "plot_metric", desc: "matplotlib chart" },
    { name: "write_document", desc: "PDF report" },
  ];
  const cellW = 2.1;
  const cellH = 0.7;
  tools.forEach((t, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.7 + col * (cellW + 0.1);
    const y = 1.95 + row * (cellH + 0.1);
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: cellW, h: cellH,
      fill: { color: theme.surface }, line: { color: theme.border, width: 0.5 }
    });
    // Tiny code-style name
    slide.addText(t.name + "()", {
      x: x + 0.1, y: y + 0.05, w: cellW - 0.2, h: 0.3,
      fontSize: 10, bold: true, color: theme.accent, fontFace: "Consolas"
    });
    slide.addText(t.desc, {
      x: x + 0.1, y: y + 0.35, w: cellW - 0.2, h: 0.3,
      fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI"
    });
  });

  // Multi-tool chaining stat
  slide.addText("Multi-tool chaining: 5/5 PASS", {
    x: 0.7, y: 4.4, w: 4.3, h: 0.3,
    fontSize: 12, bold: true, color: theme.text, fontFace: "Segoe UI"
  });
  slide.addText("Agent plans 2-3 tool calls in a single turn when the task spans them.", {
    x: 0.7, y: 4.7, w: 4.3, h: 0.4,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI"
  });

  // RIGHT: Screenshot
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.3, y: 1.85, w: 4.0, h: 2.85,
    fill: { color: theme.surface }, line: { color: theme.border, width: 0.75 }
  });
  slide.addImage({
    path: SCREENSHOTS + '03-chat-tool-call.png',
    x: 5.4, y: 1.93, w: 3.8, h: 2.69,
    sizing: { type: 'contain', w: 3.8, h: 2.69 }
  });
  slide.addText("Live tool call: get_gpu_stats() → result → answer", {
    x: 5.3, y: 4.75, w: 4.0, h: 0.25,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", italic: true
  });

  // Page number
  slide.addText("09", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
