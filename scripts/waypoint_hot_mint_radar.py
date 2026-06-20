#!/usr/bin/env python3
"""Waypoint HOT NFT live mint radar with persistent anti-duplicate delivery.

Outputs a compact Telegram-ready Markdown message, or empty stdout when no new
collections should be posted. Uses Waypoint's public WebSocket/API directly.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import websockets
from curl_cffi import requests

WS_URL = "wss://api.waypoint.tools/ws/mints"
API_BASE = "https://api.waypoint.tools"
BLOCKSCOUT_BASE = "https://eth.blockscout.com"
WAYPOINT_URL = "https://waypoint.tools/mintscan/#0x1cc5659764fe5f750919a4af264145a4013f419a"
STATE_PATH = Path.home() / ".hermes" / "waypoint-hot-mint-radar-state.json"
MONTH_SECONDS = 32 * 24 * 3600


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--listen-seconds", type=float, default=8.0)
    p.add_argument("--min-mints", type=int, default=1)
    p.add_argument(
        "--max-collection-age-hours",
        type=float,
        default=72.0,
        help="only share collections first seen/deployed within this many hours; 0 = current calendar month only",
    )
    p.add_argument("--reset-state", action="store_true")
    p.add_argument(
        "--preview",
        action="store_true",
        help="show current best candidates without touching dedupe state; for manual format tests only",
    )
    return p.parse_args()


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"seen_addresses": [], "seen_names": [], "seen_txs": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"seen_addresses": [], "seen_names": [], "seen_txs": []}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    for key in ("seen_addresses", "seen_names", "seen_txs"):
        state[key] = list(dict.fromkeys(str(x) for x in state.get(key, []) if x))[:3000]
    state["updated_at"] = int(time.time())
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    try:
        STATE_PATH.chmod(0o600)
    except Exception:
        pass


def norm_name(name: str) -> str:
    name = re.sub(r"\s+\(\d+\)$", "", name or "")
    name = re.sub(r"\s*\([^)]*\)$", "", name)
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def now_wib() -> str:
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%H:%M WIB")


def fmt_age(ts: float | int | None) -> str:
    if not ts:
        return "Live now"
    delta = max(0, int(time.time() - float(ts)))
    if delta < 60:
        return f"Live now • {delta}s ago"
    if delta < 3600:
        return f"Live now • {delta // 60}m ago"
    return f"Live now • {delta // 3600}h ago"


def timestamp_dt(ts: float | int | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except Exception:
        return None


def is_current_calendar_month(ts: float | int | None) -> bool:
    dt = timestamp_dt(ts)
    if dt is None:
        return False
    now = datetime.now(timezone.utc)
    return dt.year == now.year and dt.month == now.month and dt <= now + timedelta(minutes=2)


def is_new_collection_timestamp(ts: float | int | None, max_age_hours: float) -> bool:
    dt = timestamp_dt(ts)
    if dt is None:
        return False
    now = datetime.now(timezone.utc)
    if dt > now + timedelta(minutes=2):
        # If upstream clock is slightly future, keep it; if wildly future this still avoids stale old collections.
        return True
    if dt.year != now.year or dt.month != now.month:
        return False
    if max_age_hours and max_age_hours > 0:
        return (now - dt) <= timedelta(hours=max_age_hours)
    return True


def fmt_collection_age(ts: float | int | None) -> str:
    dt = timestamp_dt(ts)
    if dt is None:
        return "New this month"
    delta = max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    if delta < 3600:
        return f"New collection • {max(1, delta // 60)}m old"
    if delta < 86400:
        return f"New collection • {delta // 3600}h old"
    return f"New this month • {delta // 86400}d old"


def get_json(path: str) -> dict[str, Any] | None:
    return http_json(API_BASE + path, headers={"Origin": "https://waypoint.tools", "Referer": "https://waypoint.tools/mintscan/"})


def http_json(url: str, headers: dict[str, str] | None = None, timeout: int = 18) -> dict[str, Any] | None:
    try:
        r = requests.get(url, impersonate="chrome136", headers=headers or {}, timeout=timeout)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def short_addr(addr: str | None) -> str:
    if not addr:
        return "?"
    a = str(addr)
    return a[:6] + "…" + a[-4:] if len(a) > 12 else a


def looks_like_valid_x(twitter: str | None, name: str) -> str | None:
    if not twitter:
        return None
    tw = str(twitter).strip()
    if not tw:
        return None
    # Waypoint sometimes returns direct handles/URLs; keep only plausible X links/handles.
    if tw.startswith("@"):
        handle = tw[1:]
        return f"https://x.com/{handle}" if re.match(r"^[A-Za-z0-9_]{1,15}$", handle) else None
    if re.match(r"^[A-Za-z0-9_]{1,15}$", tw):
        return f"https://x.com/{tw}"
    if "twitter.com/" in tw or "x.com/" in tw:
        return tw.replace("twitter.com", "x.com")
    return None


def blockscout_contract_analysis(addr: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    address = http_json(f"{BLOCKSCOUT_BASE}/api/v2/addresses/{addr}") or {}
    token = address.get("token") if isinstance(address.get("token"), dict) else {}
    contract = http_json(f"{BLOCKSCOUT_BASE}/api/v2/smart-contracts/{addr}") or {}
    holders = http_json(f"{BLOCKSCOUT_BASE}/api/v2/tokens/{addr}/holders") or {}

    creator = address.get("creator_address_hash")
    out["creator"] = creator
    out["creation_tx"] = address.get("creation_transaction_hash")
    out["verified"] = bool(address.get("is_verified") or contract.get("creation_status") == "success")
    out["contract_type"] = token.get("type") or "NFT"
    out["holders_count"] = token.get("holders_count")
    out["blockscout_name"] = address.get("name") or token.get("name")
    impls = contract.get("implementations") or address.get("implementations") or []
    if impls and isinstance(impls, list):
        names = [x.get("name") for x in impls if isinstance(x, dict) and x.get("name")]
        out["implementation"] = ", ".join(names[:2]) if names else None
    out["proxy_type"] = address.get("proxy_type") or contract.get("proxy_type")

    items = holders.get("items") if isinstance(holders, dict) else []
    top = 0
    top_addr = None
    if isinstance(items, list):
        for idx, h in enumerate(items[:20]):
            try:
                val = int(h.get("value") or 0)
            except Exception:
                val = 0
            if idx == 0:
                top = val
                top_addr = ((h.get("address") or {}).get("hash"))
    supply = None
    try:
        supply = int(token.get("total_supply") or 0)
    except Exception:
        pass
    if supply and top:
        out["top_holder_pct"] = round(top / supply * 100, 1)
        out["top_holder_value"] = top
        out["top_holder_address"] = top_addr

    if creator:
        dev_tokens = http_json(f"{BLOCKSCOUT_BASE}/api/v2/addresses/{creator}/tokens?type=ERC-721") or {}
        dev_value = None
        for item in dev_tokens.get("items", []) if isinstance(dev_tokens, dict) else []:
            tok = item.get("token") or {}
            if str(tok.get("address_hash") or "").lower() == addr.lower():
                try:
                    dev_value = int(item.get("value") or 0)
                except Exception:
                    dev_value = None
                break
        if dev_value is not None:
            out["deployer_holdings"] = dev_value
            if supply:
                out["deployer_holding_pct"] = round(dev_value / supply * 100, 1)
    return out


def website_url(raw: str | None) -> str | None:
    if not raw:
        return None
    url = str(raw).strip()
    if not url or url.lower() in {"none", "null", "-"}:
        return None
    if url.startswith("//"):
        url = "https:" + url
    elif not re.match(r"^https?://", url, flags=re.I):
        url = "https://" + url
    return url


def opensea_enrichment(slug: str | None) -> dict[str, Any]:
    if not slug:
        return {}
    out: dict[str, Any] = {}
    base = "https://api.opensea.io/api/v2/collections"
    meta = http_json(f"{base}/{slug}") or {}
    stats = http_json(f"{base}/{slug}/stats") or {}
    if meta:
        out["os_project_url"] = meta.get("project_url")
        out["os_twitter"] = meta.get("twitter_username")
        out["os_discord"] = meta.get("discord_url")
        out["os_collection_url"] = meta.get("opensea_url")
        out["os_safelist"] = meta.get("safelist_status")
        out["os_collection_offers_enabled"] = meta.get("collection_offers_enabled")
    total = stats.get("total") if isinstance(stats.get("total"), dict) else {}
    out["os_volume"] = total.get("volume")
    out["os_sales"] = total.get("sales")
    out["os_floor"] = total.get("floor_price")
    out["os_num_owners"] = total.get("num_owners")
    for row in stats.get("intervals", []) if isinstance(stats.get("intervals"), list) else []:
        if row.get("interval") == "one_day":
            out["os_volume_1d"] = row.get("volume")
            out["os_sales_1d"] = row.get("sales")
    return out


def social_label(c: dict[str, Any]) -> str:
    bits = []
    if c.get("twitter_url"):
        bits.append("X linked")
    else:
        bits.append("No X found")
    if website_url(c.get("website")):
        bits.append("website linked")
    if c.get("discord_url"):
        bits.append("Discord linked")
    return " • ".join(bits)


def risk_notes(c: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    if not c.get("verified_contract"):
        notes.append("contract unverified")
    if not c.get("twitter_url"):
        notes.append("no X")
    if c.get("holders_count") in (None, "0", 0):
        notes.append("holders unknown")
    try:
        if c.get("top_holder_pct") and float(c["top_holder_pct"]) >= 20:
            notes.append(f"top holder {c['top_holder_pct']}%")
    except Exception:
        pass
    try:
        if c.get("deployer_holding_pct") and float(c["deployer_holding_pct"]) >= 5:
            notes.append(f"deployer holds {c['deployer_holding_pct']}%")
    except Exception:
        pass
    if c.get("os_sales") in (None, 0, "0") and not c.get("os_volume"):
        notes.append("no market demand yet")
    if c.get("deployer") is None and c.get("creator") is None:
        notes.append("deployer unknown")
    return notes[:4]


def score_badge(score: int) -> str:
    if score >= 80:
        return f"{score}/100 🔥 Strong"
    if score >= 60:
        return f"{score}/100 🟡 Medium"
    if score >= 40:
        return f"{score}/100 🟠 Speculative"
    return f"{score}/100 🔴 Weak"


def alpha_score(c: dict[str, Any]) -> tuple[int, list[str]]:
    """Free-mint DD score: real demand + distribution matter more than FP/mint hype."""
    score = 0
    reasons: list[str] = []

    recent = int(c.get("recent_count") or 0)
    if recent >= 50:
        score += 15
        reasons.append("hot mint flow")
    elif recent >= 15:
        score += 11
        reasons.append("active mint")
    elif recent >= 3:
        score += 6
        reasons.append("some activity")
    elif recent >= 1:
        score += 3

    if c.get("is_free"):
        score += 8
        reasons.append("free mint")
    if c.get("is_mintable"):
        score += 5
        reasons.append("mintable")
    if c.get("verified_contract"):
        score += 8
        reasons.append("verified")
    else:
        score -= 12

    if c.get("twitter_url"):
        score += 8
        reasons.append("X linked")
    else:
        score -= 8
    if website_url(c.get("website")):
        score += 6
        reasons.append("website linked")
    else:
        score -= 6
    if c.get("discord_url"):
        score += 3

    try:
        sales = int(c.get("os_sales") or 0)
    except Exception:
        sales = 0
    try:
        volume = float(c.get("os_volume") or 0)
    except Exception:
        volume = 0.0
    try:
        floor = float(c.get("os_floor") or 0)
    except Exception:
        floor = 0.0

    # User rule: do not trust FP. Volume/sales/offers are the demand signal.
    if volume >= 0.05 and sales >= 20:
        score += 20
        reasons.append("real demand")
    elif volume >= 0.01 or sales >= 25:
        score += 12
        reasons.append("some demand")
    elif volume > 0 or sales >= 5:
        score += 7
        reasons.append("thin demand")
    elif floor > 0:
        score -= 12
        reasons.append("FP no volume")
    else:
        score -= 10
        reasons.append("no demand yet")

    try:
        holders = int(c.get("holders_count") or 0)
    except Exception:
        holders = 0
    try:
        minters = int(c.get("unique_minters") or 0)
    except Exception:
        minters = 0
    if holders >= 300:
        score += 10
        reasons.append("holder base")
    elif holders >= 100:
        score += 8
        reasons.append("holder base")
    elif holders >= 20:
        score += 5
    elif holders >= 5:
        score += 2
    elif holders == 0:
        score -= 8
    if minters >= 300:
        score += 7
        reasons.append("many minters")
    elif minters >= 100:
        score += 5
        reasons.append("many minters")
    elif minters >= 20:
        score += 3

    try:
        top = float(c.get("top_holder_pct") or 0)
    except Exception:
        top = 0.0
    if 0 < top <= 5:
        score += 10
        reasons.append("healthy spread")
    elif 0 < top <= 10:
        score += 7
        reasons.append("healthy spread")
    elif 0 < top <= 20:
        score += 2
    elif top > 30:
        score -= 18
        reasons.append("top holder concentrated")
    elif top > 20:
        score -= 10
        reasons.append("top holder high")

    try:
        dev_pct = float(c.get("deployer_holding_pct") or 0)
    except Exception:
        dev_pct = 0.0
    if dev_pct >= 10:
        score -= 18
        reasons.append("dev hoard risk")
    elif dev_pct >= 5:
        score -= 10
        reasons.append("dev holds supply")
    elif 0 < dev_pct <= 2:
        score += 3

    if c.get("deployer") or c.get("creator"):
        score += 5
        reasons.append("deployer found")
    else:
        score -= 6

    dt = timestamp_dt(c.get("collection_birth"))
    if dt:
        age_min = max(0, int((datetime.now(timezone.utc) - dt).total_seconds() // 60))
        if age_min <= 60:
            score += 5
            reasons.append("very new")
        elif age_min <= 360:
            score += 3
            reasons.append("new today")

    # Hard caps so mint hype/FP cannot override missing demand/social/hoard risk.
    if volume < 0.01 and sales < 25:
        score = min(score, 72)
    if not c.get("twitter_url"):
        score = min(score, 78)
    if not website_url(c.get("website")) and not c.get("twitter_url"):
        score = min(score, 62)
    if top > 20:
        score = min(score, 68)
    if dev_pct >= 5:
        score = min(score, 65)
    if (floor > 0) and volume == 0 and sales == 0:
        score = min(score, 50)

    score = max(0, min(100, score))
    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return score, deduped[:4]


async def collect_ws(listen_seconds: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headers = {
        "Origin": "https://waypoint.tools",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Referer": "https://waypoint.tools/mintscan/",
    }
    overview: dict[str, Any] = {}
    mints: list[dict[str, Any]] = []
    async with websockets.connect(WS_URL, additional_headers=headers, open_timeout=20, ping_interval=None) as ws:
        deadline = time.time() + listen_seconds
        while time.time() < deadline:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=max(0.5, deadline - time.time()))
            except asyncio.TimeoutError:
                break
            try:
                data = json.loads(msg)
            except Exception:
                continue
            typ = data.get("type")
            if typ == "overview":
                overview = data
            elif typ == "mint":
                mints.append(data)
    return overview, mints


def merge_overview_candidates(overview: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    windows = overview.get("windows") if isinstance(overview, dict) else None
    if not isinstance(windows, dict):
        return out
    # Use short windows so repeated 24h hot collections don't spam forever.
    for win in ("60", "180", "300", "600"):
        rows = windows.get(win) or []
        if not isinstance(rows, list):
            continue
        for idx, c in enumerate(rows[:20]):
            addr = str(c.get("address") or "").lower()
            if not addr.startswith("0x"):
                continue
            cur = out.setdefault(addr, dict(c))
            cur[f"mints_{win}s"] = c.get("recent_mints") or 0
            cur["best_rank"] = min(int(cur.get("best_rank", 999)), idx + 1)
            cur["address"] = addr
    return out


def build_candidates(overview: dict[str, Any], live_mints: list[dict[str, Any]], max_collection_age_hours: float) -> list[dict[str, Any]]:
    by_addr = merge_overview_candidates(overview)
    grouped_mints: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in live_mints:
        addr = str(m.get("address") or "").lower()
        if addr.startswith("0x"):
            grouped_mints[addr].append(m)
            by_addr.setdefault(addr, {"address": addr, "name": m.get("name") or addr[:10]})
    candidates: list[dict[str, Any]] = []
    for addr, c in by_addr.items():
        detail = get_json(f"/api/collection/{addr}") or {}
        mints = grouped_mints.get(addr) or []
        latest = max((float(m.get("timestamp") or 0) for m in mints), default=float(detail.get("last_mint_time") or 0))
        first_seen = detail.get("first_seen")
        deployed_at = detail.get("deployed_at")
        collection_birth = first_seen or deployed_at
        # Strict user preference: only share collections from the current month,
        # and especially fresh ones. Do not fall back to latest mint time for
        # unknown/old collections, because that lets old collections with new txs through.
        if not is_new_collection_timestamp(collection_birth, max_collection_age_hours):
            continue
        if deployed_at and not is_current_calendar_month(deployed_at):
            continue
        if latest and time.time() - float(latest) > 10 * 60:
            continue
        name = detail.get("short_name") or c.get("name") or detail.get("name") or addr[:10]
        chain_analysis = blockscout_contract_analysis(addr)
        os_data = opensea_enrichment(detail.get("opensea_slug"))
        website = detail.get("website") or os_data.get("os_project_url")
        twitter_url = looks_like_valid_x(detail.get("twitter"), name) or looks_like_valid_x(os_data.get("os_twitter"), name)
        discord_url = detail.get("discord_url") or os_data.get("os_discord")
        txs = list(dict.fromkeys(str(m.get("tx_hash") or "") for m in mints if m.get("tx_hash")))
        recent_count = max(
            int(c.get("mints_60s") or 0),
            int(c.get("mints_180s") or 0),
            int(c.get("recent_mints") or 0),
            len(mints),
            int(detail.get("mints_3m") or 0),
        )
        if recent_count < 1:
            continue
        price_raw = detail.get("mint_price_raw")
        price = detail.get("mint_price") or (mints[-1].get("mint_price") if mints else None) or "?"
        is_free = price_raw == 0 or str(price).lower() == "free" or any(str(m.get("mint_price") or "").lower() == "free" for m in mints)
        score = recent_count
        if is_free:
            score += 10000
        if detail.get("is_mintable") or c.get("is_mintable"):
            score += 500
        if latest:
            score += max(0, 900 - int(time.time() - float(latest)))
        candidates.append({
            "address": addr,
            "name": name,
            "norm_name": norm_name(name),
            "recent_count": recent_count,
            "tx_count": len(txs) if txs else None,
            "latest_tx": txs[0] if txs else ((detail.get("recent_mints") or [{}])[0].get("tx_hash") if isinstance(detail.get("recent_mints"), list) and detail.get("recent_mints") else None),
            "price": "Free" if is_free else str(price),
            "is_free": is_free,
            "is_mintable": bool(detail.get("is_mintable") or c.get("is_mintable")),
            "current_supply": detail.get("current_supply"),
            "max_supply": detail.get("max_supply"),
            "opensea_url": detail.get("opensea_url") or os_data.get("os_collection_url"),
            "etherscan_url": detail.get("etherscan_url"),
            "twitter_url": twitter_url,
            "website": website,
            "discord_url": discord_url,
            "deployer": detail.get("deployer"),
            "deployer_url": detail.get("deployer_url"),
            "creator": chain_analysis.get("creator"),
            "creation_tx": chain_analysis.get("creation_tx"),
            "verified_contract": chain_analysis.get("verified"),
            "contract_type": chain_analysis.get("contract_type"),
            "implementation": chain_analysis.get("implementation"),
            "proxy_type": chain_analysis.get("proxy_type"),
            "holders_count": chain_analysis.get("holders_count") or detail.get("unique_minters"),
            "unique_minters": detail.get("unique_minters"),
            "wallet_ratio": detail.get("wallet_ratio"),
            "top_holder_pct": chain_analysis.get("top_holder_pct"),
            "top_holder_value": chain_analysis.get("top_holder_value"),
            "top_holder_address": chain_analysis.get("top_holder_address"),
            "deployer_holdings": chain_analysis.get("deployer_holdings"),
            "deployer_holding_pct": chain_analysis.get("deployer_holding_pct"),
            "os_volume": os_data.get("os_volume"),
            "os_volume_1d": os_data.get("os_volume_1d"),
            "os_sales": os_data.get("os_sales"),
            "os_sales_1d": os_data.get("os_sales_1d"),
            "os_floor": os_data.get("os_floor"),
            "os_collection_offers_enabled": os_data.get("os_collection_offers_enabled"),
            "first_seen": first_seen,
            "deployed_at": deployed_at,
            "collection_birth": collection_birth,
            "last_mint_time": latest,
            "score": score,
        })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


def format_item(i: int, c: dict[str, Any]) -> str:
    tx_count = c.get("tx_count") or "?"
    supply_cur = c.get("current_supply") if c.get("current_supply") is not None else "?"
    supply_max = c.get("max_supply") if c.get("max_supply") is not None else "?"
    price = "0 ETH" if c.get("is_free") else c.get("price", "?")
    status = []
    status.append(fmt_collection_age(c.get("collection_birth")))
    if c.get("is_mintable"):
        status.append("Mintable")
    status.append(fmt_age(c.get("last_mint_time")))

    contract_bits = []
    if c.get("verified_contract"):
        contract_bits.append("verified")
    elif c.get("verified_contract") is False:
        contract_bits.append("unverified")
    if c.get("implementation"):
        contract_bits.append(str(c["implementation"]).replace("ERC721", "ERC721"))
    elif c.get("contract_type"):
        contract_bits.append(str(c["contract_type"]))
    if c.get("proxy_type"):
        contract_bits.append(str(c["proxy_type"]))

    deployer = c.get("deployer") or c.get("creator")

    holder_bits = []
    if c.get("holders_count"):
        holder_bits.append(f"{c['holders_count']} holders")
    if c.get("unique_minters"):
        holder_bits.append(f"{c['unique_minters']} minters")
    if c.get("top_holder_pct"):
        holder_bits.append(f"top {c['top_holder_pct']}%")
    holder_line = " • ".join(holder_bits) if holder_bits else "?"

    dev_line = None
    if c.get("deployer_holdings") is not None:
        dev_line = f"{c['deployer_holdings']} NFT"
        if c.get("deployer_holding_pct") is not None:
            dev_line += f" • {c['deployer_holding_pct']}%"

    market_bits = []
    if c.get("os_volume") is not None:
        market_bits.append(f"Vol {float(c['os_volume']):.4f} ETH")
    if c.get("os_sales") is not None:
        market_bits.append(f"{c['os_sales']} sales")
    if c.get("os_floor") is not None:
        market_bits.append(f"FP {c['os_floor']} ETH")
    if c.get("os_collection_offers_enabled"):
        market_bits.append("offers enabled")
    market_line = " • ".join(market_bits) if market_bits else "no volume/offers data"

    score, score_reasons = alpha_score(c)
    notes = risk_notes(c)

    links = [f"[Waypoint]({WAYPOINT_URL})"]
    if c.get("opensea_url"):
        links.append(f"[OpenSea]({c['opensea_url']})")
    site = website_url(c.get("website"))
    if site:
        links.append(f"[Website]({site})")
    if c.get("twitter_url"):
        links.append(f"[X]({c['twitter_url']})")
    if c.get("etherscan_url"):
        links.append(f"[Contract]({c['etherscan_url']})")
    if c.get("latest_tx"):
        links.append(f"[Tx](https://etherscan.io/tx/{c['latest_tx']})")
    if c.get("creation_tx"):
        links.append(f"[DeployTx](https://etherscan.io/tx/{c['creation_tx']})")

    mint_lines = [
        "🟢 **Mint Info**",
        f"• Mint: {c['recent_count']} mints / {tx_count} tx",
        f"• Price: {price}",
        f"• Supply: {supply_cur} / {supply_max}",
        f"• Status: {' • '.join(status)}",
    ]
    score_lines = [
        "📊 **Score**",
        f"• {score_badge(score)}",
        f"• Reason: {', '.join(score_reasons) if score_reasons else 'basic signal'}",
    ]
    project_lines = [
        "🔎 **Project Check**",
        f"• Social: {social_label(c)}",
        f"• Market: {market_line}",
        f"• Contract: {' • '.join(contract_bits[:3]) if contract_bits else '?'}",
        f"• Deployer: {short_addr(deployer)}",
    ]
    if dev_line:
        project_lines.append(f"• Dev wallet: {dev_line}")
    project_lines.extend([
        f"• Holders: {holder_line}",
        f"• Notes: {', '.join(notes) if notes else 'basic checks ok'}",
    ])
    link_lines = ["🔗 **Links**", " • ".join(links)]

    # Balanced mobile Telegram spacing: blank lines between sections only,
    # single newlines inside each section so it does not look too tall.
    return "\n\n".join([
        f"**{i}. {c['name']}**\n━━━━━━━━━━━━━━━━━━━━",
        "\n".join(mint_lines),
        "\n".join(score_lines),
        "\n".join(project_lines),
        "\n".join(link_lines),
    ])


def main() -> int:
    args = parse_args()
    if args.reset_state and STATE_PATH.exists():
        STATE_PATH.unlink()
    state = load_state()
    seen_addresses = set(str(x).lower() for x in state.get("seen_addresses", []))
    seen_names = set(str(x) for x in state.get("seen_names", []))
    overview, mints = asyncio.run(collect_ws(args.listen_seconds))
    candidates = build_candidates(overview, mints, args.max_collection_age_hours)
    selected = []
    for c in candidates:
        if not args.preview and (c["address"] in seen_addresses or c["norm_name"] in seen_names):
            continue
        if int(c.get("recent_count") or 0) < args.min_mints:
            continue
        selected.append(c)
        if len(selected) >= min(max(args.limit, 1), 3):
            break
    # Always mark candidates seen so recurring hot collections don't get posted later.
    # Preview mode is read-only so manual format tests don't affect cron dedupe.
    if candidates and not args.preview:
        state["seen_addresses"] = [c["address"] for c in candidates] + list(seen_addresses)
        state["seen_names"] = [c["norm_name"] for c in candidates if c.get("norm_name")] + list(seen_names)
        state["seen_txs"] = [c["latest_tx"] for c in candidates if c.get("latest_tx")] + list(state.get("seen_txs", []))
        state["last_candidates"] = [{"name": c["name"], "address": c["address"], "recent_count": c["recent_count"]} for c in candidates[:20]]
        save_state(state)
    if not selected:
        return 0
    print("🔥 HOT NFT Live Mint")
    print(f"Update {now_wib()} • Waypoint")
    print("")
    for idx, c in enumerate(selected, 1):
        if idx > 1:
            print("")
        print(format_item(idx, c))
    print("")
    print("DYOR sebelum mint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
