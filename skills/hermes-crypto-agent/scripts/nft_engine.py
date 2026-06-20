"""
hermes/nft_engine.py — Template NFT buy/sell lintas-marketplace.

EVM: Reservoir aggregator (multi-marketplace: OpenSea + Blur + LooksRare + dst)
Solana: Magic Eden + Tensor
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import httpx
from web3 import Web3
from eth_account.signers.local import LocalAccount


@dataclass
class NFTResult:
    status: str
    tx_hashes: list[str] = None
    error: Optional[str] = None


def _load_governor_classes():
    try:
        from .governor import SpendGovernor, TxIntent
    except ImportError:  # script copied/executed flat
        from governor import SpendGovernor, TxIntent
    return SpendGovernor, TxIntent


def _authorize_tx(w3: Web3, account: LocalAccount, action: str, tx: dict,
                  *, usd_value: Optional[float] = None):
    SpendGovernor, TxIntent = _load_governor_classes()
    gov = SpendGovernor()
    try:
        w3.eth.call({k: tx[k] for k in ("from", "to", "data", "value") if k in tx})
        simulated_ok = True
    except Exception:
        simulated_ok = False
    intent = TxIntent(
        wallet=account.address,
        chain_id=w3.eth.chain_id,
        action=action,
        usd_value=usd_value,
        native_value=int(tx.get("value", 0)) / 1e18,
        gas_price_wei=tx.get("maxFeePerGas") or tx.get("gasPrice"),
        simulated_ok=simulated_ok,
        recipient=tx.get("to"),
    )
    decision = gov.authorize(intent)
    return decision, gov, intent


# ─────────────────────────── EVM / Reservoir ───────────────────────────

# Reservoir chain subdomain mapping
RESERVOIR_CHAINS = {
    1: "ethereum", 8453: "base", 42161: "arbitrum",
    10: "optimism", 137: "polygon", 56: "bsc",
    43114: "avalanche", 7777777: "zora",
}


class ReservoirClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def base_url(self, chain_id: int) -> str:
        sub = RESERVOIR_CHAINS[chain_id]
        return f"https://api-{sub}.reservoir.tools" if sub != "ethereum" \
            else "https://api.reservoir.tools"

    async def execute_buy(self, chain_id: int, items: list[dict],
                           taker: str) -> dict:
        """items: [{token: '0xcontract:tokenId', quantity: 1}, ...]"""
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{self.base_url(chain_id)}/execute/buy/v7",
                json={"items": items, "taker": taker, "source": "hermes-agent"},
                headers={"x-api-key": self.api_key, "content-type": "application/json"},
            )
        r.raise_for_status()
        return r.json()

    async def execute_list(self, chain_id: int, listings: list[dict],
                            maker: str) -> dict:
        """listings: [{token, weiPrice, orderbook, orderKind, ...}]"""
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{self.base_url(chain_id)}/execute/list/v5",
                json={"params": listings, "maker": maker, "source": "hermes-agent"},
                headers={"x-api-key": self.api_key, "content-type": "application/json"},
            )
        r.raise_for_status()
        return r.json()


async def buy_nft_evm(w3: Web3, account: LocalAccount,
                       contract: str, token_id: str,
                       reservoir_api_key: Optional[str] = None,
                       execute: bool = False,
                       usd_value: Optional[float] = None) -> NFTResult:
    rc = ReservoirClient(reservoir_api_key or os.environ["RESERVOIR_API_KEY"])
    plan = await rc.execute_buy(
        w3.eth.chain_id,
        [{"token": f"{contract}:{token_id}", "quantity": 1}],
        account.address,
    )
    return await _execute_reservoir_steps(w3, account, plan, execute=execute, usd_value=usd_value)


async def sweep_floor_evm(w3: Web3, account: LocalAccount,
                            collection_contract: str, count: int,
                            max_price_wei: int,
                            reservoir_api_key: Optional[str] = None,
                            execute: bool = False,
                            usd_value: Optional[float] = None) -> NFTResult:
    """Floor sweep: ambil N termurah dari contract, kalau price <= max."""
    rc = ReservoirClient(reservoir_api_key or os.environ["RESERVOIR_API_KEY"])

    # 1. fetch cheapest listings
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{rc.base_url(w3.eth.chain_id)}/orders/asks/v5",
            params={"contracts": collection_contract, "status": "active",
                    "sortBy": "price", "limit": count},
            headers={"x-api-key": rc.api_key},
        )
    orders = r.json().get("orders", [])
    eligible = [o for o in orders if int(o["price"]["amount"]["raw"]) <= max_price_wei]
    if not eligible:
        return NFTResult(status="error", error="no listings under max price")

    items = [{"token": f"{collection_contract}:{o['tokenSetId'].split(':')[-1]}",
              "quantity": 1} for o in eligible]
    plan = await rc.execute_buy(w3.eth.chain_id, items, account.address)
    return await _execute_reservoir_steps(w3, account, plan, execute=execute, usd_value=usd_value)


async def list_nft_evm(w3: Web3, account: LocalAccount,
                        contract: str, token_id: str, price_eth: float,
                        marketplace: str = "opensea",
                        reservoir_api_key: Optional[str] = None,
                        execute: bool = False,
                        usd_value: Optional[float] = None) -> NFTResult:
    """List NFT for sale. marketplace: 'opensea'|'blur'|'looks-rare'."""
    rc = ReservoirClient(reservoir_api_key or os.environ["RESERVOIR_API_KEY"])
    wei_price = w3.to_wei(price_eth, "ether")
    plan = await rc.execute_list(
        w3.eth.chain_id,
        [{
            "token": f"{contract}:{token_id}",
            "weiPrice": str(wei_price),
            "orderbook": marketplace,
            "orderKind": "seaport-v1.6" if marketplace == "opensea" else "blur",
        }],
        account.address,
    )
    return await _execute_reservoir_steps(w3, account, plan, execute=execute, usd_value=usd_value)


async def _execute_reservoir_steps(w3: Web3, account: LocalAccount, plan: dict,
                                   *, execute: bool = False,
                                   usd_value: Optional[float] = None) -> NFTResult:
    """Iterate Reservoir steps with governor gate; dry-run unless execute=True."""
    tx_hashes = []
    pending_signatures = 0
    for step in plan.get("steps", []):
        for item in step.get("items", []):
            kind = item.get("kind")
            if item.get("status") != "incomplete":
                continue
            if kind == "transaction":
                tx_data = item["data"]
                tx = {
                    "from": account.address,
                    "to": Web3.to_checksum_address(tx_data["to"]),
                    "data": tx_data["data"],
                    "value": int(tx_data.get("value", 0)),
                    "gas": int(tx_data.get("gas", 300000)),
                    "nonce": w3.eth.get_transaction_count(account.address, "pending"),
                    "chainId": w3.eth.chain_id,
                    "maxFeePerGas": w3.eth.gas_price * 2,
                    "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
                }
                decision, gov, intent = _authorize_tx(w3, account, "nft", tx, usd_value=usd_value)
                if not decision.allowed:
                    return NFTResult(status=decision.verdict, tx_hashes=tx_hashes, error=decision.summary())
                if not execute:
                    return NFTResult(status="dry_run", tx_hashes=tx_hashes,
                                     error="dry run only; pass execute=True after user confirmation")
                signed = account.sign_transaction(tx)
                h = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
                gov.record(intent, h)
                tx_hashes.append(h)
                w3.eth.wait_for_transaction_receipt(h, timeout=180)
            elif kind == "signature":
                # EIP-712 typed data signing can create/list orders; require execute=True.
                pending_signatures += 1
                if not execute:
                    return NFTResult(status="dry_run", tx_hashes=tx_hashes,
                                     error="signature step present; pass execute=True after user confirmation")
                from eth_account.messages import encode_typed_data
                msg = encode_typed_data(full_message=item["data"]["sign"])
                signature = account.sign_message(msg).signature.hex()
                post_url = item["data"]["post"]["endpoint"]
                post_body = item["data"]["post"]["body"]
                post_body["signature"] = signature
                async with httpx.AsyncClient() as c:
                    await c.post(f"https://api.reservoir.tools{post_url}", json=post_body)
    return NFTResult(status="sent" if execute else "dry_run", tx_hashes=tx_hashes,
                     error=None if execute else f"planned {pending_signatures} signature step(s), no tx sent")


# ─────────────────────────── SOLANA / Magic Eden ───────────────────────────

async def buy_nft_solana_me(client, keypair, token_mint: str,
                              max_price_sol: float,
                              execute: bool = False) -> NFTResult:
    """Buy lewat Magic Eden public API."""
    from solders.transaction import VersionedTransaction
    import base64

    ME = "https://api-mainnet.magiceden.dev/v2"
    async with httpx.AsyncClient() as c:
        # 1. cari listing untuk mint ini
        r = await c.get(f"{ME}/tokens/{token_mint}/listings")
        listings = r.json()
        if not listings:
            return NFTResult(status="error", error="no listing for mint")
        l = listings[0]
        if l["price"] > max_price_sol:
            return NFTResult(status="error", error=f"price {l['price']} > max {max_price_sol}")

        # 2. dapat instructions buy
        r = await c.get(f"{ME}/instructions/buy_now", params={
            "buyer": str(keypair.pubkey()),
            "seller": l["seller"],
            "tokenMint": token_mint,
            "tokenATA": l["tokenAddress"],
            "price": l["price"],
            "auctionHouseAddress": l.get("auctionHouse"),
        })
        tx_resp = r.json()

    raw = base64.b64decode(tx_resp["txSigned"]["data"])
    vtx = VersionedTransaction.from_bytes(raw)
    from solders.message import to_bytes_versioned
    if not execute:
        return NFTResult(status="dry_run", error="dry run only; pass execute=True after user confirmation")
    signed = VersionedTransaction(vtx.message,
                                    [keypair.sign_message(to_bytes_versioned(vtx.message))])
    sig = await client.send_raw_transaction(bytes(signed))
    return NFTResult(status="sent", tx_hashes=[str(sig.value)])
