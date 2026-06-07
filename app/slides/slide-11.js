function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  slide.addText("Multi-tool Chaining (Phase 5F)", {
    x: 0.5, y: 0.25, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: theme.primary, fontFace: "Segoe UI"
  });

  // Big result
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.9, w: 2.8, h: 1.6, fill: { color: theme.light }, rectRadius: 0.1 });
  slide.addText("5/5", {
    x: 0.5, y: 0.9, w: 2.8, h: 1.0,
    fontSize: 72, bold: true, color: "10b981", align: "center", fontFace: "Segoe UI"
  });
  slide.addText("PASS  |  Chaining rate 100%", {
    x: 0.5, y: 1.9, w: 2.8, h: 0.5,
    fontSize: 10, bold: true, color: theme.secondary, align: "center", fontFace: "Segoe UI"
  });

  // Task table
  const tasks = [
    ["Task", "Tools expected", "Result"],
    ["GPU + Qdrant", "get_gpu_stats, get_collection_info", "PASS"],
    ["Docs + Models", "search_docs, list_models", "PASS"],
    ["Models + GPU", "list_models, get_gpu_stats", "PASS"],
    ["PDF + GPU", "write_document, get_gpu_stats", "PASS"],
    ["3-tool chain", "get_collection_info, list_models, get_gpu_stats", "PASS"],
  ];
  const tX = 3.6;
  const tW = [1.4, 2.5, 2.4];
  tasks.forEach((row, ri) => {
    const isH = ri === 0;
    const y = 0.9 + ri * 0.52;
    row.forEach((cell, ci) => {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: tX + ci * tW[ci], y: y, w: tW[ci], h: 0.5,
        fill: { color: isH ? theme.light : (ri % 2 === 0 ? theme.bg : theme.light) },
        line: { color: theme.light, width: 0.5 }
      });
      const c = isH ? theme.accent : cell === "PASS" ? "10b981" : theme.primary;
      slide.addText(cell, {
        x: tX + ci * tW[ci] + 0.08, y: y, w: tW[ci] - 0.12, h: 0.5,
        fontSize: isH ? 10 : 11, bold: isH, color: c,
        fontFace: "Segoe UI", valign: "middle"
      });
    });
  });

  // What this means
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.1, w: 9, h: 1.15, fill: { color: theme.light }, rectRadius: 0.08 });
  slide.addText("The model plans and executes multiple tools in parallel - without asking the user.", {
    x: 0.7, y: 4.2, w: 8.6, h: 0.4,
    fontSize: 14, bold: true, color: theme.primary, fontFace: "Segoe UI"
  });
  slide.addText("In a single iteration, the agent receives a multi-part query and calls 2-3 tools simultaneously. No user re-prompts, no separate turns. This is real agent capability - not scripted sequences.", {
    x: 0.7, y: 4.62, w: 8.6, h: 0.55,
    fontSize: 11, color: theme.secondary, fontFace: "Segoe UI"
  });
  slide.addText("11", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Segoe UI" });
}
module.exports = { createSlide };
