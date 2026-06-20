# Waypoint HOT NFT Live Mint Radar

Use this reference when the user asks to monitor live/HOT NFT mints from Waypoint MintScan and deliver Telegram cron updates.

## Trigger
- User provides a Waypoint MintScan URL, e.g. `https://waypoint.tools/mintscan/#<address>`.
- User asks for "live mint", "HOT NFT", "free mint", or "yang lagi minting" monitoring.

## Data source pattern
1. Use `web_extract` on the Waypoint MintScan URL. Direct API/WebSocket access may be Cloudflare-protected, so prefer the page extraction when available.
2. Parse two sections:
   - `Mints Overview`: project name, mint count, `Mintable`/airdrop marker.
   - `Live Mints` / `Recent Mints`: project name, price/free marker, recipient, age, and Etherscan TX links.
3. Rank at most 3 items. Prioritize:
   - `🆓 Free` / `0 ETH`
   - high mint count in the active window
   - `Mintable`
   - recent tx age in seconds/minutes
4. If data is weak/noisy, send only 1–2 items or stay silent/short. Do not spam long lists.

## OpenSea, market demand, X/website, deployer, and holder enrichment
- TX: use the latest matching `https://etherscan.io/tx/...` from the live/recent mint rows for that collection.
- OpenSea: use Waypoint/Blockscout/OpenSea URL only when clearly present/relevant. If uncertain, omit instead of writing "not found".
- Market demand is mandatory for free-mint analysis: pull OpenSea stats when a slug exists and show volume, sales, floor price, and whether collection offers are enabled. Do **not** treat floor price as demand; volume/sales/offers matter more than FP.
- X/Twitter: include project X only if Waypoint/OpenSea returns a plausible handle/URL. If none exists, say `No X found` and add `Notes: no X` instead of inventing a link.
- Website: if Waypoint returns `website: null`, fallback to OpenSea collection metadata (`project_url`) before saying none. Normalize bare domains to `https://...`. Do not invent or random-search sites when missing.
- Website: include `[Website](...)` only if Waypoint returns a plausible website URL; normalize bare domains to `https://...`. If Waypoint returns `website: null`, use OpenSea collection metadata (`project_url`) and only then a quick web-search fallback by project name before saying website none. Do not invent links.
- Market demand: for free/live mints, do **not** score from floor price alone. Pull OpenSea stats when possible and show volume, sales, floor price, and whether collection offers are enabled. Volume/sales/offers are the real demand signal; FP is only context.
- Deployer/creator: enrich from Blockscout `/api/v2/addresses/<contract>` using `creator_address_hash` and `creation_transaction_hash`; link `DeployTx` when available. Also check the deployer/dev wallet's holdings of the same NFT and flag hoarding.
- Holders: enrich from Blockscout token/holders endpoints; include holder count, unique minters, top-holder percentage, and deployer/dev holding percentage when available. If one wallet or dev holds a large supply share, reduce score and note possible fomo/hoard risk.
- Contract: include verification/proxy/implementation hints (e.g. `verified • ERC721SeaDropCloneable • eip1167`) so the group sees basic project quality before minting.
- Never invent supply, contract address, OpenSea slug, X link, website, deployer, holder counts, market stats, or TX links. Use `?` for unknown fields or omit links.

## User-preferred Telegram format
The user strongly prefers compact, embedded-link formatting, not raw URL blocks.

Use this shape:

```markdown
🔥 HOT NFT Live Mint
Update 01:39 WIB • Waypoint

**1. TaskBarItem**
━━━━━━━━━━━━━━━━━━━━

🟢 **Mint Info**
• Mint: 1 mint / 1 tx
• Price: 0 ETH
• Supply: 3 / ?
• Status: New collection • 46m old • Mintable • Live now

📊 **Score**
• 62/100 🟡 Medium
• Reason: hot mint flow, free mint, verified, real demand

🔎 **Project Check**
• Social: X linked • website linked
• Market: Vol 0.0307 ETH • 188 sales • FP 0.000199 ETH • offers enabled
• Contract: verified • ERC721SeaDropCloneable • eip1167
• Deployer: 0x1234…abcd
• Dev wallet: 2 NFT • 0.2%
• Holders: 278 holders • 151 minters • top 10.2%
• Notes: basic checks ok

🔗 **Links**
[Waypoint](https://waypoint.tools/mintscan/#...) • [OpenSea](https://opensea.io/collection/...) • [Website](https://project.example) • [X](https://x.com/...) • [Contract](https://etherscan.io/address/...) • [Tx](https://etherscan.io/tx/...) • [DeployTx](https://etherscan.io/tx/...)

DYOR sebelum mint.
```

Rules:
- Keep the title `🔥 HOT NFT Live Mint`.
- Use WIB (`Asia/Jakarta`) in the header, not UTC.
- Use embedded Markdown links: `[Waypoint](...) • [OpenSea](...) • [Tx](...)`.
- Avoid raw `OS: https://...` / `TX: https://...` lines.
- Omit missing links instead of adding clutter.
- Keep descriptions short and spaced; avoid dense/numpuk blocks.
- For Waypoint HOT posts, use balanced mobile-readable spacing: blank lines **between sections only**, single newlines inside each section. Too little spacing collapses into dense `·` text in Telegram; too much spacing makes posts too tall.
- Use section headings with blank lines: `Mint Info`, `Score`, `Project Check`, `Links`.
- Keep links horizontal on one line using ` • ` separators, not one link per line.
- For `/watch` contract results, default to a short summary only: score, mint activity, verified/deployer/holder/social signals, key warning, horizontal links, and a one-line quick take. Full analysis only when the user asks for detail.
- If Waypoint/OpenSea returns `website: null`, do a quick web-search fallback by project name before saying Website none; do not invent links.
- For X/Twitter WL/Allowlist radar formatting, see `references/x-nft-wl-allowlist-radar-format.md` and keep posts as short action cards with a single `X Post` link.
- End with `DYOR sebelum mint.`

## Cron delivery notes
- If using Hermes cron, set `cron.wrap_response=false` when the user wants clean channel posts without the `Cronjob Response: ... (job_id: ...)` wrapper.
- For script-only radars, prefer `no_agent=True` and empty stdout on no-signal runs so nothing is delivered.
- For Waypoint summarization, prefer the persistent script `/root/.hermes/scripts/waypoint_hot_mint_radar.sh` as a `no_agent=True` cron. It connects to Waypoint WebSocket/API, dedupes by collection address/name in `~/.hermes/waypoint-hot-mint-radar-state.json`, filters strictly to collections first seen/deployed in the current calendar month and preferably within the last 72 hours, and prints empty stdout when the same collection is still hot. Avoid LLM-only Waypoint cron for recurring posts because it may repeat the same collection when TX changes or let old collections through.

## Safety
- This is research/radar only.
- Do not sign, broadcast, mint, send transactions, or claim a mint is safe.
- Always frame as a live signal and require DYOR before connecting a wallet.