"""
Test client — simulates the full payment flow.
In production: replace FAKE_TX_HASH with a real on-chain tx hash after sending FET.

How to send real FET (CLI):
  fetchd tx bank send <your-key> fetch1xjd27whm9fyyy3w2yv8ey2zlr837adkh7q7hqd \
    10000000000000000atestfet --chain-id dorado-1 --node https://rpc-dorado.fetch.ai:443

Then paste the returned tx hash into FAKE_TX_HASH below.
"""
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


class ErrorResponse(Model):
    reason: str


eleeBo_ADDRESS = "agent1qtyl39w7mepqkddkvm4xdez20gp6z4kf2gtxrdxewr72kdyvdgy4zr9mlqn"

# Replace with a real tx hash after sending FET on-chain
FAKE_TX_HASH = "64D89EC2E1B438F19E81F69E12C6B2CD02240A7BC10C79D933AF432D61857ADC"

client = Agent(
    name="test-client",
    seed="test-client-seed-001",
    port=8002,
    endpoint=["http://localhost:8002/submit"],
)


@client.on_event("startup")
async def send_task(ctx: Context):
    ctx.logger.info("Sending AI request to eleeBo...")
    await ctx.send(eleeBo_ADDRESS, AIRequest(
        prompt="Explain blockchain in 2 sentences.",
        model="qwen2.5:14b",
    ))


@client.on_message(model=PaymentRequest)
async def handle_payment_request(ctx: Context, sender: str, msg: PaymentRequest):
    ctx.logger.info(f"Payment required: {msg.amount_fet} FET -> {msg.wallet}")
    ctx.logger.info(f"Request ID: {msg.request_id}")
    ctx.logger.info("Send FET on-chain, then update FAKE_TX_HASH and rerun.")
    ctx.logger.info(f"Submitting tx_hash: {FAKE_TX_HASH}")

    await ctx.send(sender, PaymentConfirm(
        request_id=msg.request_id,
        tx_hash=FAKE_TX_HASH,
    ))


@client.on_message(model=AIResponse)
async def handle_result(ctx: Context, sender: str, msg: AIResponse):
    ctx.logger.info(f"Result [{msg.request_id}]: {msg.result}")


@client.on_message(model=ErrorResponse)
async def handle_error(ctx: Context, sender: str, msg: ErrorResponse):
    ctx.logger.error(f"Error: {msg.reason}")


if __name__ == "__main__":
    client.run()
