function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  slide.addText("Capacity Test - Max Concurrent Users", {
    x: 0.5, y: 0.25, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: theme.primary, fontFace: "Arial"
  });
  slide.addText("Escalating load: 1 -> 2 -> 3 -> 4 concurrent users until failure or p50 > 60s", {
    x: 0.5, y: 0.85, w: 9, h: 0.3,
    fontSize: 11, color: theme.secondary, fontFace: "Arial"
  });

  // Results table
  const tableData = [
    ["Concurrent", "p50 wall", "p95 wall", "Throughput", "Fail rate"],
    ["1 user", "13.3s", "19.2s", "0.07 r/s", "0%"],
    ["2 users", "29.0s", "39.0s", "0.06 r/s", "0%"],
    ["3 users", "42.6s", "45.3s", "0.07 r/s", "0%"],
    ["4 users", "74.3s", "88.4s", "0.05 r/s", "0%"],
  ];
  const colW = [1.6, 1.5, 1.5, 1.6, 1.4];
  tableData.forEach((row, ri) => {
    const isH = ri === 0;
    const y = 1.2 + ri * 0.52;
    row.forEach((cell, ci) => {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0.5 + ci * colW[ci], y: y, w: colW[ci], h: 0.5,
        fill: { color: isH ? theme.light : (ri % 2 === 0 ? theme.bg : theme.light) },
        line: { color: theme.light, width: 0.5 }
      });
      const c = isH ? theme.accent : (cell.includes("4") && ri === 4 ? "f59e0b" : theme.primary);
      slide.addText(cell, {
        x: 0.5 + ci * colW[ci] + 0.08, y: y, w: colW[ci] - 0.12, h: 0.5,
        fontSize: isH ? 11 : 12, bold: isH, color: c,
        fontFace: "Arial", valign: "middle"
      });
    });
  });

  // Conclusion cards
  slide.addText("Conclusions", {
    x: 0.5, y: 3.85, w: 9, h: 0.35,
    fontSize: 13, bold: true, color: theme.accent, fontFace: "Arial"
  });
  const conclusions = [
    { val: "4", label: "Max concurrent users", sub: "before p50 exceeds 60s" },
    { val: "~0.06", label: "Best throughput", sub: "req/s at any load level" },
    { val: "GPU", label: "Bottleneck", sub: "LLM inference on RTX 3050 4GB" },
  ];
  conclusions.forEach((c, i) => {
    const x = 0.5 + i * 3.1;
    slide.addShape(pres.shapes.RECTANGLE, { x: x, y: 4.2, w: 2.9, h: 1.05, fill: { color: theme.light }, rectRadius: 0.08 });
    slide.addText(c.val, { x: x + 0.15, y: 4.25, w: 2.6, h: 0.45, fontSize: 26, bold: true, color: theme.accent, fontFace: "Arial" });
    slide.addText(c.label, { x: x + 0.15, y: 4.7, w: 2.6, h: 0.25, fontSize: 11, bold: true, color: theme.primary, fontFace: "Arial" });
    slide.addText(c.sub, { x: x + 0.15, y: 4.95, w: 2.6, h: 0.2, fontSize: 9, color: theme.secondary, fontFace: "Arial" });
  });

  slide.addText("13", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Arial" });
}
module.exports = { createSlide };
