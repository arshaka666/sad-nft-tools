# NFT radar Telegram formatting lessons

Use this reference when formatting X/Twitter NFT radar posts for Telegram topics.

## Topic routing
- FREE MINT / STEALTH MINT / LIVE MINT goes to the Live Mint topic only.
- WL / Allowlist / Whitelist / Early Access goes to the WL/Allowlist topic only.

## Mobile-readable spacing
Telegram mobile can visually collapse dense single-newline text into one paragraph. The user's preferred balance:
- Blank line between the header and each item.
- Blank line after the divider.
- Blank line between metadata lines (`🏷️`, `✅`/`⚡`, `📝`, `🔗`).
- Keep each metadata line itself compact; do not add blank lines after every small sub-bullet inside an already-short section.
- Keep links horizontal and compact, preferably one `[X Post](...)` link for X radar.

## WL / Allowlist / Early Access format
```markdown
🧾 WL / Allowlist Radar
Update 20:00 WIB • X

**1. @Project**
━━━━━━━━━━━━━━━━━━━━

🏷️ WL / Allowlist • ETH • FCFS

✅ Req: follow + like + RT/repost

📝 Short cleaned tweet text...

🔗 [X Post](https://x.com/i/status/...)
```

Rules:
- Include `Early Access` as a WL-mode signal/label when present.
- Extract project handle as title when possible.
- Extract lightweight requirements: follow, like, RT/repost, reply/comment, join/Discord.
- Avoid raw URL at the top of the item.

## FREE / STEALTH / LIVE mint format
```markdown
🚨 NFT Mint Radar
Update 20:04 WIB • X

**1. @Project**
━━━━━━━━━━━━━━━━━━━━

🏷️ Free mint • ETH • 0.0007 ETH

⚡ Info: FCFS • live now • schedule/phase • 111/wallet

⏰ June 22

📝 Short cleaned tweet text...

🔗 [X Post](https://x.com/i/status/...)
```

Rules:
- Use `⚡ Info` instead of `✅ Req` for general mint radar.
- Extract highlights like FCFS, live now, stealth, schedule/phase, holder phase, and wallet limit.
- Keep tweet text truncated and cleaned; do not dump long tweet text inline with the link.
