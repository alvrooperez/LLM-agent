import os
import shutil
from pathlib import Path

SRC = Path(r"C:\Users\aborb\.minimax-agent\projects\ai-engineer-portfolio\phase-2-rag")
DST = Path(r"C:\Users\aborb\.minimax-agent\projects\ai-engineer-portfolio\app")

EXCLUDE = {'.venv', '.venv-train', '.pytest_cache', 'unsloth_compiled_cache', '__pycache__'}

count = 0
for src_dir, dirs, files in os.walk(SRC):
    # Filtrar dirs in-place
    dirs[:] = [d for d in dirs if d not in EXCLUDE]

    rel = Path(src_dir).relative_to(SRC)
    dst_dir = DST / rel
    dst_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        src_file = Path(src_dir) / f
        dst_file = dst_dir / f
        if not dst_file.exists() or src_file.stat().st_mtime > dst_file.stat().st_mtime:
            shutil.copy2(src_file, dst_file)
            count += 1
            if count % 50 == 0:
                print(f"  Copied {count} files...")

print(f"Done: {count} files copied")
