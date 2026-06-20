#!/usr/bin/env python3
"""Safety-first quick NFT mint template.

Default = dry run. Real broadcast requires BOTH --execute and --confirm.
Secrets come from env only: PRIVATE_KEY + ALCHEMY_RPC/RPC_ETH/RPC_URL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal

from web3 import Web3


def env(name: str, *fallbacks: str) -> str:
    for key in (name, *fallbacks):
        val = os.environ.get(key)
        if val:
            return val.strip()
    raise SystemExit(f"❌ Missing env: {name}" + (f" (or {', '.join(fallbacks)})" if fallbacks else ""))


def load_abi(raw: str):
    if raw.startswith("file:"):
        with open(raw[5:]) as f:
            return json.load(f)
    return json.loads(raw)


def main():
    ap = argparse.ArgumentParser(description="Safety-first quick NFT mint")
    ap.add_argument("--contract", required=True)
    ap.add_argument("--abi", default='[{"inputs":[],"name":"mint","outputs":[],"stateMutability":"payable","type":"function"}]')
    ap.add_argument("--function", default="mint")
    ap.add_argument("--args", default="[]", help="JSON list of function args")
    ap.add_argument("--value", default="0", help="ETH value")
    ap.add_argument("--gas-price-gwei", type=Decimal, default=None)
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
    sender = acct.address
    contract_addr = Web3.to_checksum_address(args.contract)
    contract = w3.eth.contract(address=contract_addr, abi=load_abi(args.abi))
    fn_args = json.loads(args.args)
    value = w3.to_wei(Decimal(args.value), "ether")

    fn = getattr(contract.functions, args.function)(*fn_args)
    tx = fn.build_transaction({
        "from": sender,
        "value": value,
        "nonce": w3.eth.get_transaction_count(sender, "pending"),
        "chainId": w3.eth.chain_id,
    })

    print(f"Wallet: {sender}")
    print(f"Contract: {contract_addr}")
    print("Simulating...")
    try:
        w3.eth.call({k: tx[k] for k in ("from", "to", "data", "value") if k in tx})
        est = getattr(contract.functions, args.function)(*fn_args).estimate_gas({"from": sender, "value": value})
    except Exception as e:
        raise SystemExit(f"❌ Simulation/estimate reverted — no tx sent: {e}")

    tx["gas"] = int(est * 1.3) + 5000
    if args.gas_price_gwei is not None:
        tx["gasPrice"] = w3.to_wei(args.gas_price_gwei, "gwei")
        fee_per_gas = tx["gasPrice"]
    else:
        block = w3.eth.get_block("pending")
        priority = w3.eth.max_priority_fee
        base = int(block.get("baseFeePerGas", w3.eth.gas_price))
        tx["maxFeePerGas"] = base * 2 + priority
        tx["maxPriorityFeePerGas"] = priority
        fee_per_gas = tx["maxFeePerGas"]

    total_cost_eth = Decimal(str(w3.from_wei(tx["gas"] * int(fee_per_gas) + value, "ether")))
    print(f"Estimate OK: {est} gas → using {tx['gas']}")
    print(f"Max total cost: {total_cost_eth} ETH")
    if args.max_total_eth is not None and total_cost_eth > args.max_total_eth:
        raise SystemExit(f"❌ Cost cap exceeded — no tx sent: {total_cost_eth} > {args.max_total_eth} ETH")

    if not (args.execute and args.confirm):
        print("✅ Dry run complete — no tx sent. Add BOTH --execute --confirm to broadcast.")
        return

    print("Sending transaction...")
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Tx sent: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    print("✅ MINT SUCCESS" if receipt["status"] == 1 else "❌ MINT FAILED")
    print(f"Gas used: {receipt['gasUsed']}")


if __name__ == "__main__":
    main()
