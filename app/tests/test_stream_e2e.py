import urllib.request, json, time

# Mensaje simple sin tools para ver streaming puro
data = json.dumps({
    'message': 'Saluda en 3 lineas distintas',
    'model': 'qwen2.5-rag-ft',
}).encode()
req = urllib.request.Request(
    'http://localhost:8090/api/chat/stream',
    data=data,
    headers={'Content-Type': 'application/json', 'User-Agent': 'stream-test/1.0'},
    method='POST',
)

t0 = time.time()
tokens = []
tool_calls_seen = []
with urllib.request.urlopen(req, timeout=120) as r:
    print(f"Status: {r.status}, Content-Type: {r.headers.get('Content-Type')}")
    buf = b''
    last_token_time = t0
    while True:
        chunk = r.read(1)
        if not chunk:
            break
        buf += chunk
        # Procesar cuando tengamos \n\n
        if buf.endswith(b'\n\n'):
            block = buf.decode('utf-8', errors='replace')
            buf = b''
            # Parsear SSE
            event = None
            data_str = ''
            for line in block.strip().split('\n'):
                if line.startswith('event: '):
                    event = line[7:].strip()
                elif line.startswith('data: '):
                    data_str = line[6:]
            if event == 'token' and data_str:
                payload = json.loads(data_str)
                tokens.append(payload['text'])
                if len(tokens) == 1 or len(tokens) % 5 == 0:
                    elapsed = time.time() - t0
                    print(f"  [{len(tokens):3d} tokens, {elapsed:.1f}s] last: {payload['text']!r}")
            elif event == 'tool_call':
                payload = json.loads(data_str)
                tool_calls_seen.append(payload['name'])
            elif event == 'done':
                payload = json.loads(data_str)
                print(f"\nDone: {payload['iterations']} iter, {payload['elapsed_sec']}s server")
            elif event == 'error':
                payload = json.loads(data_str)
                print(f"\nERROR: {payload}")

total = time.time() - t0
print(f"\nTotal: {len(tokens)} tokens, {total:.1f}s")
print(f"Tool calls: {tool_calls_seen}")
print(f"Full response: {''.join(tokens)}")
