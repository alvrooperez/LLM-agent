function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: theme.accent } });
  slide.addText("Performance - Load Test (Phase 5D)", {
    x: 0.5, y: 0.25, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: theme.primary, fontFace: "Arial"
  });

  // Config
  slide.addText("Config: 3 concurrent users, 12 total requests, warmup=2", {
    x: 0.5, y: 0.85, w: 9, h: 0.3,
    fontSize: 11, color: theme.secondary, fontFace: "Arial"
  });

  // Stat cards top row
  const topStats = [
    { val: "12/12", label: "Successful requests", sub: "100% success rate" },
    { val: "10.2s", label: "Server p50 latency", sub: "wall clock 36.5s" },
    { val: "0", label: "Failures", sub: "0% error rate" },
    { val: "1.00", label: "Tools per request", sub: "avg tool call rate" },
  ];
  topStats.forEach((s, i) => {
    const x = 0.5 + i * 2.35;
    slide.addShape(pres.shapes.RECTANGLE, { x: x, y: 1.15, w: 2.15, h: 1.1, fill: { color: theme.light }, rectRadius: 0.08 });
    slide.addText(s.val, { x: x, y: 1.18, w: 2.15, h: 0.6, fontSize: 30, bold: true, color: theme.accent, align: "center", fontFace: "Arial" });
    slide.addText(s.label, { x: x + 0.1, y: 1.75, w: 1.95, h: 0.25, fontSize: 10, bold: true, color: theme.primary, align: "center", fontFace: "Arial" });
    slide.addText(s.sub, { x: x + 0.1, y: 1.98, w: 1.95, h: 0.2, fontSize: 9, color: theme.secondary, align: "center", fontFace: "Arial" });
  });

  // Latency bars
  slide.addText("Server-side latency distribution", {
    x: 0.5, y: 2.45, w: 9, h: 0.35,
    fontSize: 13, bold: true, color: theme.primary, fontFace: "Arial"
  });
  const bars = [
    { label: "p50", val: 10240, color: theme.accent },
    { label: "p95", val: 62170, color: "f59e0b" },
    { label: "max", val: 88000, color: "ef4444" },
  ];
  const maxBar = 88000;
  bars.forEach((b, i) => {
    const y = 2.85 + i * 0.52;
    slide.addText(b.label, { x: 0.5, y: y, w: 0.5, h: 0.42, fontSize: 11, bold: true, color: theme.secondary, valign: "middle", fontFace: "Arial" });
    slide.addShape(pres.shapes.RECTANGLE, { x: 1.05, y: y + 0.08, w: 5.5, h: 0.28, fill: { color: theme.light }, rectRadius: 0.04 });
    const barW = (b.val / maxBar) * 5.5;
    slide.addShape(pres.shapes.RECTANGLE, { x: 1.05, y: y + 0.08, w: barW, h: 0.28, fill: { color: b.color }, rectRadius: 0.04 });
    slide.addText((b.val / 1000).toFixed(1) + "s", { x: 1.1 + barW, y: y, w: 0.8, h: 0.42, fontSize: 11, color: theme.primary, valign: "middle", fontFace: "Arial" });
  });

  // VRAM note
  slide.addShape(pres.shapes.RECTANGLE, { x: 7.0, y: 2.85, w: 2.5, h: 1.3, fill: { color: theme.light }, rectRadius: 0.08 });
  slide.addText("VRAM stable", { x: 7.15, y: 2.95, w: 2.2, h: 0.3, fontSize: 11, bold: true, color: "10b981", fontFace: "Arial" });
  slide.addText("2354 -> 2337 MB\nDelta: -17 MB\nNo memory leak", {
    x: 7.15, y: 3.28, w: 2.2, h: 0.8,
    fontSize: 10, color: theme.secondary, fontFace: "Arial"
  });

  // Bottom
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.6, w: 9, h: 0.7, fill: { color: theme.light }, rectRadius: 0.08 });
  slide.addText("One notable case: RAG query triggered 5 tool calls in a single response (multi-step chaining within one iteration).", {
    x: 0.7, y: 4.7, w: 8.6, h: 0.5,
    fontSize: 11, color: theme.secondary, fontFace: "Arial"
  });
  slide.addText("12", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Arial" });
}
module.exports = { createSlide };
