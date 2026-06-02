import aiohttp
from datetime import datetime
from uuid import uuid4

from uagents import Agent, Context, Model, Protocol
from uagents.setup import fund_agent_if_low
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)


# --- Messages (direct agent-to-agent protocol) ---

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


class ErrorResponse(Model):
    reason: str


# --- Config ---

SEED       = "eleeBo-agent-seed-change-this-to-something-secret"
PRICE_FET  = 0.01
PRICE_UFET = int(PRICE_FET * 10**18)
OLLAMA_URL = "http://localhost:11434/api/generate"
REST_NODE  = "https://rest-fetchhub.fetch.ai"
DENOM      = "afet"
MODEL_FAST = "llama3.1:8b"    # pro kratke dotazy (<80 znaku)
MODEL_FULL = "qwen2.5:14b"    # pro slozite dotazy

SYSTEM_PROMPT = (
    "You are eleeBo, a skilled AI assistant. "
    "For creative tasks (poems, haiku, stories): be imaginative, vivid, and expressive. Use strong imagery and varied language. "
    "For factual questions: be accurate, clear, and concise. "
    "Never add disclaimers, apologies, or explanations about your capabilities. "
    "Never say you cannot do something. Just do it."
)

# Sledovani uzivatelu pro ASI:One onboarding
seen_senders: set[str] = set()

eleeBo = Agent(
    name="eleeBo",
    seed=SEED,
    port=8001,
    mailbox=True,
)

fund_agent_if_low(eleeBo.wallet.address())
WALLET = str(eleeBo.wallet.address())

pending: dict[str, tuple[str, str, str]] = {}
used_tx_hashes: set[str] = set()
total_earned: float = 0.0


# --- Helpers ---

async def verify_payment(tx_hash: str, recipient: str, min_amount: int) -> tuple[bool, str]:
    if tx_hash in used_tx_hashes:
        return False, "tx_hash already used"
    url = f"{REST_NODE}/cosmos/tx/v1beta1/txs/{tx_hash}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status in (400, 404):
                    return False, "tx not found on ledger"
                data = await resp.json()
    except Exception as e:
        return False, f"ledger query failed: {e}"
    try:
        if data.get("tx_response", {}).get("code", -1) != 0:
            return False, "tx failed on-chain"
        for msg in data.get("tx", {}).get("body", {}).get("messages", []):
            if msg.get("@type") != "/cosmos.bank.v1beta1.MsgSend":
                continue
            if msg.get("to_address") != recipient:
                continue
            for coin in msg.get("amount", []):
                if coin.get("denom") == DENOM and int(coin.get("amount", 0)) >= min_amount:
                    return True, "ok"
        return False, "no matching MsgSend found"
    except Exception as e:
        return False, f"tx parse error: {e}"


CREATIVE_KEYWORDS = {"poem", "haiku", "story", "write", "creative", "song", "rhyme", "verse", "limerick"}

def pick_model(prompt: str, requested: str = "") -> str:
    if requested and requested not in ("qwen2.5:14b", "llama3.1:8b", "llava:13b"):
        return MODEL_FULL
    if requested:
        return requested
    # Creative tasks always get the full model
    if any(kw in prompt.lower() for kw in CREATIVE_KEYWORDS):
        return MODEL_FULL
    return MODEL_FAST if len(prompt) < 80 else MODEL_FULL


def is_creative(prompt: str) -> bool:
    return any(kw in prompt.lower() for kw in CREATIVE_KEYWORDS)


