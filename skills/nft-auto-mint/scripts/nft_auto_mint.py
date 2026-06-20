#!/usr/bin/env python3
"""
NFT Auto Mint — safety-first web3.py minter.

Default behavior is DRY RUN. A real transaction is only broadcast when BOTH
--execute and --confirm are provided. Never run this with a wallet you cannot
afford to risk.

Examples:
  python3 nft_auto_mint.py single --contract 0x... --abi file:abi.json --value 0
  python3 nft_auto_mint.py single --contract 0x... --abi file:abi.json --value 0 --execute --confirm
  python3 nft_auto_mint.py mass --contract 0x... --abi file:abi.json --count 3 --execute --confirm --max-total-eth 0.01
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from decimal import Decimal
from typing import Any, Optional

from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt

GAS_MULTIPLIER = 1.2
CONFIRMATION_WAIT = 15
CONFIRMATION_TIMEOUT = 120


def _load_env() -> tuple[str, str]:
    pk = os.environ.get("PRIVATE_KEY")
    rpc = os.environ.get("ALCHEMY_RPC") or os.environ.get("RPC_ETH") or os.environ.get("RPC_URL")
    if not pk or not rpc:
        print("❌ ERROR: PRIVATE_KEY and ALCHEMY_RPC/RPC_ETH/RPC_URL must be set.", file=sys.stderr)
        print("   export PRIVATE_KEY=0x...", file=sys.stderr)
        print("   export ALCHEMY_RPC=https://eth-mainnet.g.alchemy.com/v2/...", file=sys.stderr)
        sys.exit(1)
    return pk.strip(), rpc.strip()


def _load_abi(raw: str) -> list[dict]:
    if raw.startswith("file:"):
        path = raw[5:]
        if not os.path.isfile(path):
            print(f"❌ ABI file not found: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            return json.load(f)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("❌ ABI is not valid JSON. Use inline JSON or 'file:/path/to/abi.json'.", file=sys.stderr)
        sys.exit(1)


def _find_mint_fn(abi: list[dict]) -> Optional[dict]:
    candidates = {
        "mint", "publicmint", "safemint", "claim", "mintnft", "minttoken",
        "purchase", "buy", "mintdino", "mintegg", "mintpublic"
    }
    for entry in abi:
        if entry.get("type") != "function":
            continue
        name = entry.get("name", "").lower()
        if name in candidates and entry.get("stateMutability") in ("payable", "nonpayable"):
            return entry
    return None


def _wei(val_eth: str | float | Decimal) -> int:
    return Web3.to_wei(Decimal(str(val_eth)), "ether")


def _coerce_arg(sol_type: str, name: str, raw: Any, account_addr: str, to_addr: str, quantity: int) -> Any:
    if raw is None:
        lname = name.lower()
        if sol_type == "address":
            if lname in ("to", "receiver", "recipient", "minter", "account", "owner", "_to", "_receiver"):
                return Web3.to_checksum_address(to_addr)
            return Web3.to_checksum_address(account_addr)
        if sol_type.startswith("uint") or sol_type.startswith("int"):
            return quantity
        if sol_type == "bool":
            return False
        if sol_type == "bytes":
            return b""
        if sol_type == "string":
            return ""
        if sol_type.endswith("[]"):
            return []
        raise ValueError(f"No default arg for Solidity type {sol_type!r}; pass --mint-args JSON")
    if sol_type == "address":
        return Web3.to_checksum_address(str(raw))
    if sol_type.startswith("uint") or sol_type.startswith("int"):
        return int(raw)
    if sol_type == "bool":
        return bool(raw)
    if sol_type == "bytes":
        if isinstance(raw, bytes):
            return raw
        if isinstance(raw, str) and raw.startswith("0x"):
            return bytes.fromhex(raw[2:])
        return str(raw).encode()
    return raw


def _build_mint_args(mint_fn: dict, account_addr: str, to_addr: str, quantity: int, raw_args: Optional[str]) -> list[Any]:
    """Build arguments for common mint/claim functions, with --mint-args override."""
    inputs = mint_fn.get("inputs", []) or []
    if not inputs:
        return []
    supplied = None
    if raw_args:
        try:
            supplied = json.loads(raw_args)
        except json.JSONDecodeError as e:
            raise ValueError(f"--mint-args must be JSON: {e}")
        if not isinstance(supplied, (list, dict)):
            raise ValueError("--mint-args must be a JSON list or object")

    args = []
    for idx, item in enumerate(inputs):
        name = item.get("name", f"arg{idx}") or f"arg{idx}"
        sol_type = item.get("type", "")
        raw = None
        if isinstance(supplied, list) and idx < len(supplied):
            raw = supplied[idx]
        elif isinstance(supplied, dict) and name in supplied:
            raw = supplied[name]
        args.append(_coerce_arg(sol_type, name, raw, account_addr, to_addr, quantity))
    return args


def _format_receipt(receipt: TxReceipt) -> str:
    status = "✅ Success" if receipt.get("status") == 1 else "❌ Failed"
    gas_used = receipt.get("gasUsed", 0)
    effective_gas = receipt.get("effectiveGasPrice", 0)
    fee_eth = Web3.from_wei(gas_used * effective_gas, "ether")
    return (
        f"  Tx Hash:    {receipt['transactionHash'].hex()}\n"
        f"  Block #:    {receipt.get('blockNumber', 'N/A')}\n"
        f"  Status:     {status}\n"
        f"  Gas Used:   {gas_used:,}\n"
        f"  Gas Price:  {Web3.from_wei(effective_gas, 'gwei'):.2f} gwei\n"
        f"  Fee:        {fee_eth:.6f} ETH\n"
        f"  Logs:       {len(receipt.get('logs', []))}"
    )


def _wait_for_receipt(w3: Web3, tx_hash: str, timeout: int = CONFIRMATION_TIMEOUT) -> TxReceipt:
    print("⏳ Waiting for tx to be mined...")
    elapsed = 0
    while elapsed < timeout:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt and receipt.get("blockNumber") is not None:
                return receipt
        except TransactionNotFound:
            pass
        time.sleep(CONFIRMATION_WAIT)
        elapsed += CONFIRMATION_WAIT
    raise TimeoutError(f"Tx {tx_hash} not confirmed within {timeout}s")


def _build_tx(
    w3: Web3,
    account: Any,
    contract: Any,
    mint_fn: dict,
    value_wei: int,
    to_addr: str,
    quantity: int,
    mint_args_json: Optional[str],
    gas_multiplier: float,
    priority_fee_gwei: Optional[float] = None,
) -> tuple[dict, list[Any]]:
    mint_fn_name = mint_fn["name"]
    args = _build_mint_args(mint_fn, account.address, to_addr, quantity, mint_args_json)
    fn = getattr(contract.functions, mint_fn_name)(*args)
    tx = fn.build_transaction({
        "from": account.address,
        "value": value_wei,
        "nonce": w3.eth.get_transaction_count(account.address, "pending"),
        "chainId": w3.eth.chain_id,
    })
    try:
        w3.eth.call({k: tx[k] for k in ("from", "to", "data", "value") if k in tx})
        est = w3.eth.estimate_gas(tx)
    except Exception as e:
        raise RuntimeError(f"Simulation/estimate failed; refusing to broadcast: {e}")
    tx["gas"] = int(est * gas_multiplier)
    block = w3.eth.get_block("pending")
    base_fee = block.get("baseFeePerGas") if hasattr(block, "get") else None
    priority = Web3.to_wei(priority_fee_gwei, "gwei") if priority_fee_gwei is not None else w3.eth.max_priority_fee
    if base_fee is not None:
        tx["maxFeePerGas"] = int(base_fee) * 2 + int(priority)
        tx["maxPriorityFeePerGas"] = int(priority)
    else:
        tx["gasPrice"] = w3.eth.gas_price
    print(f"  ⛽ Estimated gas: {est:,} → buffered: {tx['gas']:,}")
    return tx, args


def _summarize_tx(w3: Web3, tx: dict, value_wei: int) -> dict:
    gas_price = tx.get("maxFeePerGas") or tx.get("gasPrice") or 0
    max_cost = tx["gas"] * int(gas_price) + value_wei
    return {
        "dry_run": True,
        "from": tx.get("from"),
        "to": tx.get("to"),
        "value_eth": Web3.from_wei(value_wei, "ether"),
        "estimated_gas": tx["gas"],
        "max_fee_gwei": Web3.from_wei(int(gas_price), "gwei") if gas_price else 0,
        "total_max_cost_eth": Web3.from_wei(max_cost, "ether"),
        "nonce": tx.get("nonce"),
    }


def _send(w3: Web3, account: Any, tx: dict) -> TxReceipt:
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hash_hex = tx_hash.hex()
    print(f"  📤 Tx sent: {tx_hash_hex}")
    return _wait_for_receipt(w3, tx_hash_hex)


def _check_balance(w3: Web3, account: Any, needed_wei: int) -> bool:
    balance = w3.eth.get_balance(account.address)
    if balance < needed_wei:
        needed_eth = Web3.from_wei(needed_wei, "ether")
        bal_eth = Web3.from_wei(balance, "ether")
        print(f"  ❌ Insufficient balance: {bal_eth:.6f} ETH available, {needed_eth:.6f} ETH needed", file=sys.stderr)
        return False
    return True


def _assert_execute_allowed(args):
    if not (args.execute and args.confirm):
        print("🧪 DRY RUN ONLY — no tx sent. Add BOTH --execute --confirm to broadcast.")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="NFT Auto Mint — safety-first web3.py minter")
    sub = parser.add_subparsers(dest="mode", required=True)

    def common(p):
        p.add_argument("--contract", required=True)
        p.add_argument("--abi", required=True)
        p.add_argument("--value", type=str, default="0")
        p.add_argument("--to", default=None)
        p.add_argument("--quantity", type=int, default=1)
        p.add_argument("--mint-args", default=None, help="JSON list/object for mint function args")
        p.add_argument("--execute", action="store_true", help="Allow real broadcast")
        p.add_argument("--confirm", action="store_true", help="Second explicit confirmation for broadcast")
        p.add_argument("--dry-run", action="store_true", help="Kept for compatibility; dry run is default")
        p.add_argument("--gas-multiplier", type=float, default=GAS_MULTIPLIER)
        p.add_argument("--priority-fee", type=float, default=None)
        p.add_argument("--max-total-eth", type=str, default=None, help="Maximum total cost allowed per tx")

    p_single = sub.add_parser("single", help="Single mint")
    common(p_single)

    p_mass = sub.add_parser("mass", help="Mass mint repeated N times")
    common(p_mass)
    p_mass.add_argument("--count", type=int, default=5)

    args = parser.parse_args()
    pk, rpc = _load_env()
    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        print("❌ Cannot connect to RPC. Check RPC env.", file=sys.stderr)
        sys.exit(1)

    account = w3.eth.account.from_key(pk)
    to_addr = Web3.to_checksum_address(args.to or account.address)
    abi = _load_abi(args.abi)
    mint_fn = _find_mint_fn(abi)
    if not mint_fn:
        print("❌ No recognized mint/claim function found in ABI.", file=sys.stderr)
        sys.exit(1)

    value_wei = _wei(args.value)
    contract = w3.eth.contract(address=Web3.to_checksum_address(args.contract), abi=abi)
    count = args.count if args.mode == "mass" else 1

    print(f"\n{'='*55}")
    print(f"  🖼  NFT Auto Mint — {args.mode.upper()}")
    print(f"{'='*55}")
    print(f"  Chain ID:        {w3.eth.chain_id}")
    print(f"  Wallet:          {account.address}")
    print(f"  Contract:        {args.contract}")
    print(f"  Mint Function:   {mint_fn['name']}({', '.join(i.get('type','') for i in mint_fn.get('inputs', []))})")
    print(f"  Mint Value:      {args.value} ETH")
    print(f"  Recipient:       {to_addr}")
    print(f"  Count:           {count}")
    print(f"{'='*55}\n")

    can_execute = _assert_execute_allowed(args)
    success = fail = 0
    for i in range(1, count + 1):
        print(f"── Mint #{i}/{count} ──")
        try:
            tx, built_args = _build_tx(
                w3, account, contract, mint_fn, value_wei, to_addr,
                args.quantity, args.mint_args, args.gas_multiplier, args.priority_fee,
            )
            summary = _summarize_tx(w3, tx, value_wei)
            print(f"  Args:            {built_args}")
            print(f"  Value:           {summary['value_eth']:.6f} ETH")
            print(f"  Estimated Gas:   {summary['estimated_gas']:,}")
            print(f"  Max Fee:         {summary['max_fee_gwei']:.2f} gwei")
            print(f"  Max Total Cost:  {summary['total_max_cost_eth']:.6f} ETH")
            if args.max_total_eth is not None and Decimal(str(summary['total_max_cost_eth'])) > Decimal(args.max_total_eth):
                raise RuntimeError(f"cost cap exceeded: {summary['total_max_cost_eth']} ETH > {args.max_total_eth} ETH")
            if not _check_balance(w3, account, int(Web3.to_wei(summary['total_max_cost_eth'], 'ether'))):
                raise RuntimeError("insufficient balance")
            if can_execute:
                receipt = _send(w3, account, tx)
                print(_format_receipt(receipt))
                success += 1 if receipt.get("status") == 1 else 0
                fail += 0 if receipt.get("status") == 1 else 1
            else:
                print("  ✅ Dry run complete — no tx sent.")
        except Exception as e:
            fail += 1
            print(f"  ❌ Mint #{i} stopped: {e}", file=sys.stderr)
            if can_execute:
                break

    print(f"\n{'='*40}")
    print(f"  Complete: {success} sent ✅ / {fail} stopped ❌")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
