function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  // Large number
  slide.addText("01", {
    x: 0.5, y: 1.2, w: 3, h: 1.8,
    fontSize: 120, bold: true, color: theme.accent, fontFace: "Arial", transparency: 15
  });
  // Section title
  slide.addText("Hardware & Architecture", {
    x: 0.5, y: 2.5, w: 9, h: 0.9,
    fontSize: 42, bold: true, color: theme.primary, fontFace: "Arial"
  });
  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.5, w: 2.5, h: 0.05, fill: { color: theme.accent } });
  // Subtitle
  slide.addText("RTX 3050 4GB  |  16GB RAM  |  Windows 11  |  Docker Desktop", {
    x: 0.5, y: 3.7, w: 9, h: 0.4,
    fontSize: 14, color: theme.secondary, fontFace: "Arial"
  });
  slide.addText("Full local stack - no cloud APIs", {
    x: 0.5, y: 4.15, w: 9, h: 0.35,
    fontSize: 13, color: theme.accent, fontFace: "Arial", italic: true
  });
  slide.addText("03", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Arial" });
}
module.exports = { createSlide };
