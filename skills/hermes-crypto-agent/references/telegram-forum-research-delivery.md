# Telegram Forum Topic Delivery for NFT/Web3 Research

Use this when the user authorizes sending NFT/Ethereum research updates to a Telegram group/channel that uses forum topics, including recurring cron radar jobs for X/Twitter mint signals and Waypoint HOT NFT live mints.

## User format + anti-spam preferences

- Keep radar updates compact like a pinned note, not a verbose report.
- For Waypoint live mints, use the exact title `🔥 HOT NFT Live Mint`.
- Use WIB in headers: `Update <HH:MM> WIB • <source>`.
- Do not expose cron wrapper text such as `Cronjob Response`, job IDs, schedule metadata, or “to stop/manage this job” footer in delivered messages.
- Do not post raw long URLs; use embedded Markdown links such as `[Waypoint](...) • [OpenSea](...) • [Tx](...)`.
- Do not repeat the same collection, tweet/post, contract, or link. For cron/script jobs, persist seen tweet IDs, URLs, and content fingerprints; if nothing new remains, produce empty stdout for `no_agent=True` or exactly `[SILENT]` for agent cron jobs.
- Filter to collection/posting from the current month, and prioritize items that are newly active in the last minutes/hours. Avoid recycling old/high-count noise.
- For X radar, cap at 3 items and prefer a recency window like 72 hours unless the user asks otherwise.

## Why this matters

Telegram forum groups can reject sends to the bare chat ID with `Topic_closed` if the default/general topic is closed. For research notifications, route to a live topic instead of assuming `telegram:<chat_id>` is enough.

## Procedure

1. Discover available messaging targets first:
   - `send_message(action="list")`
   - Prefer the exact topic target returned by the adapter, e.g. `telegram:Group Name / topic 1 (group)`.
2. If you only have a numeric chat ID and the group is a forum, use the thread form when the topic ID is known:
   - `telegram:<chat_id>:<thread_id>`
3. Send one harmless test message before relying on the target for recurring research delivery.
4. If bare `telegram:<chat_id>` returns `Topic_closed`, do not retry the same bare target. Ask for/derive a live topic target and send there.
5. Never include wallet secrets, private keys, seed phrases, mnemonics, bot tokens, API keys, or raw credential file contents in research notifications.

## User-specific observed targets and routing rules

For this user’s NFT/Ethereum research updates, route by signal type. Category separation is strict: do not send everything to one topic.

| Signal type | Preferred target | Rule |
|---|---|---|
| FREE MINT, STEALTH MINT, STEALTH LAUNCH, LIVE MINT, MINT LIVE | `telegram:let's fucking yappers (LFY) / topic 37039 (group)` | This thread is ONLY for those categories. Exclude WL, Allowlist, Whitelist, and generic FCFS unless the post is explicitly also free/stealth/live mint. |
| WL, Allowlist, Whitelist | `telegram:let's fucking yappers (LFY) / topic 53949 (group)` | Never post these to topic 37039. |
| Waypoint HOT NFT live mint radar | `telegram:-1002851937818:54012` | Keep separate from general mint radar. |

The corresponding LFY group chat ID is:

```text
-1002851937818
```

Use named topic targets when available. If only numeric routing is exposed, use thread form `telegram:-1002851937818:<thread_id>` with `37039`, `53949`, or `54012` as appropriate. Always send a harmless test message after changing targets, and keep research notifications clean, concise, and free of shell placeholders or raw credential content.
