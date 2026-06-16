// Slide 10 — Performance
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow
  slide.addText("PERFORMANCE", {
    x: 0.7, y: 0.5, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.85, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("Bottleneck, capacity, and one big fix.", {
    x: 0.7, y: 1.0, w: 8.6, h: 0.7,
    fontSize: 24, bold: true, color: theme.text, fontFace: "Georgia"
  });

  // LEFT: Capacity chart (line chart with native)
  const capacityData = [
    { name: "p50 (s)", labels: ["1 user", "2 users", "3 users", "4 users"], values: [13.3, 29.0, 42.6, 74.3] },
    { name: "p95 (s)", labels: ["1 user", "2 users", "3 users", "4 users"], values: [19.2, 39.0, 45.3, 88.4] },
  ];
  slide.addChart(pres.charts.LINE, capacityData, {
    x: 0.7, y: 1.95, w: 4.7, h: 3.2,
    chartColors: [theme.accent, theme.textSoft],
    showLegend: true,
    legendPos: "b",
    legendFontSize: 9,
    legendColor: theme.text,
    catAxisLabelColor: theme.text,
    catAxisLabelFontSize: 10,
    valAxisLabelColor: theme.textSoft,
    valAxisLabelFontSize: 9,
    showTitle: true,
    title: "Server latency by concurrent users",
    titleColor: theme.text,
    titleFontSize: 12,
    showValue: false,
    lineSize: 2,
    lineDataSymbol: "circle",
    lineDataSymbolSize: 6,
    plotArea: { fill: { color: theme.surface } },
    chartArea: { fill: { color: theme.bg } },
  });

  // RIGHT: Two fix cards
  // Fix 1: RAG latency fix
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.6, y: 1.95, w: 3.7, h: 1.5,
    fill: { color: theme.accentSoft }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("69s  →  20s", {
    x: 5.7, y: 2.05, w: 3.5, h: 0.5,
    fontSize: 26, bold: true, color: theme.accent, fontFace: "Georgia"
  });
  slide.addText("RAG query latency fix", {
    x: 5.7, y: 2.55, w: 3.5, h: 0.3,
    fontSize: 11, bold: true, color: theme.text, fontFace: "Segoe UI"
  });
  slide.addText("Agent loop was oscillating on RAG. Early-stop when 2 iterations call the same tools.", {
    x: 5.7, y: 2.85, w: 3.5, h: 0.55,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI"
  });

  // Fix 2: Capacity finding
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.6, y: 3.6, w: 3.7, h: 1.5,
    fill: { color: theme.surface }, line: { color: theme.border, width: 0.75 }
  });
  slide.addText("4 concurrent", {
    x: 5.7, y: 3.7, w: 3.5, h: 0.5,
    fontSize: 26, bold: true, color: theme.text, fontFace: "Georgia"
  });
  slide.addText("Max users before p50 > 60s", {
    x: 5.7, y: 4.2, w: 3.5, h: 0.3,
    fontSize: 11, bold: true, color: theme.text, fontFace: "Segoe UI"
  });
  slide.addText("GPU inference is the bottleneck, not the software stack. Scaling needs more GPUs or batching.", {
    x: 5.7, y: 4.5, w: 3.5, h: 0.55,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI"
  });

  // Page number
  slide.addText("10", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
