# Hermes NFT Agent Skills

Skill + script pack untuk bikin **Hermes AI Agent** yang bisa monitor, riset, dan eksekusi workflow NFT/Web3 dengan output rapi ke Telegram group/topic.

Paket ini bukan cuma radar. Ini kumpulan skill operasional yang bisa dipakai untuk:

- **NFT mint radar** — Waypoint HOT NFT, X/Twitter FREE / STEALTH / LIVE mint, WL / Allowlist / Early Access signal.
- **Auto mint dari contract** — baca ABI/source, detect mint function, cek supply/price/limit, simulasi tx, build calldata, gas strategy, kirim mint tx kalau wallet/RPC tersedia.
- **SeaDrop / Seaport / OpenSea-style flow** — referensi flow mint/claim/fulfill order, marketplace contract interaction, approval/value check, dan tx integrity.
- **Universal minter** — pola mint untuk OpenSea, Manifold, Zora, Thirdweb, SeaDrop, custom ERC-721/ERC-1155, claim NFT, dan mint URL.
- **Auto fill WL / allowlist** — reverse engineer form/site, submit Google Form/backend custom, batch 100 wallet atau lebih, random username/comment/proof kalau diminta, dan simpan audit CSV/JSON.
- **Batch multi-wallet ops** — queue banyak wallet/address, rate-limit, retry, resume-from-failure, dan ringkasan sukses/duplicate/fail.
- **Web3 ops** — contract read/write, RPC fallback, holder/deployer/token check, airdrop check, wallet ops, bridge/swap/DeFi pattern, dan monitoring on-chain.
- **NFT research** — contract verification, deployer/dev wallet, holder concentration, real demand, volume/sales/offers, social/website/X/Discord, mint risk, dan warning singkat.
- **Telegram delivery** — cron script-only hemat token, routing ke topic berbeda, format horizontal link, dan update singkat yang gampang dibaca.

Fokus paket ini bukan cuma “mint rame” atau “floor price tinggi”, tapi juga:

- volume / sales / offers
- holder concentration
- dev/deployer wallet holdings
- contract verification
- mint function / ABI / calldata sanity check
- supply, price, wallet limit, allowlist gating
- marketplace/order flow seperti Seaport kalau relevan
- website / X / Discord/social
- score ringkas dan warning yang enak dibaca di Telegram

## Isi repo

```text
skills/      Hermes skills yang bisa di-copy ke ~/.hermes/skills/
scripts/     Radar scripts untuk cron no-agent mode
cron/        Template routing Telegram topic/thread
docs/        Tutorial install dan setup step-by-step
install/     Installer lokal
.github/     GitHub Actions validation workflow
```

## Quick start untuk member

### 1. Install Hermes Agent

