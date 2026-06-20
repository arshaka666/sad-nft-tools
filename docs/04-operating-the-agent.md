# 04 — Cara Operasi Harian Agent

## 1. Prinsip utama NFT radar

Jangan nilai NFT free mint dari floor price saja.

Checklist yang dipakai:

```text
Market demand: volume, sales, offers/bids
Holder distribution: top holder %, unique holders, minters
Dev/deployer: wallet deployer pegang berapa supply
Social: website, X, Discord
Contract: verified, type/proxy, suspicious pattern
Mint signal: free, live, stealth, FCFS, schedule
```

## 2. Format score Live Mint

Score tidak boleh tinggi hanya karena:

- free mint
- mint rame
- FP tinggi
- contract verified

Score naik kalau:

- volume/sales ada
- offers enabled / real demand ada
- holder spread sehat
- dev wallet tidak nimbun
- website/X ada
- deployer jelas

Score turun kalau:

- volume 0 / sales 0
- no website + no X
- top holder terlalu besar
- dev wallet nimbun
- contract unverified

## 3. Slash command penting di Telegram

```text
/watch <contract_or_link>
```

Untuk analisis ringkas NFT contract/mint.

Output default harus singkat:

```text
🔥 PROJECT — Watch
Score: xx/100
Free mint/live mint • supply
Market: volume/sales/offers
Holders/top holder/dev wallet
Website/X/social
Links horizontal
Quick take satu baris
```

Full analysis hanya kalau diminta.

## 4. Cara update keyword radar

Edit:

```bash
nano ~/.hermes/scripts/x_nft_mint_radar.py
```

Bagian penting:

```python
MODE_CONFIG = {
  "general": {...},
  "wl": {...},
}
```

Untuk WL radar, keyword yang sudah dipakai:

```text
WL
Allowlist
Whitelist
White list
Early Access
```

Setelah edit:

```bash
python3 -m py_compile ~/.hermes/scripts/x_nft_mint_radar.py
```

## 5. Cara update format Telegram

Edit:

```bash
nano ~/.hermes/scripts/x_nft_mint_radar_format.py
nano ~/.hermes/scripts/waypoint_hot_mint_radar.py
```

Test:

```bash
python3 -m py_compile ~/.hermes/scripts/x_nft_mint_radar_format.py ~/.hermes/scripts/waypoint_hot_mint_radar.py
~/.hermes/scripts/x_nft_mint_radar_format.py --mode general --limit 2 --no-dedupe
~/.hermes/scripts/x_nft_mint_radar_format.py --mode wl --limit 2 --no-dedupe
~/.hermes/scripts/waypoint_hot_mint_radar.py --preview --limit 2 --listen-seconds 8
```

## 6. Cara backup skill/script

```bash
ts=$(date +%Y%m%d_%H%M%S)
tar -czf ~/hermes-nft-agent-backup-$ts.tar.gz \
  ~/.hermes/skills/web3 \
  ~/.hermes/skills/social-media/xurl \
  ~/.hermes/scripts/*radar*
```

Jangan backup `.env`, token, cookies, wallet, seed phrase ke repo publik.

## 7. Cara debug cron

List job:

```bash
hermes cron list
```

Run job manual:

```bash
hermes cron run <job_id>
```

Lihat output terakhir:

```bash
ls -lah ~/.hermes/cron/output/
```

Cek logs gateway:

```bash
tail -100 ~/.hermes/logs/gateway.log
```

## 8. Best practice untuk group

- Jangan spam lebih dari 1–3 item per update.
- Jangan campur WL dengan live/free mint.
- Links horizontal, bukan raw URL panjang.
- Kalau data kurang, tulis `unknown` atau omit, jangan ngarang.
- Selalu tutup dengan `DYOR sebelum mint.`
- Jangan pernah suruh member connect wallet tanpa warning.
