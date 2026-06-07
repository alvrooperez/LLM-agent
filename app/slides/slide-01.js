function createSlide(pres, theme) {
  const slide = pres.addSlide();
  // Dark background
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  // Accent block top
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: theme.accent } });
  // Left accent bar
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.12, h: 5.625, fill: { color: theme.accent } });
  // Subtle grid lines
  for (let i = 1; i < 10; i++) {
    slide.addShape(pres.shapes.LINE, { x: i, y: 0, w: 0, h: 5.625, line: { color: theme.light, width: 0.3, transparency: 80 } });
  }
  // Title
  slide.addText("AI Engineering Portfolio", {
    x: 0.6, y: 1.5, w: 8.8, h: 1.4,
    fontSize: 54, bold: true, color: theme.primary,
    fontFace: "Arial", fit: "shrink"
  });
  // Subtitle
  slide.addText("Local LLM with RAG, Fine-tuning & Tool Calling", {
    x: 0.6, y: 3.0, w: 8.8, h: 0.6,
    fontSize: 22, color: theme.secondary, fontFace: "Arial"
  });
  // Divider line
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 3.7, w: 3.0, h: 0.04, fill: { color: theme.accent } });
  // Meta
  slide.addText("RTX 3050 4GB  |  MSI Katana GF66  |  Windows 11", {
    x: 0.6, y: 4.0, w: 8, h: 0.4,
    fontSize: 13, color: theme.secondary, fontFace: "Arial"
  });
  slide.addText("June 2025", {
    x: 0.6, y: 4.5, w: 8, h: 0.3,
    fontSize: 12, color: theme.secondary, fontFace: "Arial"
  });
  // Gold badge top right
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 8.0, y: 0.4, w: 1.7, h: 0.5,
    fill: { color: theme.accent }, rectRadius: 0.06
  });
  slide.addText("NO CLOUD", {
    x: 8.0, y: 0.4, w: 1.7, h: 0.5,
    fontSize: 11, bold: true, color: theme.bg, align: "center", valign: "middle",
    fontFace: "Arial"
  });
}
module.exports = { createSlide };
