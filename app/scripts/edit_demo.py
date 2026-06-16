"""
Recorta docs/demo.mp4 (2:14) en dos deliverables:
  1. docs/demo.webm   — video completo 1:50 con pausas fuera y speed 1.1x
  2. docs/demo.gif    — highlight 20s (login + GPU + RAG), 800px, 10fps, <5MB

Usa el ffmpeg bundle de imageio-ffmpeg (no requiere ffmpeg en PATH).
"""
import subprocess
import sys
from pathlib import Path

FFMPEG = Path(r"C:\Users\aborb\AppData\Roaming\Python\Python314\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe")
INPUT = Path(r"C:\Users\aborb\.minimax-agent\projects\ai-engineer-portfolio\docs\demo.mp4")
OUT_WEBM = Path(r"C:\Users\aborb\.minimax-agent\projects\ai-engineer-portfolio\docs\demo.webm")
OUT_GIF = Path(r"C:\Users\aborb\.minimax-agent\projects\ai-engineer-portfolio\docs\demo.gif")

DURATION = 134.63  # from immeta
print(f"[INFO] Input: {INPUT} ({DURATION:.1f}s = {int(DURATION//60)}:{DURATION%60:05.2f})")
print(f"[INFO] ffmpeg: {FFMPEG}")
print(f"[INFO] ffmpeg exists: {FFMPEG.exists()}")

def run(args, label):
    print(f"\n[RUN] {label}")
    print(f"  {' '.join(str(a) for a in args)}")
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  STDERR: {r.stderr[-1500:]}")
        sys.exit(1)
    print(f"  OK ({len(r.stdout)} bytes stdout)")

# ─── 1. WEB completo: recortar pausas + speed 1.1x ──────────────────────────
# Plan de recortes en el video ORIGINAL (2:14):
#   KEEP  0:00-0:10   intro pantalla quieta          (10s)
#   CUT   0:10-0:25   login (typing)                (15s)
#   KEEP  0:25-0:55   GPU tool call                 (30s)
#   CUT   0:55-1:05   typing pregunta               (10s)
#   KEEP  1:05-1:30   RAG tool call                 (25s)
#   CUT   1:30-1:50   typing + setup compare         (20s)
#   KEEP  1:50-2:14   compare + cierre              (24s)
# Total KEEP = 10 + 30 + 25 + 24 = 89s ≈ 1:29
# Acelerado 1.1x → ~1:21
# Más generoso: incluyo login y typing → 1:50 final

# Versión pragmática: 2 segmentos largos
seg1 = ["0:00", "1:05"]  # intro + login + GPU + inicio typing RAG (65s)
seg2 = ["1:30", "2:14"]  # compare + cierre (44s)
# Total = 109s @ 1.1x = 99s = 1:39  ✓

# Construir filter_complex para trim + concat + setpts (speed)
vf_filter = (
    f"[0:v]trim=start=0:end=65,setpts=PTS-STARTPTS,setpts=PTS/1.1[v0];"
    f"[0:a]atrim=start=0:end=65,asetpts=PTS-STARTPTS,atempo=1.1[a0];"
    f"[0:v]trim=start=90:end=134.63,setpts=PTS-STARTPTS,setpts=PTS/1.1[v1];"
    f"[0:a]atrim=start=90:end=134.63,asetpts=PTS-STARTPTS,atempo=1.1[a1];"
    f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
)
run([
    str(FFMPEG), "-y", "-i", str(INPUT),
    "-filter_complex", vf_filter,
    "-map", "[outv]", "-map", "[outa]",
    "-c:v", "libvpx-vp9", "-b:v", "1M", "-deadline", "realtime", "-cpu-used", "4",
    "-c:a", "libopus", "-b:a", "96k",
    str(OUT_WEBM),
], f"WEBM completo (speed 1.1x, ~99s)")

# ─── 2. GIF highlight 20s ────────────────────────────────────────────────────
# Clips para el GIF (sin audio):
#   0:25-0:55  GPU tool call (30s) — el highlight más claro
#   1:05-1:30  RAG tool call (25s) — segundo highlight
#   → recorte a 10s + 10s = 20s total
gif_filter = (
    f"[0:v]trim=start=25:end=35,setpts=PTS-STARTPTS,scale=800:-2:flags=lanczos[v0];"
    f"[0:v]trim=start=65:end=75,setpts=PTS-STARTPTS,scale=800:-2:flags=lanczos[v1];"
    f"[v0][v1]concat=n=2:v=1:a=0[outv];"
    f"[outv]split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
)
run([
    str(FFMPEG), "-y", "-i", str(INPUT),
    "-filter_complex", gif_filter,
    "-r", "10",  # 10 fps para que pese poco
    "-loop", "0",
    str(OUT_GIF),
], f"GIF highlight 20s, 800px, 10fps, palettegen")

# ─── Reporte final ──────────────────────────────────────────────────────────
for p in [OUT_WEBM, OUT_GIF]:
    if p.exists():
        mb = p.stat().st_size / 1024 / 1024
        print(f"\n[OK] {p.name}: {mb:.2f} MB")
    else:
        print(f"\n[FAIL] {p.name}: no se generó")
