#!/usr/bin/env python3
"""Format x_nft_mint_radar.py JSON into clean Telegram reports.

User preference:
- readable mobile Telegram formatting
- no long raw one-paragraph dumps
- horizontal links
- concise actionable WL/mint entries
"""
from __future__ import annotations
import argparse
import os
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RADAR = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes'))) / 'scripts' / 'x_nft_mint_radar.py'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Format authenticated X NFT radar output')
    parser.add_argument('--mode', choices=['general', 'wl'], default='general')
    parser.add_argument('--limit', type=int, default=3)
    parser.add_argument('--max-age-hours', type=float, default=72.0)
    parser.add_argument('--no-dedupe', action='store_true')
    return parser.parse_args()


def clean_text(text: str, n: int = 240) -> str:
    text = re.sub(r'https?://\S+', '', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('&amp;', '&')
    # Remove repeated giveaway fluff but keep core instructions readable.
    text = re.sub(r'(?i)\b(giveaway time|whitelist giveaway)\b[:!\s-]*', '', text).strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + '…'


def signal_label(mode: str, hits: list[str], text: str) -> str:
    low = (text or '').lower()
    hit = ' '.join(hits).lower()
    if 'early access' in hit or 'early access' in low:
        return 'Early Access'
    if mode == 'wl' or any(k in hit or k in low for k in ['allowlist', 'whitelist', 'white list', ' wl']):
        return 'WL / Allowlist'
    if 'stealth mint' in low or 'stealth launch' in low:
        return 'Stealth mint'
    if 'free mint' in low or 'free' in low:
        return 'Free mint'
    if 'mint live' in low or 'live mint' in low:
        return 'Live mint'
    return 'NFT mint signal'


def args_mode_allows_fcfs(mode: str) -> bool:
    return mode == 'wl'


def chain_label(text: str) -> str | None:
    low = (text or '').lower()
    if 'hedera' in low or ' hbar' in f' {low} ':
        return 'Hedera'
    if 'solana' in low or ' sol ' in f' {low} ':
        return 'Solana'
    if 'base' in low:
        return 'Base'
    if 'polygon' in low or 'matic' in low:
        return 'Polygon'
    if 'ethereum' in low or ' eth' in f' {low} ' or 'mainnet' in low:
        return 'ETH'
    return None


def mint_cost_label(text: str) -> str | None:
    low = (text or '').lower()
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:eth|Ξ)', text or '', re.I)
    if m:
        return f'{m.group(1)} ETH'
    if 'free mint' in low or re.search(r'\bfree\b', low):
        return 'free / cek gas'
    return None


def short_meta(text: str, hits: list[str], mode: str) -> str:
    bits = [signal_label(mode, hits, text)]
    ch = chain_label(text)
    if ch:
        bits.append(ch)
    cost = mint_cost_label(text)
    if cost:
        bits.append(cost)
    if args_mode_allows_fcfs(mode) and 'fcfs' in (text or '').lower():
        bits.append('FCFS')
    return ' • '.join(dict.fromkeys(bits))


def project_name(text: str) -> str:
    text = text or ''
    # Prefer tagged project handles when present.
    handles = re.findall(r'@([A-Za-z0-9_]{2,15})', text)
    if handles:
        # Skip obvious personal/giveaway cohost second handles only if first looks project-like.
        return '@' + handles[0]
    m = re.search(r'(?i)(?:upcoming|from|for)\s+([A-Z][A-Za-z0-9_.-]{2,}(?:\s+NFT)?)', text)
    if m:
        return m.group(1).strip()
    words = clean_text(text, 80).split()
    return ' '.join(words[:4]) if words else 'Unknown project'


def requirements(text: str) -> str:
    low = (text or '').lower()
    req = []
    if 'follow' in low:
        req.append('follow')
    if 'like' in low:
        req.append('like')
    if 'retweet' in low or ' repost' in f' {low} ' or ' rt ' in f' {low} ':
        req.append('RT/repost')
    if 'reply' in low or 'comment' in low or 'drop' in low:
        req.append('reply/comment')
    if 'join' in low or 'discord' in low:
        req.append('join/Discord')
    if not req:
        return 'cek post'
    return ' + '.join(dict.fromkeys(req))


def deadline_hint(text: str) -> str | None:
    text = text or ''
    m = re.search(r'(?i)(winners?\s+(?:next\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|today|tomorrow)|ends?\s+[^.!\n]{3,40}|snapshot\s+[^.!\n]{3,40}|june\s+\d{1,2}|jul\w*\s+\d{1,2}|\d{1,2}:\d{2}\s*(?:am|pm)\s*utc)', text)
    return m.group(1).strip() if m else None


def mint_highlights(text: str) -> str:
    low = (text or '').lower()
    bits: list[str] = []
    if 'fcfs' in low:
        bits.append('FCFS')
    if 'public mint live' in low or 'mint live' in low or 'live mint' in low:
        bits.append('live now')
    if 'stealth' in low:
        bits.append('stealth')
    if 'schedule' in low or 'phase' in low:
        bits.append('schedule/phase')
    if 'holder' in low:
        bits.append('holder phase')
    m = re.search(r'\b\d+\s*/\s*wallet\b', text or '', re.I)
    if m:
        bits.append(m.group(0).replace(' ', ''))
    return ' • '.join(dict.fromkeys(bits)) if bits else 'cek post'


def format_item(i: int, item: dict, mode: str) -> str:
    url = item.get('url') or '-'
    text = item.get('text') or ''
    hits = item.get('keyword_hits') or []
    title = project_name(text)
    deadline = deadline_hint(text)

    lines = [
        f'**{i}. {title}**',
        '━━━━━━━━━━━━━━━━━━━━',
        '',
        f'🏷️ {short_meta(text, hits, mode)}',
        '',
    ]
    if mode == 'wl':
        lines.append(f'✅ Req: {requirements(text)}')
        if deadline:
            lines.extend(['', f'⏰ {deadline}'])
    else:
        lines.append(f'⚡ Info: {mint_highlights(text)}')
        if deadline:
            lines.extend(['', f'⏰ {deadline}'])

    lines.extend([
        '',
        f'📝 {clean_text(text, 220 if mode == "general" else 240)}',
        '',
        f'🔗 [X Post]({url})',
    ])
    return '\n'.join(lines)


def main() -> int:
    args = parse_args()
    limit = min(max(args.limit, 1), 3)
    cmd = [
        sys.executable,
        str(RADAR),
        '--mode', args.mode,
        '--limit', str(limit),
        '--max-age-hours', str(args.max_age_hours),
    ]
    if args.no_dedupe:
        cmd.append('--no-dedupe')

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        print(f'Radar error: script exit {proc.returncode}')
        return proc.returncode
    try:
        data = json.loads(proc.stdout)
    except Exception as e:
        print(f'Radar error: JSON parse failed: {type(e).__name__}')
        return 1
    if not data.get('ok'):
        print(f"Radar error: {data.get('message') or data.get('error')}")
        return 1

    items = data.get('items') or []
    if not items:
        # Empty stdout = silent cron delivery; avoids spam.
        return 0

    title = '🧾 WL / Allowlist Radar' if args.mode == 'wl' else '🚨 NFT Mint Radar'
    update_time = datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%H:%M WIB')
    sections = [f'{title}\nUpdate {update_time} • X']
    for i, item in enumerate(items[:limit], 1):
        sections.append(format_item(i, item, args.mode))
    print('\n\n'.join(sections))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
