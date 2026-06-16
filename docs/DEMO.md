# Demo assets

Video and GIF walkthroughs of the chat app, used in the README, the PPT
deck, and the LinkedIn launch post.

## Files

| File | Size | Duration | Use |
|---|---|---|---|
| `docs/demo.webm` | ~9 MB | 1:39 | Full demo with audio. Embed in PPT or host on Loom/YouTube. |
| `docs/demo.gif`  | ~3 MB | 17 s @ 8× speed | README hero, LinkedIn post, Twitter, anywhere a still image is too little and a video is too much. |

Both files are generated from a single OBS recording of a real run against
the local stack (Ollama + Qdrant + chat app on :8090).

## How the recording was made

1. Stack up: Ollama (with `qwen2.5:3b` + `qwen2.5-rag-ft`), Qdrant, chat app.
2. Chrome window 1280×800 at `http://localhost:8090`, F11 for clean view.
3. OBS → Scenes: "Demo" → Sources: `+` → Window capture → select Chrome.
4. Start recording, follow the script in `docs/DEMO_SCRIPT.md`, stop.
5. Run `python scripts/edit_demo.py` to produce both deliverables.

## How the deliverables were generated

`app/scripts/edit_demo.py` uses the ffmpeg binary that ships
with `imageio-ffmpeg` (no system ffmpeg install needed) to:

- **WEBM** — keep two non-overlapping segments (intro+login+GPU, then
  compare+cierre), drop the typing pauses, accelerate 1.1×, encode with
  `libvpx-vp9` + `libopus`. ~1:39 output, ~9 MB.
- **GIF** — speed the whole video 8×, scale to 720 px wide, 14 fps,
  `palettegen`+`paletteuse` for clean colors, loop forever. ~17 s, ~3 MB.

Re-run after any new recording:

```powershell
python app\scripts\edit_demo.py
```

## Manual screenshot capture

Use Windows Snipping Tool (Win+Shift+S) or the `mss` Python library for
quick stills to drop into slides or README cards.
