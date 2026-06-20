# 00 — Tutorial Member: Bikin AI Agent Hermes + Pasang NFT Skill

Ini panduan paling ringkas untuk member group yang mau bikin AI agent sendiri dari nol, lalu pasang skill NFT/Web3 yang sudah kita pakai bareng.

## Hasil akhir yang kamu dapat

Setelah mengikuti tutorial ini, kamu punya:

- Hermes AI Agent jalan di server / VPS / laptop.
- Skill NFT/Web3 masuk ke agent.
- Script radar NFT siap dipakai.
- Telegram gateway bisa kirim update ke group/topic.
- Cron otomatis untuk:
  - FREE / STEALTH / LIVE MINT
  - WL / Allowlist / Early Access
  - Waypoint HOT NFT Live Mint

## 1. Siapkan server

Rekomendasi paling aman:

```text
OS: Ubuntu 22.04 / 24.04 atau Debian 12
RAM: 2 GB minimum, 4 GB lebih nyaman
Disk: 20 GB+
Akses: SSH + sudo
```

Update server:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git unzip python3 python3-venv build-essential
```

## 2. Install Hermes Agent

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc
```

Cek:

```bash
hermes --version
hermes doctor
```

Kalau Hermes minta fix dependency:

```bash
hermes doctor --fix
```

## 3. Setup model/provider

Jalankan wizard:

```bash
hermes setup
```

Atau kalau mau langsung pilih model:

```bash
hermes model
```

Pilih provider yang kamu punya, misalnya Nous Portal, OpenRouter, Anthropic, Google Gemini, atau custom OpenAI-compatible endpoint.

Test agent:

```bash
hermes chat -q "Halo, jawab singkat dalam bahasa Indonesia."
```

Kalau ada jawaban, berarti Hermes basic sudah jalan.

## 4. Enable tools penting

```bash
hermes tools enable terminal
hermes tools enable file
hermes tools enable web
hermes tools enable cronjob
hermes tools enable skills
hermes tools enable session_search
```

Cek:

```bash
hermes tools list
```

Restart session/gateway setelah enable tools kalau perlu.

## 5. Clone / download repo skill

Kalau dari GitHub:

```bash
git clone <REPO_URL>
cd hermes-nft-agent-skills
```

Kalau dari ZIP:

```bash
unzip hermes-nft-agent-skills.zip
cd hermes-nft-agent-skills
```

## 6. Install NFT skill pack

```bash
bash install/install.sh
```

Installer akan copy:

```text
skills/*  -> ~/.hermes/skills/
scripts/* -> ~/.hermes/scripts/
```

Cek skill:

```bash
hermes skills list | grep -E 'nft|web3|xurl|polymarket|blogwatcher|hermes-agent'
```

Cek script:

```bash
python3 -m py_compile \
  ~/.hermes/scripts/x_nft_mint_radar.py \
  ~/.hermes/scripts/x_nft_mint_radar_format.py \
  ~/.hermes/scripts/waypoint_hot_mint_radar.py
```

## 7. Cara pakai skill dari chat Hermes

Buka Hermes:

```bash
hermes
```

Load skill:

```text
/skill nft-auto-mint
/skill web3-ops
/skill xurl
```

Contoh command analisis:

```text
/watch 0xContractAddress
```

Atau:

```text
Analisis NFT mint ini: <link>
Cek score, mint activity, holder concentration, deployer wallet, contract, website/X/social, dan warning.
```

## 8. Setup X radar credential

X/Twitter radar butuh cookie/session dari akun kamu sendiri. Simpan lokal, jangan commit ke GitHub.

Buat file:

```bash
nano ~/.hermes/x-radar.env
```

Isi:

```bash
X_AUTH_TOKEN=isi_auth_token_x_kamu
X_CT0=isi_ct0_x_kamu
```

Kunci permission:

```bash
chmod 600 ~/.hermes/x-radar.env
```

Jangan pernah kirim isi file ini ke chat group.

## 9. Test radar manual

