function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: theme.bg } });
  slide.addText("03", {
    x: 0.5, y: 1.2, w: 3, h: 1.8,
    fontSize: 120, bold: true, color: theme.accent, fontFace: "Segoe UI", transparency: 15
  });
  slide.addText("Fine-tuning", {
    x: 0.5, y: 2.5, w: 9, h: 0.9,
    fontSize: 42, bold: true, color: theme.primary, fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.5, w: 2.5, h: 0.05, fill: { color: theme.accent } });
  slide.addText("Unsloth LoRA on tool-calling examples  |  230 train / 15 held-out test", {
    x: 0.5, y: 3.7, w: 9, h: 0.4,
    fontSize: 14, color: theme.secondary, fontFace: "Segoe UI"
  });
  slide.addText("07", { x: 9.3, y: 5.1, w: 0.5, h: 0.35, fontSize: 10, color: theme.secondary, fontFace: "Segoe UI" });
}
module.exports = { createSlide };
