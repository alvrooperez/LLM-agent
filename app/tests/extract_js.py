import urllib.request, re
req = urllib.request.Request('http://localhost:8090/', headers={'User-Agent': 'test/1.0'})
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        html = r.read().decode()
except Exception as e:
    print(f"Server down: {e}")
    exit(1)
m = re.search(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
js = m.group(1)
out = 'C:/Users/aborb/.mavis/logs/extracted_compare.js'
with open(out, 'w', encoding='utf-8') as f:
    f.write(js)
print(f"Written: {out} ({len(js)} chars)")