Preview tanpa ganggu dedupe:

```bash
~/.hermes/scripts/x_nft_mint_radar_format.py --mode general --limit 2 --no-dedupe
~/.hermes/scripts/x_nft_mint_radar_format.py --mode wl --limit 2 --no-dedupe
~/.hermes/scripts/waypoint_hot_mint_radar.py --preview --limit 2 --listen-seconds 8
```

Kalau output kosong, bisa normal: tidak ada signal baru atau source sedang kosong.

## 10. Setup Telegram gateway

Jalankan wizard:

```bash
hermes gateway setup
```

Pilih Telegram, masukkan bot token dari BotFather, lalu test:

```bash
hermes gateway run
```

Kalau sudah aman, install jadi service:

```bash
hermes gateway install
hermes gateway start
hermes gateway status
```

## 11. Ambil target Telegram topic

Format target topic:

```text
telegram:<chat_id>:<thread_id>
```

Contoh:

```text
telegram:-1001234567890:54012
```

Saran routing:

```text
FREE / STEALTH / LIVE MINT    -> thread khusus free/live/stealth
WL / Allowlist / Early Access -> thread WL sendiri
Waypoint HOT NFT Live Mint    -> thread live mint/high-signal sendiri
```

## 12. Pasang cron radar

FREE / STEALTH / LIVE:

```bash
hermes cron create 'every 10m' \
  --name 'X NFT Mint Radar — FREE/STEALTH/LIVE ONLY' \
  --script x_nft_mint_radar_general.sh \
  --no-agent \
  --deliver 'telegram:<chat_id>:<free_thread_id>'
```

WL / Allowlist:

```bash
hermes cron create 'every 10m' \
  --name 'X NFT WL/Allowlist/Early Access Radar' \
  --script x_nft_mint_radar_wl.sh \
  --no-agent \
  --deliver 'telegram:<chat_id>:<wl_thread_id>'
```

Waypoint HOT NFT:

```bash
hermes cron create 'every 10m' \
  --name 'Waypoint HOT NFT Live Mint Radar' \
  --script waypoint_hot_mint_radar.sh \
  --no-agent \
  --deliver 'telegram:<chat_id>:<waypoint_thread_id>'
```

Cek:

```bash
hermes cron list
hermes cron status
```

Run manual:

```bash
hermes cron run <job_id>
```

## 13. Best practice untuk group

- Jangan campur WL dengan FREE / LIVE mint.
- Jangan spam; cukup 1–3 item terbaik per update.
- Link dibuat horizontal dan rapi.
- Kalau X/website tidak ada, jangan ngarang.
- Score jangan tinggi hanya karena mint gratis.
- Cek real demand: volume, sales, offers/bids.
- Cek holder concentration dan dev wallet.
- Cek contract verified/unverified.
- Tetap DYOR sebelum connect wallet atau mint.

## 14. Troubleshooting cepat

### Hermes tidak kebaca setelah install

```bash
source ~/.bashrc
which hermes
hermes --version
```

### Skill belum muncul

```bash
bash install/install.sh
hermes skills list
```

Kalau di chat, mulai session baru:

```text
/reset
```

### Cron tidak kirim

```bash
hermes cron list
hermes cron status
```

Kalau stdout kosong, berarti script memang silent karena belum ada signal baru.

### Telegram salah thread

Edit deliver target:

```bash
hermes cron edit <job_id>
```

### X radar error auth

Cek file ada dan permission aman:

```bash
ls -l ~/.hermes/x-radar.env
chmod 600 ~/.hermes/x-radar.env
```

Isi ulang token X kalau expired.

## 15. Checklist selesai

- [ ] `hermes chat -q "Halo"` berhasil.
- [ ] `bash install/install.sh` berhasil.
- [ ] `hermes skills list` menampilkan skill NFT/Web3.
- [ ] `python3 -m py_compile ...` OK.
- [ ] Telegram gateway running.
- [ ] Cron jobs terdaftar.
- [ ] Radar terkirim ke topic yang benar.
