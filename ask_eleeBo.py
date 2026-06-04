"""
Rychly dotaz na eleeBo (lokalni Ollama).
Pouziti: python ask_eleeBo.py "co je kvantova fyzika?"
"""
import sys
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:14b"
SYSTEM = (
    "You are eleeBo, a skilled AI assistant. "
    "Answer directly and concisely. Never add disclaimers."
)

prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Dotaz: ")

resp = requests.post(OLLAMA_URL, json={
    "model": MODEL,
    "system": SYSTEM,
    "prompt": prompt,
    "stream": False,
    "options": {"temperature": 0.7},
}, timeout=120)

print("\neleeBo:", resp.json().get("response", "").strip())
