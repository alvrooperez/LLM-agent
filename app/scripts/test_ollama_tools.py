"""Debug: qué devuelve Ollama cuando le paso tools?"""
import json
import urllib.request
import sys

sys.path.insert(0, "C:\\Users\\aborb\\.minimax-agent\\projects\\ai-engineer-portfolio\\phase-2-rag\\scripts")
import tools.implementations  # noqa: F401 — esto registra las tools
from tools.registry import get_tools_schema, get_system_prompt

tools = get_tools_schema()
system_prompt = get_system_prompt()

print(f"Tools count: {len(tools)}")
print(f"Tools: {[t['function']['name'] for t in tools]}")
print()

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Dime el estado de la GPU NVIDIA"},
]

payload = {
    "model": "qwen2.5:3b",
    "messages": messages,
    "tools": tools,
    "stream": False,
    "options": {"temperature": 0.7, "num_predict": 512},
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request("http://localhost:11434/api/chat", data=data, headers={"Content-Type": "application/json"})

print("Sending to Ollama...")
with urllib.request.urlopen(req, timeout=120) as resp:
    result = json.loads(resp.read().decode("utf-8"))

msg = result.get("message", {})
content = msg.get("content", "")
tool_calls = msg.get("tool_calls", [])

print(f"\nModel response:")
print(f"  Content ({len(content)} chars): {content[:400]}")
print(f"  Tool calls: {tool_calls}")
print(f"\nFull JSON keys: {list(result.keys())}")