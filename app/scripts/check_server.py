"""
check_server.py — Verifica si el server en :8090 está respondiendo.
No usa Invoke-WebRequest. Solo Python urllib con timeout duro.

Uso:
  python scripts/check_server.py
  echo $LASTEXITCODE  # 0=up, 1=down, 2=down+timeout
"""
import sys
import urllib.request
import urllib.error

PORT = 8090
URL = f"http://localhost:{PORT}/api/health"
HEADERS = {"User-Agent": "check_server/1.0"}


def main() -> int:
    try:
        req = urllib.request.Request(URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.0) as r:
            body = r.read().decode("utf-8", errors="replace")
            if r.status == 200:
                print(f"UP: {body}")
                return 0
            else:
                print(f"DOWN: HTTP {r.status}")
                return 1
    except urllib.error.HTTPError as e:
        print(f"DOWN: HTTP {e.code}: {e.read().decode()[:100]}")
        return 1
    except urllib.error.URLError as e:
        print(f"DOWN: URLError: {e.reason}")
        return 1
    except TimeoutError:
        print("DOWN: timed out after 3s (server bound but not responding)")
        return 2
    except Exception as e:
        print(f"DOWN: {type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
