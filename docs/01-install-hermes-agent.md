# 01 — Install Hermes Agent dari Nol

Panduan ini untuk member yang ingin bikin AI agent sendiri pakai Hermes.

## 1. Siapkan server / VPS

Rekomendasi minimal:

```text
OS: Ubuntu 22.04 / 24.04 atau Debian 12
RAM: 2 GB minimum, 4 GB lebih nyaman
Disk: 20 GB+
Akses: SSH + user sudo
```

Update server:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git unzip python3 python3-venv build-essential
```

## 2. Install Hermes Agent

Linux / macOS / WSL:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc
```

Cek install:

```bash
hermes --version
hermes doctor
```

Kalau ada dependency yang kurang, jalankan:

```bash
hermes doctor --fix
```

## 3. Setup model/provider

Jalankan wizard:

```bash
hermes setup
```

Atau langsung pilih model/provider:

```bash
hermes model
```

Pilih provider yang kamu punya. Contoh:

- Nous Portal
- OpenRouter
- Anthropic
- OpenAI-compatible/custom endpoint
- Google Gemini
- local/custom provider

> Tips: pastikan chat basic jalan dulu sebelum setup Telegram/cron.

Test:

```bash
hermes chat -q "Halo, jawab singkat."
```

Kalau agent bisa jawab, lanjut.

## 4. Enable toolsets yang dibutuhkan

Untuk Web3/NFT radar, minimal butuh:

```bash
hermes tools enable terminal
hermes tools enable file
hermes tools enable web
hermes tools enable cronjob
hermes tools enable skills
```

Cek:

```bash
hermes tools list
```

Setelah enable tools, restart session/gateway kalau perlu.

## 5. Struktur penting Hermes

```text
~/.hermes/config.yaml       config utama
~/.hermes/.env              API keys / secrets
~/.hermes/skills/           skill lokal
~/.hermes/scripts/          script radar/custom automation
~/.hermes/cron/             cron job config/output
~/.hermes/logs/             logs gateway/error
```

Jangan share `.env`, `auth.json`, `.xurl`, cookies, private key, seed phrase, atau token.

## 6. Next step

Lanjut ke:

```text
docs/02-install-nft-skills.md
```
