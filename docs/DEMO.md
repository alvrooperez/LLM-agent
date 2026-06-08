# Demo assets

GIFs and screenshots for the README.

## Generating the demo GIF

1. Start the chat app: `python -m uvicorn scripts.chat_app:app --port 8090`
2. Open Chrome at http://localhost:8090
3. Maximize the window
4. In another terminal: `python ../app/make_demo_gif.py --duration 30 --fps 10`
5. Interact with the chat during the 30s:
   - Type "¿Cuántos puntos hay en la colección de Qdrant?" (shows `get_collection_info` tool)
   - Type "Genera un PDF de tipo project_report con título Demo" (shows `write_document` tool)
   - Type "Lista los modelos" (shows `list_models` tool)
   - Press Ctrl+M to open compare mode, type "¿Cuál es tu color favorito?" (shows side-by-side comparison)
6. The GIF is saved to `docs/demo.gif`

## Manual screenshot capture

Use Windows Snipping Tool (Win+Shift+S) or `mss` library for quick captures.
