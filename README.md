# Hermes NFT Agent Skills

Skill + script pack untuk bikin **Hermes AI Agent** yang bisa monitor NFT/Web3 signal dan kirim update rapi ke Telegram group/topic.

Paket ini dibuat dari workflow yang sudah dipakai langsung di Hermes Agent untuk:

- **Waypoint HOT NFT live mint radar** — live mint baru dari Waypoint dengan score + contract/holder/social check.
- **X/Twitter FREE / STEALTH / LIVE mint radar** — hanya free mint, stealth mint/launch, live mint/mint live.
- **X/Twitter WL / Allowlist / Early Access radar** — dipisah dari live/free mint supaya thread tidak campur.
- **Web3/NFT research skills** — bantu analisis contract, deployer, holder concentration, real demand, market signal, dan mint risk.

Fokus paket ini bukan cuma “mint rame” atau “floor price tinggi”, tapi juga:

- volume / sales / offers
- holder concentration
- dev/deployer wallet holdings
- contract verification
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
hermes skills list | grep -E 'nft|web3|xurl|polymarket|blogwatcher|hermes-agent'
python3 -m py_compile scripts/x_nft_mint_radar.py scripts/x_nft_mint_radar_format.py scripts/waypoint_hot_mint_radar.py
```

### 4. Pakai skill di Hermes

Di chat Hermes:

```text
/skill nft-auto-mint
/skill web3-ops
/skill xurl
```

Contoh request:

```text
/watch 0xContractAddress
```

Atau:

```text
Analisis mint NFT ini: <link mint / OpenSea / contract>
Cek score, holder concentration, deployer wallet, contract, market demand, website/X, dan warning.
```

### 5. Setup Telegram gateway + cron radar

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
| `nft-auto-mint` | NFT mint workflow, Waypoint HOT radar notes, safety checks |
| `web3-ops` | On-chain read/simulation patterns, deployer/holder/token checks |
| `hermes-crypto-agent` | Crypto/Web3 agent toolkit |
| `universal-minter` | General minting patterns and contract interaction references |
| `nft-wl-filler` | WL / allowlist form workflow references |
| `batch-ops` | Batch operation patterns |
| `xurl` | X/Twitter CLI workflow references |
| `polymarket` | Market query skill |
| `blogwatcher` | Feed monitoring skill |
| `hermes-agent` | Hermes setup/config/gateway/cron reference |

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
```

Lihat `cron/telegram-routing.md` dan `docs/03-telegram-gateway-and-cron.md` untuk template cron.

## Safety

- Repo ini **tidak** menyertakan private key, seed phrase, mnemonic, wallet password, X cookies, Telegram bot token, API key, atau `.env`.
- Script radar di repo ini untuk research/read-only. Tidak sign tx, tidak broadcast tx, tidak mint otomatis.
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
