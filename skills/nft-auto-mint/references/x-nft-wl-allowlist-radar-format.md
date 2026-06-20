# X NFT WL / Allowlist Radar Formatting

Use this reference for the X/Twitter WL/Allowlist radar posts delivered to Telegram allowlist topics.

## User preference
- Keep Telegram posts readable on mobile: section spacing, but not huge gaps.
- Avoid raw long tweet dumps like `1. https://x.com/... WL / Allowlist ... long paragraph`.
- Show the X post as a single embedded link at the bottom of each item.
- Keep output concise and action-oriented.

## Preferred shape

```markdown
🧾 WL / Allowlist Radar
Update 19:54 WIB • X

**1. @ProjectHandle**
━━━━━━━━━━━━━━━━━━━━
🏷️ WL / Allowlist • ETH • free / cek gas
✅ Req: follow + like + RT/repost + reply/comment
⏰ Winners next Monday
📝 Short cleaned summary of the post, truncated before it becomes a wall of text.

🔗 [X Post](https://x.com/i/status/...)

**2. Project Name**
━━━━━━━━━━━━━━━━━━━━
🏷️ WL / Allowlist • FCFS
✅ Req: cek post
📝 Short summary...

🔗 [X Post](https://x.com/i/status/...)
```

## Extraction rules
- Title: prefer the first tagged project handle (`@ProjectHandle`). If no handle exists, infer a short project name from text; do not use the whole tweet as title.
- Meta line: include signal (`WL / Allowlist`, `Free mint`, `Stealth mint`), chain if obvious, mint price/free if obvious, and FCFS for allowlist posts.
- Requirements: detect and summarize `follow`, `like`, `RT/repost`, `reply/comment`, `join/Discord`; otherwise use `cek post`.
- Deadline: include if the tweet clearly says winners/ends/snapshot/date. Omit if uncertain.
- Summary: remove raw URLs, collapse whitespace, decode `&amp;`, strip repetitive giveaway labels, and truncate to about 240 characters.
- Links: use only `🔗 [X Post](...)` per item unless the source has trustworthy official project links.

## Cron routing
- WL/Allowlist/Whitelist output belongs in the LFY/Allowlist topic, not the FREE/STEALTH/LIVE mint topic.
- For the current setup this is `telegram:-1002851937818:53949`.

## Pitfalls
- Do not put the tweet URL at the beginning of the item title; Telegram makes the whole post look noisy.
- Do not paste the full tweet when it includes many requirements/hashtags; summarize the useful parts.
- Do not over-space every bullet; separate items and sections, but keep bullets within an item compact.