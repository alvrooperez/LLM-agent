// Slide 7 — Fine-tuning setup
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow
  slide.addText("FINE-TUNING", {
    x: 0.7, y: 0.5, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.85, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("Unsloth LoRA on tool-calling examples.", {
    x: 0.7, y: 1.0, w: 8.6, h: 0.7,
    fontSize: 24, bold: true, color: theme.text, fontFace: "Georgia"
  });

  // Pipeline (vertical timeline)
  const phases = [
    { num: "1", title: "Generate dataset", body: "230 train / 15 held-out test. Tool-call pairs in JSONL.", time: "~10 min" },
    { num: "2", title: "Train with Unsloth", body: "LoRA r=16, 2 epochs, batch=2, grad_accum=4. ~28 min on RTX 3050.", time: "28 min" },
    { num: "3", title: "Merge to GGUF", body: "CPU merge, then llama.cpp Q4_K_M quantization. Final model: 1.93 GB.", time: "~3 min" },
    { num: "4", title: "Register in Ollama", body: "Modelfile + system prompt. Hot-load with `ollama create`.", time: "<1 min" },
  ];
  phases.forEach((p, i) => {
    const y = 2.0 + i * 0.78;
    // Number circle (thin outline, not filled)
    slide.addShape(pres.shapes.OVAL, {
      x: 0.7, y: y, w: 0.55, h: 0.55,
      fill: { color: theme.bg }, line: { color: theme.accent, width: 1.25 }
    });
    slide.addText(p.num, {
      x: 0.7, y: y, w: 0.55, h: 0.55,
      fontSize: 18, color: theme.accent, fontFace: "Georgia", italic: true,
      align: "center", valign: "middle"
    });
    // Title
    slide.addText(p.title, {
      x: 1.45, y: y - 0.05, w: 5.5, h: 0.3,
      fontSize: 13, bold: true, color: theme.text, fontFace: "Segoe UI"
    });
    // Body
    slide.addText(p.body, {
      x: 1.45, y: y + 0.25, w: 5.5, h: 0.5,
      fontSize: 10, color: theme.textSoft, fontFace: "Segoe UI"
    });
    // Time (right, monospace-ish)
    slide.addText(p.time, {
      x: 7.0, y: y + 0.05, w: 1.5, h: 0.3,
      fontSize: 11, color: theme.accent, fontFace: "Segoe UI", align: "right", bold: true
    });
  });

  // Page number
  slide.addText("07", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
