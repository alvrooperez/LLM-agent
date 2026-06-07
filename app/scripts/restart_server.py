"""
restart_server.py — Mata el server viejo en :8090 y arranca uno nuevo de forma fiable.
No usa Invoke-WebRequest (que se cuelga en Windows PowerShell 5.1).
Usa subprocess.run con timeout duro en Python.

Uso:
  python scripts/restart_server.py
"""
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

PORT = 8090
SCRIPTS_DIR = Path(__file__).parent
WORKDIR = SCRIPTS_DIR.parent
LOG_OUT = Path(r"C:\Users\aborb\.mavis\logs\chat_app.out")
LOG_ERR = Path(r"C:\Users\aborb\.mavis\logs\chat_app.err")
EXE = "python"

# Ensure log dir
LOG_OUT.parent.mkdir(parents=True, exist_ok=True)


def get_listener_pid() -> int | None:
    """Devuelve el PID que escucha en PORT, o None."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {PORT} -ErrorAction SilentlyContinue | "
             f"Where-Object State -eq Listen | Select-Object -ExpandProperty OwningProcess"],
            capture_output=True, text=True, timeout=5
        )
        out = r.stdout.strip()
        if out and out.isdigit():
            return int(out)
    except Exception as e:
        print(f"get_listener_pid: {e}", file=sys.stderr)
    return None


def kill_pid(pid: int) -> bool:
    """Mata un PID. Devuelve True si se mató."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() == ""
    except Exception as e:
        print(f"kill_pid: {e}", file=sys.stderr)
        return False


def start_server() -> int:
    """Arranca el server detached. Importante: redirigir IO y detach del parent
    para que el script termine aunque el server siga vivo."""
    fout = open(LOG_OUT, "a", encoding="utf-8")
    ferr = open(LOG_ERR, "a", encoding="utf-8")
    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    proc = subprocess.Popen(
        [EXE, "-m", "uvicorn", "scripts.chat_app:app", "--host", "0.0.0.0", "--port", str(PORT)],
        cwd=str(WORKDIR),
        stdout=fout,
        stderr=ferr,
        stdin=subprocess.DEVNULL,
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )
    # No esperamos a proc — fire and forget
    return proc.pid


def check_health(timeout: float = 3.0) -> tuple[bool, str]:
    """Health check con urllib. Devuelve (ok, body)."""
    try:
        req = urllib.request.Request(
            f"http://localhost:{PORT}/api/health",
            headers={"User-Agent": "restart_check/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200, r.read().decode()
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    print("=" * 60)
    print(f"RESTART — :{PORT} (workdir: {WORKDIR})")
    print("=" * 60)

    # 1. Matar el viejo
    old_pid = get_listener_pid()
    if old_pid:
        print(f"[1/3] Killing old process PID {old_pid}...")
        if kill_pid(old_pid):
            print(f"  -> killed")
        else:
            print(f"  -> could not kill (may be gone already)")
    else:
        print(f"[1/3] No process listening on :{PORT}")

    time.sleep(2)

    # 2. Arrancar el nuevo
    print(f"[2/3] Starting new server...")
    new_pid = start_server()
    print(f"  -> PID {new_pid}, logs: {LOG_OUT.name} / {LOG_ERR.name}")

    # 3. Esperar y verificar
    print(f"[3/3] Waiting for server to be ready (max 10s)...")
    for attempt in range(10):
        time.sleep(1)
        ok, body = check_health(timeout=2.0)
        if ok:
            print(f"  -> READY after {attempt+1}s")
            print(f"  -> Health: {body}")
            return 0

    print(f"  -> TIMEOUT after 10s")
    # Show logs for debugging
    print("\nLast 10 lines of stderr:")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Get-Content '{LOG_ERR}' -Tail 10"],
            capture_output=True, text=True, timeout=5
        )
        print(r.stdout)
    except Exception:
        pass
    return 1


if __name__ == "__main__":
    sys.exit(main())
