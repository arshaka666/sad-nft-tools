# 04 — Cara Operasi Harian Agent

## 1. Prinsip utama NFT/Web3 agent

Paket ini dipakai untuk radar, riset, dan eksekusi. Default cara kerja:

```text
inspect -> verify -> simulate/dry-run -> execute kalau scope aman -> audit hasil
```

Kemampuan utama:

- Radar NFT: FREE / STEALTH / LIVE mint, WL / Allowlist / Early Access, Waypoint HOT NFT.
- Auto mint contract: baca ABI/source, detect mint function, cek price/supply/limit, build calldata, gas strategy, kirim tx kalau wallet/RPC valid.
- SeaDrop / Seaport / OpenSea-style: validasi flow mint/claim/order, approval, value, recipient, dan tx integrity.
- Universal minter: OpenSea, Manifold, Zora, Thirdweb, SeaDrop, custom ERC-721/ERC-1155, mint URL, claim NFT.
- Auto fill WL: Google Form/custom backend/multi-page site, batch 100 wallet atau lebih, random username/comment/proof kalau diminta, audit CSV/JSON.
- Batch ops: banyak wallet/address, rate-limit, retry, resume-from-failure, ringkasan sukses/duplicate/fail.
- Web3 ops: contract read/write, holder/deployer/token checks, RPC fallback, airdrop check, monitoring on-chain.

## 2. Prinsip utama NFT radar

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

## 3. Format score Live Mint

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

## 4. Slash command penting di Telegram

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

## 5. Cara update keyword radar

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

## 6. Cara update format Telegram

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

## 7. Cara backup skill/script

```bash
ts=$(date +%Y%m%d_%H%M%S)
tar -czf ~/hermes-nft-agent-backup-$ts.tar.gz \
  ~/.hermes/skills/web3 \
  ~/.hermes/skills/social-media/xurl \
  ~/.hermes/scripts/*radar*
```

Jangan backup `.env`, token, cookies, wallet, seed phrase ke repo publik.

## 8. Cara debug cron

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

## 9. Best practice untuk group

- Jangan spam lebih dari 1–3 item per update.
- Jangan campur WL dengan live/free mint.
- Links horizontal, bukan raw URL panjang.
- Kalau data kurang, tulis `unknown` atau omit, jangan ngarang.
- Selalu tutup dengan `DYOR sebelum mint.`
- Jangan pernah suruh member connect wallet tanpa warning.
