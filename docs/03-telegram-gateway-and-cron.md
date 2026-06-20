# 03 — Telegram Gateway dan Cron Radar

Panduan ini untuk menjalankan agent di Telegram dan mengirim radar otomatis ke group/topic.

## 1. Setup Telegram gateway

Jalankan wizard Hermes:

```bash
hermes gateway setup
```

Pilih Telegram, lalu ikuti instruksi bot token dari BotFather.

Setelah selesai:

```bash
hermes gateway run
```

Kalau sudah jalan, install sebagai service:

```bash
hermes gateway install
hermes gateway start
hermes gateway status
```

## 2. Tambahkan bot ke group

1. Add bot Hermes ke group Telegram.
2. Jadikan admin kalau perlu kirim ke topic/forum.
3. Kalau group pakai topic, buka topic yang mau dipakai.
4. Kirim pesan test ke topic.
5. Dari topic itu, jalankan:

```text
/sethome
```

Atau catat target manual dengan format:

```text
telegram:<chat_id>:<thread_id>
```

Contoh target topic:

```text
telegram:-1001234567890:54012
```

## 3. Rekomendasi routing topic

Pisahkan radar biar tidak campur:

```text
FREE / STEALTH / LIVE MINT      -> thread khusus live/free mint
WL / Allowlist / Early Access   -> thread WL sendiri
Waypoint HOT NFT Live Mint      -> thread live mint/high-signal sendiri
```

## 4. Buat cron script-only

Script-only artinya Hermes tidak pakai LLM tiap tick. Script jalan, stdout dikirim ke Telegram. Kalau tidak ada output, cron silent.

### FREE / STEALTH / LIVE MINT

```bash
hermes cron create 'every 10m' \
  --name 'X NFT Mint Radar — FREE/STEALTH/LIVE ONLY' \
  --script x_nft_mint_radar_general.sh \
  --no-agent \
  --deliver 'telegram:<chat_id>:<free_thread_id>'
```

### WL / Allowlist / Early Access

```bash
hermes cron create 'every 10m' \
  --name 'X NFT WL/Allowlist/Early Access Radar' \
  --script x_nft_mint_radar_wl.sh \
  --no-agent \
  --deliver 'telegram:<chat_id>:<wl_thread_id>'
```

### Waypoint HOT NFT Live Mint

```bash
hermes cron create 'every 10m' \
  --name 'Waypoint HOT NFT Live Mint Radar' \
  --script waypoint_hot_mint_radar.sh \
  --no-agent \
  --deliver 'telegram:<chat_id>:<waypoint_thread_id>'
```

## 5. Cek cron

```bash
hermes cron list
hermes cron status
```

Run manual:

```bash
hermes cron run <job_id>
```

Pause/resume:

```bash
hermes cron pause <job_id>
hermes cron resume <job_id>
```

## 6. Test script manual

```bash
~/.hermes/scripts/x_nft_mint_radar_general.sh
~/.hermes/scripts/x_nft_mint_radar_wl.sh
~/.hermes/scripts/waypoint_hot_mint_radar.sh
```

Kalau tidak ada output, itu normal: berarti tidak ada signal baru atau sudah dedupe.

Preview tanpa ganggu dedupe:

```bash
~/.hermes/scripts/x_nft_mint_radar_format.py --mode general --limit 2 --no-dedupe
~/.hermes/scripts/x_nft_mint_radar_format.py --mode wl --limit 2 --no-dedupe
~/.hermes/scripts/waypoint_hot_mint_radar.py --preview --limit 2 --listen-seconds 8
```

## 7. Format output yang dipakai

### Waypoint HOT NFT

Cek:

- score
- market volume/sales/offers, bukan FP doang
- holder concentration
- dev/deployer wallet holdings
- website/X/Discord
- contract verified/type

### WL / Allowlist / Early Access

Cek:

- project/handle
- category
- chain/cost
- requirements
- short tweet summary
- X post link

### FREE / STEALTH / LIVE MINT

Cek:

- signal type
- chain/price
- FCFS/live/stealth/schedule/wallet-limit
- short tweet summary
- X post link

## 8. Troubleshooting

### Cron tidak kirim apa-apa

Normal kalau stdout kosong. Script dibuat silent saat tidak ada signal baru.

### X radar error auth

Cek file:

```bash
ls -l ~/.hermes/x-radar.env
```

Jangan print token ke chat. Isi ulang manual kalau expired.

### Telegram salah topic

Cek job:

```bash
hermes cron list
```

Edit deliver target:

```bash
hermes cron edit <job_id>
```

### Format berubah tidak masuk

Restart gateway:

```bash
hermes gateway restart
```

Atau tunggu cron next tick.
