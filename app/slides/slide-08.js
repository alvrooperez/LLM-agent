function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  slide.addText("Fine-tuning Results", {
    x: 0.5, y: 0.25, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: theme.primary, fontFace: "Arial"
  });

  // LEFT: Stats
  const stats = [
    { val: "230", label: "Train examples", sub: "tool-calling pairs" },
    { val: "15", label: "Held-out test", sub: "for honest eval" },
    { val: "1.9GB", label: "GGUF Q4_K_M", sub: "final model size" },
    { val: "28min", label: "Training time", sub: "RTX 3050" },
  ];
  stats.forEach((s, i) => {
    const y = 0.95 + i * 0.72;
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: y, w: 2.0, h: 0.6, fill: { color: theme.light }, rectRadius: 0.06 });
    slide.addText(s.val, { x: 0.6, y: y + 0.02, w: 1.8, h: 0.32, fontSize: 20, bold: true, color: theme.accent, fontFace: "Arial" });
    slide.addText(s.label, { x: 0.6, y: y + 0.32, w: 1.8, h: 0.2, fontSize: 9, color: theme.secondary, fontFace: "Arial" });
  });

  // RIGHT: Comparison table
  slide.addText("A/B Evaluation - Base vs Fine-tuned", {
    x: 2.8, y: 0.95, w: 6.7, h: 0.4,
    fontSize: 14, bold: true, color: theme.primary, fontFace: "Arial"
  });
  const rows = [
    ["Metric", "Base (qwen2.5:3b)", "Fine-tuned"],
    ["Tool call rate", "7%", "7%"],
    ["Avg iterations/task", "2.2", "2.0"],
    ["Response length", "315 chars", "279 chars"],
    ["RAG answer relevance", "baseline", "+83%"],
  ];
  const colW = [2.1, 2.1, 2.1];
  const tableX = 2.8;
  const tableY = 1.4;
  rows.forEach((row, ri) => {
    const isHeader = ri === 0;
    const rowH = 0.52;
    row.forEach((cell, ci) => {
      const x = tableX + ci * colW[ci];
      const y = tableY + ri * rowH;
      slide.addShape(pres.shapes.RECTANGLE, {
        x: x, y: y, w: colW[ci], h: rowH,
        fill: { color: isHeader ? theme.light : (ri % 2 === 0 ? theme.bg : theme.light) },
        line: { color: theme.light, width: 0.5 }
      });
      const textColor = isHeader ? theme.accent : (cell === "7%" && ci === 2 ? theme.accent : cell === "7%" && ci === 1 ? theme.accent : cell.includes("+") ? "10b981" : theme.primary);
      slide.addText(cell, {
        x: x + 0.1, y: y, w: colW[ci] - 0.15, h: rowH,
        fontSize: isHeader ? 11 : 12, bold: isHeader, color: textColor,
        fontFace: "Arial", valign: "middle"
      });
    });
  });

  // Honest finding callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 2.8, y: 4.1, w: 6.7, h: 1.15, fill: { color: theme.light }, rectRadius: 0.08 });
  slide.addText("Honest Finding", {
    x: 3.0, y: 4.2, w: 6.3, h: 0.35,
    fontSize: 12, bold: true, color: theme.accent, fontFace: "Arial"
  });
  slide.addText("qwen2.5:3b base already knows the tool-calling format. Fine-tuning did not add new capability - it reduced response length by 11% and iterations by 9%. Zero regression in tool call rate.", {
    x: 3.0, y: 4.55, w: 6.3, h: 0.6,
    fontSize: 11, color: theme.secondary, fontFace: "Arial"
  });
  slide.addText("08", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Arial" });
}
module.exports = { createSlide };
