#!/usr/bin/env python3
"""Authenticated X keyword radar for NFT mint signals.

Reads X_AUTH_TOKEN/X_CT0 from /root/.hermes/x-radar.env or /root/.hermes/.env.
Prints JSON with only public tweet metadata. Never prints cookies/tokens.

Modes:
- general: free mint / stealth mint / live mint NFT signals ONLY (no WL/allowlist/whitelist)
- wl: WL / Allowlist / Whitelist specific signals
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

HOME = Path.home()
ENV_FILES = [HOME / ".hermes" / "x-radar.env", HOME / ".hermes" / ".env"]
STATE_BASE = HOME / ".hermes" / "x-radar-state"
BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
SEARCH_QID = "yIphfmxUO-hddQHKIOk9tA"  # SearchTimeline op id scraped from X main.js on 2026-06-18.

MODE_CONFIG = {
    "general": {
        "title": "X NFT Mint Radar",
        "state": STATE_BASE.with_name("x-radar-state-general.json"),
        "queries": [
            '"free mint" (NFT OR ERC721 OR ERC-721 OR mint) (Ethereum OR ETH OR mainnet)',
            '("stealth mint" OR "stealth launch") (NFT OR mint)',
            '("mint live" OR "live mint") (NFT OR ERC721 OR mint) (Ethereum OR ETH)',
            '"0x" "free mint" (NFT OR ERC721)',
        ],
        "keywords": [
            "free mint", "stealth mint", "stealth launch", "mint live", "live mint", "erc721", "erc-721", "0x",
        ],
        "exclude_keywords": ["allowlist", "whitelist", "white list", " wl", "wl ", "wl.", "wl:", "wl?"],
    },
    "wl": {
        "title": "X NFT WL/Allowlist Radar",
        "state": STATE_BASE.with_name("x-radar-state-wl.json"),
        "queries": [
            '(WL OR allowlist OR whitelist OR "white list" OR "early access") (NFT OR mint) (Ethereum OR ETH OR mainnet)',
            '("WL ready" OR "WL open" OR "WL spots" OR "WL giveaway" OR "early access") (NFT OR mint)',
            '("allowlist open" OR "allowlist live" OR "allowlist spots" OR "allowlist giveaway" OR "early access open" OR "early access live") NFT',
            '("whitelist open" OR "whitelist live" OR "whitelist spots" OR "whitelist giveaway" OR "early access spots" OR "early access giveaway") NFT',
        ],
        "keywords": ["allowlist", "whitelist", "white list", "early access", " wl", "wl ", "wl.", "wl:", "wl?"],
    },
}

SPAM_WORDS = [
    "airdrop claim", "seed phrase", "private key", "connect wallet now",
    "double your", "giveaway winner", "usdt", "forex", "casino", "presale token",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Authenticated X NFT mint radar")
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_CONFIG),
        default=os.environ.get("X_RADAR_MODE", "general"),
        help="radar mode/category",
    )
    parser.add_argument("--limit", type=int, default=8, help="max JSON items")
    parser.add_argument("--no-dedupe", action="store_true", help="do not filter/update seen state")
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=72.0,
        help="only keep posts newer than this many hours; default prioritizes very recent posts",
    )
    return parser.parse_args()


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for path in ENV_FILES:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k in {"X_AUTH_TOKEN", "X_CT0", "X_CSRF_TOKEN"} and v:
                env[k] = v
    env.update({k: v for k, v in os.environ.items() if k in {"X_AUTH_TOKEN", "X_CT0", "X_CSRF_TOKEN"} and v})
    return env


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"seen_ids": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"seen_ids": []}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = list(dict.fromkeys(state.get("seen_ids", [])))[:2500]
    seen_urls = list(dict.fromkeys(state.get("seen_urls", [])))[:2500]
    fingerprints = list(dict.fromkeys(state.get("seen_fingerprints", [])))[:2500]
    state["seen_ids"] = seen
    state["seen_urls"] = seen_urls
    state["seen_fingerprints"] = fingerprints
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    try:
        path.chmod(0o600)
    except Exception:
        pass


def parse_tweet_time(created_at: str | None) -> datetime | None:
    if not created_at:
        return None
    try:
        dt = parsedate_to_datetime(created_at)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def current_month_bounds() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def is_recent_this_month(created_at: str | None, max_age_hours: float) -> tuple[bool, float | None, str | None]:
    dt = parse_tweet_time(created_at)
    if dt is None:
        return False, None, "missing/invalid created_at"
    start, now = current_month_bounds()
    if dt < start or dt > now:
        return False, None, "not current month"
    age_hours = max(0.0, (now - dt).total_seconds() / 3600)
    if max_age_hours > 0 and age_hours > max_age_hours:
        return False, age_hours, f"older than {max_age_hours:g}h"
    return True, age_hours, None


def normalize_for_fingerprint(text: str) -> str:
    text = re.sub(r"https?://\S+", " ", text or "")
    text = re.sub(r"@[A-Za-z0-9_]+", " ", text)
    text = re.sub(r"#[A-Za-z0-9_]+", " ", text)
    text = re.sub(r"\b\d+[KkMm]?\b", " ", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
    words = [w for w in text.split() if len(w) > 2]
    return " ".join(words[:32])


def content_fingerprint(t: dict[str, Any]) -> str:
    text = t.get("text") or ""
    contract = re.search(r"0x[a-fA-F0-9]{40}", text)
    if contract:
        return f"contract:{contract.group(0).lower()}"
    urls = re.findall(r"https?://\S+", text)
    if urls:
        clean_url = urls[0].rstrip(').,!?')
        return f"url:{clean_url.lower()}"
    normalized = normalize_for_fingerprint(text)
    return f"text:{normalized[:180]}"


def request_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
    return json.loads(data.decode("utf-8"))


def build_headers(auth: str, ct0: str) -> dict[str, str]:
    return {
        "authorization": f"Bearer {BEARER}",
        "cookie": f"auth_token={auth}; ct0={ct0}",
        "x-csrf-token": ct0,
        "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "en",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
        "accept": "application/json, text/plain, */*",
        "referer": "https://x.com/search?q=free%20mint&src=typed_query&f=live",
    }


_CFFI_SESSION = None
_CLIENT_TRANSACTION = None
_CLIENT_TRANSACTION_TIME = 0.0


def cffi_session(auth: str, ct0: str):
    """Browser-impersonating X session.

    X GraphQL often returns 404 to plain urllib even with valid cookies.
    curl_cffi plus X-Client-Transaction-Id mirrors the working x-tg-notify
    request pattern while keeping cookies/tokens out of stdout.
    """
    global _CFFI_SESSION
    if _CFFI_SESSION is None:
        from curl_cffi import requests as cffi

        _CFFI_SESSION = cffi.Session(impersonate="chrome136")
        _CFFI_SESSION.cookies.set("auth_token", auth, domain=".x.com")
        _CFFI_SESSION.cookies.set("ct0", ct0, domain=".x.com")
        _CFFI_SESSION.cookies.set("lang", "en", domain=".x.com")
    return _CFFI_SESSION


def transaction_client(auth: str, ct0: str):
    global _CLIENT_TRANSACTION, _CLIENT_TRANSACTION_TIME
    if _CLIENT_TRANSACTION is None or (time.time() - _CLIENT_TRANSACTION_TIME) > 2700:
        import bs4
        from x_client_transaction import ClientTransaction
        from x_client_transaction.utils import generate_headers, get_ondemand_file_url

        session = cffi_session(auth, ct0)
        ct_headers = generate_headers()
        home = session.get("https://x.com", headers=ct_headers, timeout=15)
        home.raise_for_status()
        home_resp = bs4.BeautifulSoup(home.content, "html.parser")
        ondemand_url = get_ondemand_file_url(response=home_resp)
        ondemand = session.get(ondemand_url, headers=ct_headers, timeout=15)
        ondemand.raise_for_status()
        _CLIENT_TRANSACTION = ClientTransaction(
            home_page_response=home_resp,
            ondemand_file_response=ondemand.text,
        )
        _CLIENT_TRANSACTION_TIME = time.time()
    return _CLIENT_TRANSACTION


def x_headers_for_url(auth: str, ct0: str, url: str, method: str = "GET") -> dict[str, str]:
    headers = build_headers(auth, ct0)
    try:
        ct = transaction_client(auth, ct0)
        path = urllib.parse.urlparse(url).path
        headers["X-Client-Transaction-Id"] = ct.generate_transaction_id(method=method, path=path)
    except Exception:
        # Helpful when available, but not worth printing auth-related failures.
        pass
    return headers


def extract_tweets(obj: Any) -> list[dict[str, Any]]:
    tweets: dict[str, dict[str, Any]] = {}

    def walk(x: Any):
        if isinstance(x, dict):
            legacy = x.get("legacy")
            rest_id = x.get("rest_id")
            if isinstance(legacy, dict) and (legacy.get("full_text") or legacy.get("text")) and rest_id:
                user = x.get("core", {}).get("user_results", {}).get("result", {}) if isinstance(x.get("core"), dict) else {}
                user_legacy = user.get("legacy", {}) if isinstance(user, dict) else {}
                tweets[str(rest_id)] = {
                    "id": str(rest_id),
                    "text": legacy.get("full_text") or legacy.get("text") or "",
                    "created_at": legacy.get("created_at"),
                    "screen_name": user_legacy.get("screen_name"),
                    "name": user_legacy.get("name"),
                    "followers": user_legacy.get("followers_count"),
                    "retweets": legacy.get("retweet_count"),
                    "likes": legacy.get("favorite_count"),
                    "replies": legacy.get("reply_count"),
                }
            tr = x.get("tweet_results")
            if isinstance(tr, dict):
                result = tr.get("result")
                if isinstance(result, dict):
                    walk(result)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return list(tweets.values())


def keyword_hits_for(text: str, keywords: list[str]) -> list[str]:
    low = " " + text.lower() + " "
    hits: list[str] = []
    for kw in keywords:
        if kw.strip() in low:
            hits.append(kw.strip())
    # Normalize short WL variants.
    if any(h in {"wl", "wl.", "wl:", "wl?"} for h in hits):
        hits = [h for h in hits if h not in {"wl.", "wl:", "wl?"}]
        if "wl" not in hits:
            hits.append("wl")
    return list(dict.fromkeys(hits))


def has_excluded_keyword(text: str, exclude_keywords: list[str]) -> bool:
    low = " " + (text or "").lower() + " "
    for kw in exclude_keywords:
        k = kw.strip().lower()
        if k == "wl":
            if re.search(r"(?<![a-z0-9])wl(?![a-z0-9])", low):
                return True
        elif k and k in low:
            return True
    return False


def score_tweet(t: dict[str, Any], keywords: list[str], mode: str) -> tuple[int, list[str], list[str]]:
    text = re.sub(r"\s+", " ", t.get("text") or "").strip()
    low = " " + text.lower() + " "
    hits = keyword_hits_for(text, keywords)
    red = []
    if any(w in low for w in SPAM_WORDS):
        red.append("spam/giveaway/drainer wording")
    if "0x" not in low and not re.search(r"https?://|\.xyz|\.io|\.app|opensea|transient|magiceden", low):
        red.append("no contract/link/site")
    score = 0
    score += 5 * len(hits)
    if mode == "wl" and any(h in {"allowlist", "whitelist", "white list", "wl"} for h in hits):
        score += 8
    if re.search(r"0x[a-fA-F0-9]{40}", text):
        score += 10
    if re.search(r"https?://|\.xyz|\.io|\.app|opensea|transient|magiceden", low):
        score += 6
    if "ethereum" in low or " eth" in low or "mainnet" in low:
        score += 5
    if "live" in low or "now" in low or "open" in low or "ready" in low:
        score += 3
    if red:
        score -= 8
    try:
        followers = int(t.get("followers") or 0)
        if followers >= 10000:
            score += 3
        elif followers >= 1000:
            score += 1
    except Exception:
        pass
    return score, hits, red


def search_query(query: str, auth: str, ct0: str) -> list[dict[str, Any]]:
    variables = {
        "rawQuery": query,
        "count": 20,
        "querySource": "typed_query",
        "product": "Latest",
    }
    features = {
        "rweb_video_screen_enabled": False,
        "profile_label_improvements_pcf_label_in_post_enabled": True,
        "rweb_tipjar_consumption_enabled": False,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "premium_content_api_read_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
        "responsive_web_grok_analyze_post_followups_enabled": False,
        "responsive_web_jetfuel_frame": False,
        "responsive_web_grok_share_attachment_enabled": False,
        "articles_preview_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "responsive_web_grok_show_grok_translated_post": False,
        "responsive_web_grok_analysis_button_from_backend": False,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_enhance_cards_enabled": False,
    }
    params = urllib.parse.urlencode({
        "variables": json.dumps(variables, separators=(",", ":")),
        "features": json.dumps(features, separators=(",", ":")),
    })
    url = f"https://x.com/i/api/graphql/{SEARCH_QID}/SearchTimeline?{params}"
    session = cffi_session(auth, ct0)
    r = session.get(url, headers=x_headers_for_url(auth, ct0, url), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"SearchTimeline HTTP {r.status_code}")
    data = r.json()
    return extract_tweets(data)


def main() -> int:
    args = parse_args()
    cfg = MODE_CONFIG[args.mode]
    env = load_env()
    auth = env.get("X_AUTH_TOKEN")
    ct0 = env.get("X_CT0") or env.get("X_CSRF_TOKEN")
    if not auth or not ct0:
        print(json.dumps({"ok": False, "error": "missing_x_auth", "message": "X_AUTH_TOKEN/X_CT0 not configured"}))
        return 2
    state_path: Path = cfg["state"]
    state = load_state(state_path)
    seen = set(str(x) for x in state.get("seen_ids", [])) if not args.no_dedupe else set()
    seen_urls = set(str(x) for x in state.get("seen_urls", [])) if not args.no_dedupe else set()
    seen_fingerprints = set(str(x) for x in state.get("seen_fingerprints", [])) if not args.no_dedupe else set()
    batch_fingerprints: set[str] = set()
    all_items: dict[str, dict[str, Any]] = {}
    errors = []

    for query in cfg["queries"]:
        try:
            tweets = search_query(query, auth, ct0)
        except Exception as e:
            errors.append({"query": query, "error": f"{type(e).__name__}: {e}"})
            continue
        for t in tweets:
            tid = str(t.get("id") or "")
            if not tid or tid in seen:
                continue
            if has_excluded_keyword(t.get("text") or "", cfg.get("exclude_keywords", [])):
                continue
            recent_ok, age_hours, recent_reason = is_recent_this_month(t.get("created_at"), args.max_age_hours)
            if not recent_ok:
                continue
            fp = content_fingerprint(t)
            if fp in seen_fingerprints or fp in batch_fingerprints:
                continue
            score, hits, red = score_tweet(t, cfg["keywords"], args.mode)
            if score < 8 or not hits:
                continue
            sn = t.get("screen_name") or "i"
            t["url"] = f"https://x.com/{sn}/status/{tid}"
            if t["url"] in seen_urls:
                continue
            t["score"] = score
            t["keyword_hits"] = hits
            t["red_flags"] = red
            t["age_hours"] = round(age_hours, 2) if age_hours is not None else None
            t["fingerprint"] = fp
            t["query"] = query
            batch_fingerprints.add(fp)
            all_items[tid] = t
        time.sleep(0.7)

    ranked_candidates = sorted(
        all_items.values(),
        key=lambda x: (x.get("score", 0), -(x.get("age_hours") or 0)),
        reverse=True,
    )
    items = ranked_candidates[: max(1, args.limit)]
    if ranked_candidates and not args.no_dedupe:
        # Mark every candidate seen, not only delivered items, so cron does not
        # drip-feed older posts from the same search page every 10 minutes.
        state["seen_ids"] = [str(i["id"]) for i in ranked_candidates] + list(seen)
        state["seen_urls"] = [str(i.get("url") or "") for i in ranked_candidates if i.get("url")] + list(seen_urls)
        state["seen_fingerprints"] = [str(i.get("fingerprint") or "") for i in ranked_candidates if i.get("fingerprint")] + list(seen_fingerprints)
        state["last_run_at"] = int(time.time())
        state["mode"] = args.mode
        state["current_month_only"] = True
        state["max_age_hours"] = args.max_age_hours
        save_state(state_path, state)

    for item in items:
        item["text"] = re.sub(r"\s+", " ", item.get("text") or "").strip()[:500]

    print(json.dumps({
        "ok": True,
        "source": "x_authenticated_search",
        "mode": args.mode,
        "title": cfg["title"],
        "queries": cfg["queries"],
        "count": len(items),
        "items": items,
        "errors": errors[:5],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
