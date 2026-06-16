# eleeBo — Pay-Per-Use AI Agent on Fetch.ai Mainnet

eleeBo is an autonomous AI service agent running on the Fetch.ai mainnet. It serves AI-generated responses via local Ollama models and accepts **verified on-chain FET payments** per request.

Built as a reference implementation for pay-per-use AI agents in the ASI ecosystem.

---

## How it works

```
Client                          eleeBo Agent                    Blockchain
  │                                  │                              │
  ├─── AIRequest (prompt) ──────────>│                              │
  │<── PaymentRequest (0.01 FET) ────┤                              │
  │                                  │                              │
  ├─── send 0.01 FET on-chain ───────┼─────────────────────────────>│
  ├─── PaymentConfirm (tx_hash) ────>│                              │
  │                                  ├── verify tx on-chain ───────>│
  │                                  │<─ confirmed ─────────────────┤
  │                                  ├── call Ollama                │
  │<── AIResponse (result) ──────────┤                              │
```

---

## Two access modes

| Mode | Cost | How |
|---|---|---|
| **ASI:One chat** | Free | Chat directly at [asi1.ai](https://asi1.ai) |
| **Agent-to-agent** | 0.01 FET/request | Direct protocol (see below) |

---

## Integration (agent-to-agent)

```python
from uagents import Agent, Context, Model

class AIRequest(Model):
    prompt: str
    model: str = "qwen2.5:14b"

class PaymentRequest(Model):
    wallet: str
    amount_afet: int
    amount_fet: float
    request_id: str

class PaymentConfirm(Model):
    request_id: str
    tx_hash: str

class AIResponse(Model):
    request_id: str
    result: str

eleeBo = "agent1qtyl39w7mepqkddkvm4xdez20gp6z4kf2gtxrdxewr72kdyvdgy4zr9mlqn"

# 1. Send request
await ctx.send(eleeBo, AIRequest(prompt="Your question here"))

# 2. On PaymentRequest: send 0.01 FET on-chain, get tx_hash
# 3. Confirm payment
await ctx.send(eleeBo, PaymentConfirm(request_id=req_id, tx_hash=tx_hash))

# 4. Receive AIResponse with result
```

---

## Run your own instance

```bash
git clone https://github.com/YOUR_USERNAME/eleeBo-agent
cd eleeBo-agent
python -m venv .venv && source .venv/bin/activate
pip install uagents cosmpy aiohttp
python agent.py
```

Requires [Ollama](https://ollama.ai) running locally with at least one model pulled.

---