Linux / macOS / WSL:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc
hermes setup
hermes doctor
```

Test dulu:

```bash
hermes chat -q "Halo, jawab singkat."
```

### 2. Clone repo skill ini

```bash
git clone <REPO_URL>
cd hermes-nft-agent-skills
```

Kalau kamu dapat ZIP, pakai:

```bash
unzip hermes-nft-agent-skills.zip
cd hermes-nft-agent-skills
```

### 3. Install skill + script

```bash
bash install/install.sh
```

Cek:

```bash
hermes skills list | grep -E 'nft|web3|xurl|polymarket|blogwatcher|hermes-agent|batch|universal'
python3 -m py_compile scripts/x_nft_mint_radar.py scripts/x_nft_mint_radar_format.py scripts/waypoint_hot_mint_radar.py
```

### 4. Pakai skill di Hermes

Di chat Hermes:

```text
/skill nft-auto-mint
/skill universal-minter
/skill nft-wl-filler
/skill web3-ops
/skill batch-ops
/skill xurl
```

Contoh request radar / research:

```text
/watch 0xContractAddress
```

```text
Analisis mint NFT ini: <link mint / OpenSea / contract>
Cek score, holder concentration, deployer wallet, contract, market demand, website/X, dan warning.
```

Contoh request auto mint contract:

```text
Mint NFT dari contract ini: 0xContractAddress
Cek ABI/source, mint function, price, max supply, wallet limit, simulate dulu, lalu eksekusi kalau aman.
```

Contoh request SeaDrop / Seaport / marketplace-style:

```text
Cek mint/claim/listing NFT ini dari OpenSea/SeaDrop/Seaport flow.
Validasi order/contract/value/approval, simulate, lalu siapkan tx kalau aman.
```

Contoh request auto fill WL batch 100 wallet:

```text
Isi WL form/site ini pakai 100 wallet.
Reverse engineer field/backend, generate username/comment/proof random kalau perlu, submit batch, lalu kasih audit CSV/JSON.
```

### 5. Setup Telegram gateway + cron radar hemat token

```bash
hermes gateway setup
hermes gateway install
hermes gateway start
hermes gateway status
```

Lalu buat cron script-only sesuai target topic Telegram kamu:

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

## Skill utama

| Skill | Fungsi |
|---|---|
| `nft-auto-mint` | Eksekusi NFT mint: detect contract/ABI, mint function, Thirdweb/SeaDrop/custom ERC-721/ERC-1155, EIP-1559 gas, simulation, multi-wallet, tx integrity |
| `universal-minter` | Universal NFT minter untuk OpenSea, Manifold, Zora, SeaDrop, mint URL, claim NFT, contract mint, auto gas |
| `nft-wl-filler` | Auto fill WL/allowlist: Google Form, custom backend, multi-page forms, batch 100 wallet, random X username/comment/proof, audit CSV/JSON |
| `batch-ops` | Batch operation: parallel exec, queue banyak wallet/address, rate-limit, retry, resume-from-failure, summary sukses/duplicate/fail |
| `web3-ops` | On-chain ops: RPC fallback, contract read/write, holder/deployer/token checks, mass wallets, airdrop check, mint ops |
| `hermes-crypto-agent` | Toolkit Web3 multi-chain: wallet, swap, bridge, DeFi, NFT buy/mint, monitoring, smart money/whale/deployer tracking |
| `xurl` | X/Twitter CLI workflow: search, post, DM, media, authenticated radar, social signal collection |
| `polymarket` | Query market Polymarket: market, prices, orderbook, history |
| `blogwatcher` | Monitor RSS/Atom/blog feed untuk project/news/research signal |
| `hermes-agent` | Hermes setup/config/gateway/cron/tools reference |

## Capability map

| Kebutuhan | Skill yang dipakai | Output |
|---|---|---|
| Cari free/stealth/live mint terbaru | `xurl`, `nft-auto-mint`, script radar | Telegram alert singkat + link |
| Cari WL/Allowlist/Early Access | `xurl`, `nft-wl-filler`, script radar | Telegram alert WL terpisah |
| Analisis contract NFT | `web3-ops`, `nft-auto-mint`, `hermes-crypto-agent` | Score, warning, holder/deployer/social check |
| Mint langsung dari contract | `nft-auto-mint`, `universal-minter`, `web3-ops` | Simulasi + calldata + tx hash kalau dieksekusi |
| SeaDrop/OpenSea/Seaport-style mint/claim/order | `universal-minter`, `nft-auto-mint`, `web3-ops` | Validasi flow/value/approval + tx plan |
| Isi WL 100 wallet | `nft-wl-filler`, `batch-ops` | Audit CSV/JSON sukses/duplicate/fail |
| Batch banyak wallet/address | `batch-ops`, `web3-ops` | Queue, retry, resume, summary |
| Monitoring hemat token | cron `--no-agent`, scripts | Pesan Telegram hanya kalau ada temuan |

## Script radar

| Script | Tujuan |
|---|---|
| `waypoint_hot_mint_radar.sh` | HOT NFT live mint from Waypoint, with score + market/holder/dev/social checks |
| `x_nft_mint_radar_general.sh` | FREE / STEALTH / LIVE mint signals only |
| `x_nft_mint_radar_wl.sh` | WL / Allowlist / Whitelist / Early Access only |
| `x_nft_mint_radar.py` | Authenticated X keyword collector |
| `x_nft_mint_radar_format.py` | Telegram formatter |
| `waypoint_hot_mint_radar.py` | Waypoint WebSocket/API collector + formatter |

## Format output radar

### FREE / STEALTH / LIVE MINT

```text
🚨 NFT Mint Radar
Update HH:MM WIB • X

