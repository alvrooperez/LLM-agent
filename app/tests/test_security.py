"""Test end-to-end de seguridad + agente."""
import urllib.request, urllib.error, json, time

BASE = "http://localhost:8090"

def call(path, headers=None, method="GET", data=None, timeout=10):
    h = {"User-Agent": "sec-test/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:300]


# T1
print("[T1] Health sin auth")
s, b = call("/api/health")
print(f"  {s}: {b[:80]}")

# T2
print("[T2] Models sin auth (modo open)")
s, b = call("/api/models")
print(f"  {s}: {b[:80]}")

# T3
print("[T3] Scanner (sqlmap)")
s, b = call("/api/models", headers={"User-Agent": "sqlmap/1.5"})
print(f"  {s}: {b[:80]}  (esperado 403)")

# T4
print("[T4] Path traversal")
s, b = call("/api/docs/..%2Fpasswd")
print(f"  {s}: {b[:80]}  (esperado 400)")

# T5
print("[T5] Chat con mensaje simple (modo open)")
body = json.dumps({"message": "Hola, dame el estado de la GPU", "model": "qwen2.5-rag-ft"}).encode()
t0 = time.time()
s, b = call("/api/chat", method="POST", data=body, headers={"Content-Type": "application/json"}, timeout=120)
elapsed = time.time() - t0
print(f"  {s} in {elapsed:.1f}s: {b[:150]}")

# T6
print("[T6] Chat mensaje gigante (debe rechazar)")
body = json.dumps({"message": "x" * 3000, "model": "qwen2.5-rag-ft"}).encode()
s, b = call("/api/chat", method="POST", data=body, headers={"Content-Type": "application/json"})
print(f"  {s}: {b[:80]}  (esperado 422)")

print("\nDone")
