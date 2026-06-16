// Slide 11 — Authentication
const path = require('path');
const SCREENSHOTS = 'C:/Users/aborb/.minimax-agent/projects/ai-engineer-portfolio/docs/screenshots/';

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Eyebrow
  slide.addText("AUTHENTICATION", {
    x: 0.7, y: 0.5, w: 8.5, h: 0.3,
    fontSize: 10, bold: true, color: theme.accent, charSpacing: 4,
    fontFace: "Segoe UI"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 0.85, w: 1.2, h: 0.025,
    fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
  });
  slide.addText("JWT login with scrypt-hashed passwords.", {
    x: 0.7, y: 1.0, w: 8.6, h: 0.7,
    fontSize: 24, bold: true, color: theme.text, fontFace: "Georgia"
  });

  // LEFT: Stack
  slide.addText("Stack", {
    x: 0.7, y: 1.95, w: 4.0, h: 0.3,
    fontSize: 12, bold: true, color: theme.textSoft, fontFace: "Segoe UI", charSpacing: 2
  });

  const stack = [
    { layer: "User storage", detail: "data/users.json · scrypt$n=2^14, r=8, p=1" },
    { layer: "Password verify", detail: "constant-time compare, ~50ms per attempt" },
    { layer: "Token", detail: "JWT HS256 · 24h expiry · sessionStorage" },
    { layer: "Endpoint guard", detail: "FastAPI dependency on every route except /health" },
    { layer: "Rate limit", detail: "10 login/min per IP (anti brute-force)" },
  ];
  stack.forEach((s, i) => {
    const y = 2.3 + i * 0.55;
    // Code-style label
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: y + 0.05, w: 0.05, h: 0.4,
      fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }
    });
    slide.addText(s.layer, {
      x: 0.85, y: y, w: 4.0, h: 0.25,
      fontSize: 11, bold: true, color: theme.text, fontFace: "Segoe UI"
    });
    slide.addText(s.detail, {
      x: 0.85, y: y + 0.24, w: 4.0, h: 0.3,
      fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI"
    });
  });

  // RIGHT: Screenshot of login
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.4, y: 1.85, w: 4.0, h: 3.0,
    fill: { color: theme.surface }, line: { color: theme.border, width: 0.75 }
  });
  slide.addImage({
    path: SCREENSHOTS + '01-login.png',
    x: 5.5, y: 1.93, w: 3.8, h: 2.84,
    sizing: { type: 'contain', w: 3.8, h: 2.84 }
  });
  slide.addText("Login screen — full-screen gate before the chat loads", {
    x: 5.4, y: 4.9, w: 4.0, h: 0.25,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", italic: true
  });

  // Page number
  slide.addText("11", {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3,
    fontSize: 9, color: theme.textSoft, fontFace: "Segoe UI", align: "right"
  });
}
module.exports = { createSlide };