async def call_ollama(prompt: str, model: str = "") -> str:
    chosen = pick_model(prompt, model)
    creative = is_creative(prompt)

    # For creative tasks: higher temperature = more imaginative output
    options = {"temperature": 0.85, "top_p": 0.95} if creative else {"temperature": 0.3}

    # Wrap creative prompts to encourage quality
    final_prompt = (
        f"Write an exceptional, vivid, and original response to: {prompt}\n"
        f"Be creative, use strong imagery, and avoid clichés."
        if creative else prompt
    )

    payload = {
        "model": chosen,
        "system": SYSTEM_PROMPT,
        "prompt": final_prompt,
        "stream": False,
        "options": options,
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(OLLAMA_URL, json=payload,
                          timeout=aiohttp.ClientTimeout(total=120)) as resp:
            data = await resp.json()
            return data.get("response", "").strip(), chosen


# --- Startup ---

@eleeBo.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("eleeBo AI Service started (mainnet)")
    ctx.logger.info(f"Agent  : {eleeBo.address}")
    ctx.logger.info(f"Wallet : {WALLET}")
    ctx.logger.info(f"Price  : {PRICE_FET} FET / request (direct protocol)")
    ctx.logger.info("ASI:One chat protocol: active (free)")


# --- Direct payment protocol ---

@eleeBo.on_message(model=AIRequest)
async def handle_request(ctx: Context, sender: str, msg: AIRequest):
    request_id = str(uuid4())[:8]
    pending[request_id] = (sender, msg.prompt, msg.model)
    ctx.logger.info(f"[{request_id}] AIRequest from {sender[:20]}...")
    await ctx.send(sender, PaymentRequest(
        wallet=WALLET,
        amount_afet=PRICE_UFET,
        amount_fet=PRICE_FET,
        request_id=request_id,
    ))


@eleeBo.on_message(model=PaymentConfirm)
async def handle_payment_confirm(ctx: Context, sender: str, msg: PaymentConfirm):
    global total_earned
    request_id = msg.request_id
    tx_hash = msg.tx_hash.strip()

    if request_id not in pending:
        await ctx.send(sender, ErrorResponse(reason="Unknown request_id"))
        return

    ctx.logger.info(f"[{request_id}] Verifying tx {tx_hash[:16]}...")
    ok, reason = await verify_payment(tx_hash, WALLET, PRICE_UFET)

    if not ok:
        ctx.logger.warning(f"[{request_id}] Rejected: {reason}")
        await ctx.send(sender, ErrorResponse(reason=f"Payment invalid: {reason}"))
        return

    used_tx_hashes.add(tx_hash)
    original_sender, prompt, model = pending.pop(request_id)
    ctx.logger.info(f"[{request_id}] Payment verified ✓ — calling Ollama")

    try:
        result, chosen = await call_ollama(prompt, model)
        total_earned += PRICE_FET
        ctx.logger.info(f"[{request_id}] Done ({chosen}). Earned: {total_earned:.4f} FET total")
        await ctx.send(original_sender, AIResponse(request_id=request_id, result=result))
    except Exception as e:
        ctx.logger.error(f"[{request_id}] Ollama error: {e}")
        await ctx.send(original_sender, ErrorResponse(reason=str(e)))


# --- ASI:One Chat Protocol ---

chat_protocol = Protocol(spec=chat_protocol_spec)


@chat_protocol.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    # Acknowledge immediately
    await ctx.send(sender, ChatAcknowledgement(
        timestamp=datetime.now(),
        acknowledged_msg_id=msg.msg_id,
    ))

    # Extract text from message
    text = " ".join(
        item.text for item in msg.content
        if isinstance(item, TextContent)
    ).strip()

    if not text:
        reply = "Please send a text message."
    else:
        ctx.logger.info(f"[ASI:One] Chat from {sender[:20]}...: {text[:60]}")
        try:
            result, chosen = await call_ollama(text)
            ctx.logger.info(f"[ASI:One] Responded via {chosen} ({len(result)} chars)")

            # Onboarding pro noveho uzivatele
            if sender not in seen_senders:
                seen_senders.add(sender)
                result += (
                    "\n\n---\n*Powered by eleeBo AI. "
                    "For direct agent integration with verified FET payments, "
                    f"use agent address: {eleeBo.address}*"
                )
            reply = result
        except Exception as e:
            reply = f"Error processing request: {e}"

    await ctx.send(sender, ChatMessage(
        timestamp=datetime.now(),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=reply),
            EndSessionContent(type="end-session"),
        ],
    ))


@chat_protocol.on_message(ChatAcknowledgement)
async def handle_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


eleeBo.include(chat_protocol, publish_manifest=True)


# --- Status ---

@eleeBo.on_interval(period=60.0)
async def status(ctx: Context):
    ctx.logger.info(f"Alive | pending={len(pending)} | earned={total_earned:.4f} FET")


if __name__ == "__main__":
    eleeBo.run()
