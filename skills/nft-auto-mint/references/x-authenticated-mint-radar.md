# Authenticated X NFT Mint Radar

Use this reference when the user asks to monitor X/Twitter for NFT mint alpha such as `free mint`, `allowlist`, `WL`, `whitelist`, `stealth mint`, `mint live`, or `FCFS`.

## Durable pattern

For recurring monitoring, prefer a **script-only cron job** over an LLM-driven cron:

- `no_agent=True` so the scheduler runs the script and delivers stdout verbatim.
- Keep `skills=[]` and no web/search toolsets for the cron job.
- Store X cookies in a private env file with mode `0600` (for example `~/.hermes/x-radar.env`) and never print them.
- Split outputs by Telegram topic when the user provides topic links.
- Use separate state files per radar category so dedupe for one category does not hide another category.

This keeps token usage near zero while still delivering useful alerts.

## Telegram topic target conversion

A Telegram internal topic URL like:

```text
https://t.me/c/2851937818/53949
```

maps to Hermes delivery target:

```text
telegram:-1002851937818:53949
```

Rule: prepend `-100` to the `/c/<id>/` chat id, and use the final path segment as the thread/topic id.

Examples:

```text
https://t.me/c/2851937818/37039  -> telegram:-1002851937818:37039
https://t.me/c/2851937818/53949  -> telegram:-1002851937818:53949
```

Always test with `send_message` before wiring a cron job.

## Authenticated X search implementation notes

Plain HTTP requests to X GraphQL can return `404` even when cookies are valid. The working pattern is:

1. Use `curl_cffi.Session(impersonate="chrome136")`.
2. Set cookies on `.x.com`: `auth_token`, `ct0`, and `lang=en`.
3. Include headers:
   - `Authorization: Bearer <public X bearer>`
   - `X-Csrf-Token: <ct0>`
   - `X-Twitter-Active-User: yes`
   - `X-Twitter-Auth-Type: OAuth2Session`
4. Generate `X-Client-Transaction-Id` using `x-client-transaction-id` from the X home page + ondemand JS file.
5. Scrape the current `SearchTimeline` query id from `https://x.com` → `main.<hash>.js`; X rotates it.

Useful dependency install:

```bash
python3 -m pip install 'curl_cffi>=0.7.0' 'x-client-transaction-id>=0.0.1' 'beautifulsoup4>=4.12.0'
```

## Recommended cron split

Use two no-agent cron jobs when the user wants different topics:

| Category | Keywords | Delivery |
|---|---|---|
| General mint radar | `free mint`, `allowlist`, `stealth mint`, `mint live`, `FCFS`, `0x` | general mint topic |
| WL radar | `WL`, `Allowlist`, `Whitelist`, `white list` | WL-specific topic |

Both should run every 10–15 minutes unless the user requests otherwise.

## Output rules

- Keep alerts short: top 3–5 items.
- Include source URL, trigger keyword, one-line summary, risk note, and next research step.
- Dedupe tweet IDs persistently.
- If there are no useful signals, either stay silent (best for watchdog-style cron) or send one short “no signal” line if the user asked for visible heartbeats.
- Never include cookies, auth tokens, private keys, mnemonics, or wallet secrets.
- Never execute/sign/broadcast on-chain actions from the radar; only research and dry-run next steps.