1. PROJECT / HANDLE
━━━━━━━━━━━━━━━━━━━━
🏷️ Free mint • ETH • 0 ETH
⚡ Info: FCFS • live now • wallet limit
⏰ schedule/deadline kalau kebaca
📝 Ringkasan tweet pendek
🔗 X Post
```

### WL / Allowlist / Early Access

```text
🧾 NFT WL / Allowlist Radar
Update HH:MM WIB • X

1. PROJECT / HANDLE
━━━━━━━━━━━━━━━━━━━━
🏷️ WL / Allowlist • ETH/Base/Solana
✅ Requirements: follow • like • repost • comment • form
⏰ deadline/snapshot kalau kebaca
📝 Ringkasan tweet pendek
🔗 X Post
```

### Waypoint HOT NFT

```text
🔥 HOT NFT Live Mint Update HH:MM WIB • Waypoint

1. PROJECT_NAME
━━━━━━━━━━━━━━━━━━━━
🟢 Mint Info
• Mint: ... mints / ... tx
• Price: 0 ETH
• Supply: ... / ...
• Status: New collection • Mintable • Live now

📊 Score
• NN/100 🟡 Medium
• Reason: some activity, free mint, mintable, verified contract

🔎 Project Check
• Project: X/website kalau ada, atau No X found

📜 Contract
• Contract: verified/unverified • ERC-721
• Deployer: 0x....…....
• Holders: ... holders • ... minters • top ...%
• Notes: warning penting

🔗 Links Waypoint • OpenSea • Website • X • Contract • Tx • DeployTx
```

Score guide:

```text
80–100 🔥 Strong
60–79 🟡 Medium
40–59 🟠 Speculative
0–39 🔴 Weak
```

## Telegram routing yang disarankan

Pisahkan topic supaya tidak campur:

```text
FREE / STEALTH / LIVE MINT    -> satu topic khusus
WL / Allowlist / Early Access -> topic WL sendiri
Waypoint HOT NFT Live Mint    -> topic live mint sendiri
Auto mint / execution logs    -> topic private/operator sendiri
Batch WL audit                -> topic private/operator sendiri
```

Lihat `cron/telegram-routing.md` dan `docs/03-telegram-gateway-and-cron.md` untuk template cron.

## Safety

- Repo ini **tidak** menyertakan private key, seed phrase, mnemonic, wallet password, X cookies, Telegram bot token, API key, atau `.env`.
- Script radar di repo ini untuk research/read-only. Tidak sign tx, tidak broadcast tx, tidak mint otomatis.
- Skill eksekusi mint/SeaDrop/Seaport/contract bisa membantu menyiapkan dan menjalankan flow kalau user menyediakan wallet/RPC yang valid; default aman adalah inspect → simulate → konfirmasi scope → execute.
- Auto fill WL batch harus menyimpan audit hasil submit: wallet, payload ringkas, response status, duplicate/fail reason, timestamp.
- Jangan commit file runtime seperti `.env`, `x-radar.env`, `auth.json`, `.xurl`, wallet JSON, seed phrase, atau encrypted wallet.
- Kalau pakai X radar, simpan cookie/token hanya di server lokal kamu: `~/.hermes/x-radar.env`, permission `chmod 600`.

## Tutorial lengkap

Baca berurutan:

1. `docs/01-install-hermes-agent.md`
2. `docs/02-install-nft-skills.md`
3. `docs/03-telegram-gateway-and-cron.md`
4. `docs/04-operating-the-agent.md`

## License

MIT. Gunakan, fork, dan modifikasi sesuai kebutuhan. Tetap DYOR sebelum connect wallet atau mint.
by Admin GANTENG
