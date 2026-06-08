"""
make_demo_gif.py — Captura la pantalla y crea un GIF animado.

Uso:
  1. Abre Chrome en http://localhost:8090
  2. Maximiza la ventana
  3. Ejecuta este script: python make_demo_gif.py
  4. Durante 30s, interactua con el chat (escribe queries, muestra tool calls)
  5. Para parar antes: Ctrl+C
  6. El GIF se guarda en docs/demo.gif

Flags:
  --duration 30       segundos a capturar (default 30)
  --fps 10            frames por segundo (default 10, mas bajo = GIF mas pequeño)
  --output demo.gif   ruta de salida (default docs/demo.gif)
  --region auto       captura la ventana activa (default); o WxH+X+Y
"""
import argparse
import sys
import time
from pathlib import Path
from PIL import Image
import mss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=30, help="segundos a capturar")
    parser.add_argument("--fps", type=int, default=10, help="frames por segundo")
    parser.add_argument("--output", default="docs/demo.gif", help="ruta de salida")
    parser.add_argument("--region", default="auto",
                        help="auto = ventana activa; o WxH+X+Y (ej. 1920x1080+0+0)")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    interval = 1.0 / args.fps
    total_frames = args.duration * args.fps

    print(f"Capturando {args.duration}s @ {args.fps} fps = {total_frames} frames")
    print(f"Region: {args.region}")
    print(f"Output: {out_path}")
    print("Interactua con el chat. Ctrl+C para parar antes.")

    frames = []
    sct = mss.mss()

    if args.region == "auto":
        # Capturar monitor 1 completo
        monitor = sct.monitors[1]
        region_def = {
            "left": monitor["left"],
            "top": monitor["top"],
            "width": monitor["width"],
            "height": monitor["height"],
        }
    else:
        # Parsear WxH+X+Y
        import re
        m = re.match(r"(\d+)x(\d+)\+(\d+)\+(\d+)", args.region)
        if not m:
            print(f"ERROR: region invalido '{args.region}'", file=sys.stderr)
            sys.exit(1)
        w, h, x, y = map(int, m.groups())
        region_def = {"left": x, "top": y, "width": w, "height": h}

    start = time.time()
    try:
        for i in range(total_frames):
            t0 = time.time()
            img = sct.grab(region_def)
            # Convertir mss image a PIL
            pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            # Reducir tamaño para GIF (max 1280px de ancho)
            max_w = 1280
            if pil.width > max_w:
                ratio = max_w / pil.width
                new_size = (max_w, int(pil.height * ratio))
                pil = pil.resize(new_size, Image.LANCZOS)
            frames.append(pil)

            if i % args.fps == 0:
                elapsed = time.time() - start
                print(f"  Frame {i}/{total_frames} ({elapsed:.1f}s)")

            # Esperar el siguiente frame
            elapsed_frame = time.time() - t0
            sleep_time = max(0, interval - elapsed_frame)
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        print("\nParada manual")

    if not frames:
        print("ERROR: no se capturaron frames", file=sys.stderr)
        sys.exit(1)

    print(f"\n{len(frames)} frames capturados. Creando GIF...")

    # Crear GIF
    duration_ms = int(1000 / args.fps)
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )

    size_kb = out_path.stat().st_size / 1024
    print(f"GIF guardado: {out_path} ({size_kb:.0f} KB)")
    print(f"Total captura: {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
