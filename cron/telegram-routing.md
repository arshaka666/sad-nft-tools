# Telegram routing template

Use these routes when installing the radar cron jobs. Replace chat/thread IDs for your own group.

```text
FREE / STEALTH / LIVE MINT thread: telegram:<chat_id>:<thread_id>
WL / Allowlist / Early Access thread: telegram:<chat_id>:<thread_id>
Waypoint HOT Live Mint thread: telegram:<chat_id>:<thread_id>
```

Recommended schedules:

```bash
hermes cron create 'every 10m' \
  --name 'X NFT Mint Radar — FREE/STEALTH/LIVE ONLY' \
  --script x_nft_mint_radar_general.sh \
  --no-agent \
  --deliver 'telegram:<chat_id>:<free_thread_id>'

hermes cron create 'every 10m' \
  --name 'X NFT WL/Allowlist/Early Access Radar' \
  --script x_nft_mint_radar_wl.sh \
  --no-agent \
  --deliver 'telegram:<chat_id>:<wl_thread_id>'

hermes cron create 'every 10m' \
  --name 'Waypoint HOT NFT Live Mint Radar' \
  --script waypoint_hot_mint_radar.sh \
  --no-agent \
  --deliver 'telegram:<chat_id>:<waypoint_thread_id>'
```
