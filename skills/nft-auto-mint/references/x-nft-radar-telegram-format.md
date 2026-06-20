# X/Twitter + Live-Mint Radar Telegram Format

Use this when sending NFT/Web3 radar updates from cron jobs, X/Twitter scans, Waypoint MintScan, CatchMint-style live mint sources, or similar monitoring feeds.

## User-preferred format

The user explicitly corrected the radar format multiple times: keep it clean, readable, and not spammy. Avoid raw URL walls and bulky field lists.

### Default X/Twitter radar shape

```text
🚨 NFT Mint Radar

1. https://x.com/i/status/...
Free mint • ETH • free/cek gas
Short description in one or two lines.

2. https://x.com/i/status/...
WL / Allowlist • ETH • FCFS
Short description in one or two lines.
```

Rules:
- Put the source link first for each item.
- Put the short description underneath the link.
- Avoid bulky field lists such as `Risk note`, `Next`, `Confidence`, long checklists, or many bullets unless the user asks for deep research.
- Cap routine cron alerts to top 3 items; if data is weak/noisy, send only 1–2 items.
- If there is no new qualified signal, prefer empty stdout for `no_agent=True` cron jobs so delivery is silent and the Telegram topic is not spammed.
- Keep wording member-friendly: one concise title, then numbered items.
- Do not include raw shell placeholders, debug output, secrets, cookies, tokens, private keys, mnemonics, or wallet passwords.

## HOT live mint format

For live-mint sources like Waypoint MintScan, the user prefers a compact “pinned-style” digest with embedded Markdown links, not raw URL lines.

Preferred title:

```text
🔥 HOT NFT Live Mint
```

Preferred shape:

```text
🔥 HOT NFT Live Mint
Update 01:39 WIB • Waypoint

1. TaskBarItem
1 mint / 1 tx • 0 ETH • Supply 3 / ?
New this month • 19 Jun
[Waypoint](https://waypoint.tools/mintscan/#...) • [OpenSea](https://opensea.io/collection/...) • [Tx](https://etherscan.io/tx/...)

DYOR sebelum mint.
```

Rules:
- Keep the title `🔥 HOT NFT Live Mint`.
- Include update time in WIB and source name when possible.
- Use embedded Markdown links: `[Waypoint](...) • [OpenSea](...) • [Tx](...)`.
- Do **not** print `OS: https://...` / `TX: https://...` raw URL lines for this format.
- Omit missing links instead of writing `OS: belum ketemu`.
- Prefer `0 ETH` / `Free` items and high live mint counts.
- Include only compact facts: `mints / tx • price • Supply minted/max` plus one short status/date line if known.
- End with `DYOR sebelum mint.`.

## Cron delivery wrapper

For user-facing Telegram radar cron jobs, the user does **not** want the scheduler wrapper/header/footer:

```text
Cronjob Response: ...
(job_id: ...)
-------------
To stop or manage this job...
```

Set clean delivery globally or ensure it is already set:

```bash
hermes config set cron.wrap_response false
```

Then verify `cron.wrap_response = false` in `~/.hermes/config.yaml` if needed. This is especially important for group/topic posts because the wrapper makes radar updates look spammy and unpolished.

## Routing convention from this user

- Free mint / allowlist / stealth mint / mint live NFT radar: `telegram:-1002851937818:37039`
- WL / Allowlist / Whitelist-specific radar: `telegram:-1002851937818:53949`
- HOT live mint radar from Waypoint MintScan: `telegram:-1002851937818:54012`

## Script-only cron pattern

For recurring X/Twitter radar jobs, prefer `no_agent=True` plus a script that prints the exact Telegram message. This avoids token usage and prevents LLM verbosity drift.

Recommended behavior:
- Dedupe seen tweet/project IDs in a mode-specific state file.
- Limit output to top 3.
- Empty stdout when no new signal.
- Use the clean `link first, short description below` format for X/Twitter radar.
- Use the compact embedded-link `🔥 HOT NFT Live Mint` format for live mint dashboards.

## Waypoint MintScan notes

Waypoint MintScan pages can expose useful data through page extraction even when direct terminal/API/WebSocket access hits Cloudflare or bot protection. Durable pattern:
- Use `web_extract` on the Waypoint MintScan URL for snapshot data.
- Parse `Mints Overview` for hot collections, mint counts, and `Mintable` status.
- Parse `Live Mints` / `Recent Mints` for price/free status and one recent Etherscan tx.
- Use a quick web search for `OpenSea collection <collection name> NFT` only when an OpenSea link improves the post; if uncertain, omit it.
- This is research/radar only — never sign, broadcast, or execute transactions from a cron alert.
