#!/usr/bin/env python3
"""Safety-first auto-mint hammer.

Polls a contract until a mint call simulates successfully. Default behavior is
DRY RUN: it stops and prints the prepared tx. Real broadcast requires BOTH
--execute and --confirm, plus max attempts/cost controls.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

from web3 import Web3

HALT_FILE = Path(os.environ.get("HERMES_HALT", os.environ.get("HERMES_KILLSWITCH", "~/.hermes/HALT"))).expanduser()


def env(name: str, *fallbacks: str) -> str:
    for key in (name, *fallbacks):
        val = os.environ.get(key)
        if val:
            return val.strip()
    raise SystemExit(f"❌ Missing env: {name}" + (f" (or {', '.join(fallbacks)})" if fallbacks else ""))


def build_candidates(wallet: str, quantity: int, value_wei: int):
    q = quantity.to_bytes(32, "big").hex()
    return [
        {"name": "publicMint(address,uint256)", "data": "0xce6df2b9" + wallet[2:].zfill(64) + q, "value": value_wei},
        {"name": "mintPublic(uint256)", "data": "0xefd0cbf9" + q, "value": value_wei},
        {"name": "mint(uint256)", "data": "0xa0712d68" + q, "value": value_wei},
        {"name": "mint()", "data": "0x1249c58b", "value": value_wei},
    ]


def main():
    ap = argparse.ArgumentParser(description="Safety-first auto mint hammer")
    ap.add_argument("--contract", required=True)
    ap.add_argument("--quantity", type=int, default=1)
    ap.add_argument("--value", default="0")
    ap.add_argument("--poll-seconds", type=float, default=3.0)
    ap.add_argument("--max-attempts", type=int, default=60)
    ap.add_argument("--max-total-eth", type=Decimal, default=None)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()

    rpc = env("ALCHEMY_RPC", "RPC_ETH", "RPC_URL")
    pk = env("PRIVATE_KEY")
    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        raise SystemExit("❌ RPC not connected")
    acct = w3.eth.account.from_key(pk)
    wallet = acct.address
    addr = Web3.to_checksum_address(args.contract)
    value_wei = w3.to_wei(Decimal(str(args.value)), "ether")
    chain_id = w3.eth.chain_id

    print(f"Wallet {wallet[:10]}.. | Chain {chain_id}")
    print(f"Polling every {args.poll_seconds}s, max_attempts={args.max_attempts}")
    if not (args.execute and args.confirm):
        print("🧪 DRY RUN ONLY — will not send. Add BOTH --execute --confirm to broadcast.")

    candidates = build_candidates(wallet, args.quantity, value_wei)
    for attempt in range(1, args.max_attempts + 1):
        if HALT_FILE.exists():
            raise SystemExit(f"🛑 HALT file present: {HALT_FILE}")
        nonce = w3.eth.get_transaction_count(wallet, "pending")
        gas_price = w3.eth.gas_price
        for fn in candidates:
            try:
                call = {"from": wallet, "to": addr, "data": fn["data"], "value": fn["value"]}
                w3.eth.call(call)
                gas_est = w3.eth.estimate_gas(call)
                tx = {
                    "from": wallet, "to": addr, "data": fn["data"], "value": fn["value"],
                    "nonce": nonce, "gas": int(gas_est * 1.3), "gasPrice": gas_price,
                    "chainId": chain_id,
                }
                total_cost = Decimal(str(w3.from_wei(tx["gas"] * tx["gasPrice"] + tx["value"], "ether")))
                print(f"✅ OPEN via {fn['name']} | gas={gas_est} | max_cost={total_cost} ETH")
                if args.max_total_eth is not None and total_cost > args.max_total_eth:
                    raise SystemExit(f"❌ Cost cap exceeded — no tx sent: {total_cost} > {args.max_total_eth} ETH")
                if not (args.execute and args.confirm):
                    print("✅ Dry run stopped before broadcast.")
                    return
                signed = w3.eth.account.sign_transaction(tx, pk)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                print(f"TX sent: {tx_hash.hex()}")
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if receipt["status"] == 1:
                    cost = receipt["gasUsed"] * tx["gasPrice"]
                    print(f"✅ SUKSES! {args.quantity} NFT minted | Gas {receipt['gasUsed']} | Cost {w3.from_wei(cost, 'ether'):.6f} ETH")
                else:
                    print("❌ TX failed")
                return
            except SystemExit:
                raise
            except Exception:
                continue
        time.sleep(args.poll_seconds)
    raise SystemExit("❌ Max attempts reached — no tx sent")


if __name__ == "__main__":
    main()
