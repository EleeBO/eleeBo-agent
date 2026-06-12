"""
Send mainnet FET to eleeBo agent and print the tx_hash.
Usage:
  python send_payment.py --key <hex-private-key>
"""
import argparse
import sys

from cosmpy.aerial.client import LedgerClient, NetworkConfig
from cosmpy.aerial.tx import Transaction
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.aerial.client.utils import prepare_and_broadcast_basic_transaction
from cosmpy.protos.cosmos.bank.v1beta1.tx_pb2 import MsgSend
from cosmpy.protos.cosmos.base.v1beta1.coin_pb2 import Coin

# --- Config ---
AGENT_WALLET  = "fetch1xjd27whm9fyyy3w2yv8ey2zlr837adkh7q7hqd"
PRICE_UFET    = "10000000000000000"   # 0.01 FET in afet
DENOM         = "afet"

MAINNET = NetworkConfig(
    chain_id="fetchhub-4",
    url="grpc+https://grpc-fetchhub.fetch.ai",
    fee_minimum_gas_price=5000000000,
    fee_denomination=DENOM,
    staking_denomination=DENOM,
)

FAUCET_URLS = []  # mainnet — no faucet, use real FET


def request_faucet(address: str) -> bool:
    import urllib.request, json
    body = json.dumps({"address": address}).encode()
    for url in FAUCET_URLS:
        try:
            req = urllib.request.Request(url, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                resp = json.loads(r.read())
                if resp.get("status") == "ok":
                    print(f"  Faucet OK ({url})")
                    return True
        except Exception as e:
            print(f"  Faucet {url} failed: {e}")
    return False


def get_balance(ledger: LedgerClient, address: str) -> int:
    try:
        balances = ledger.query_bank_all_balances(address)
        for coin in balances:
            if coin.denom == DENOM:
                return int(coin.amount)
    except Exception:
        pass
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", type=str, default=None,
                        help="Hex private key for existing wallet")
    args = parser.parse_args()

    # --- Wallet ---
    if args.key:
        from cosmpy.crypto.keypairs import PrivateKey
        wallet = LocalWallet(PrivateKey(bytes.fromhex(args.key)))
        print(f"Loaded wallet: {wallet.address()}")
    else:
        wallet = LocalWallet.generate()
        pk_hex = wallet._private_key._private_key_bytes.hex()
        print(f"New wallet generated!")
        print(f"  Address : {wallet.address()}")
        print(f"  Key     : {pk_hex}")
        print(f"  SAVE THIS KEY — use --key {pk_hex} to reload\n")

    address = str(wallet.address())

    # --- Connect ---
    print("Connecting to Fetch.ai mainnet...")
    ledger = LedgerClient(MAINNET)

    # --- Balance check ---
    balance = get_balance(ledger, address)
    print(f"Balance: {balance} atestfet ({balance / 10**18:.6f} FET)")

    if balance < int(PRICE_UFET) + 50_000_000_000_000:   # amount + gas buffer
        print("ERROR: Insufficient balance.")
        print(f"  Send at least 0.011 FET to: {address}")
        print("  Then rerun this script.")
        sys.exit(1)

    # --- Send payment ---
    print(f"\nSending {PRICE_UFET} afet -> {AGENT_WALLET} ...")

    msg = MsgSend(
        from_address=address,
        to_address=AGENT_WALLET,
        amount=[Coin(amount=PRICE_UFET, denom=DENOM)],
    )

    tx = Transaction()
    tx.add_message(msg)

    submitted = prepare_and_broadcast_basic_transaction(ledger, tx, wallet)
    submitted.wait_to_complete()

    tx_hash = submitted.tx_hash
    print(f"\nPayment sent!")
    print(f"  tx_hash : {tx_hash}")
    print(f"\nNow update test_client.py:")
    print(f'  FAKE_TX_HASH = "{tx_hash}"')


if __name__ == "__main__":
    main()
