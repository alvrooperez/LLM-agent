// Slide 6 — RAG evaluation results
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow
  slide.addText("RAG EVALUATION", {
    x: 0.7, y: 0.5, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.85, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("What retrieval actually buys you.", {
    x: 0.7, y: 1.0, w: 8.6, h: 0.7,
    fontSize: 24, bold: true, color: theme.text, fontFace: "Georgia"
  });

  // LEFT: native bar chart (no-RAG vs RAG relevance)
  const chartData = [{
    name: "Answer relevance (judge, 1-5)",
    labels: ["No RAG", "With RAG"],
    values: [2.4, 4.4],
  }];
  slide.addChart(pres.charts.BAR, chartData, {
    x: 0.7, y: 1.95, w: 5.0, h: 3.2,
    barDir: "col",
    barGrouping: "standard",
    chartColors: [theme.accent],
    showLegend: false,
    catAxisLabelColor: theme.text,
    catAxisLabelFontSize: 11,
    catAxisLabelFontFace: "Segoe UI",
    valAxisLabelColor: theme.textSoft,
    valAxisLabelFontSize: 9,
    valAxisMinVal: 0,
    valAxisMaxVal: 5,
    showValue: true,
    dataLabelColor: theme.text,
    dataLabelFontSize: 11,
    dataLabelFontBold: true,
    dataLabelFormatCode: "0.0",
    plotArea: { fill: { color: theme.surface } },
    chartArea: { fill: { color: theme.bg } },
  });

  // RIGHT: stats
  const stats = [
    { val: "+83%", label: "relevance improvement", sub: "judge model 1-5 scale" },
    { val: "62", label: "doc chunks indexed", sub: "AI engineering knowledge" },
    { val: "~2.5s", label: "retrieval overhead", sub: "embed + Qdrant search" },
    { val: "100%", label: "local & private", sub: "no doc leaves the laptop" },
  ];
  stats.forEach((s, i) => {
    const y = 1.95 + i * 0.8;
    slide.addText(s.val, {
      x: 6.0, y: y, w: 1.5, h: 0.45,
      fontSize: 26, bold: true, color: theme.accent, fontFace: "Segoe UI"
    });
    slide.addText(s.label, {
      x: 7.5, y: y + 0.04, w: 2.0, h: 0.25,
      fontSize: 11, bold: true, color: theme.text, fontFace: "Segoe UI"
    });
    slide.addText(s.sub, {
      x: 7.5, y: y + 0.3, w: 2.0, h: 0.25,
      fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI"
    });
    // Divider
    if (i < stats.length - 1) {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 6.0, y: y + 0.7, w: 3.3, h: 0.01,
        fill: { color: theme.border }, line: { color: theme.border, width: 0 }
      });
    }
  });

  // Page number
  slide.addText("06", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
