# 02 — Install NFT/Web3 Skills

Setelah Hermes jalan, install skill pack ini.

## 1. Clone repo skill

```bash
git clone <REPO_URL>
cd hermes-nft-agent-skills
```

Kalau download ZIP:

```bash
unzip hermes-nft-agent-skills.zip
cd hermes-nft-agent-skills
```

## 2. Jalankan installer

```bash
bash install/install.sh
```

Installer akan copy:

```text
skills/*  -> ~/.hermes/skills/
scripts/* -> ~/.hermes/scripts/
```

## 3. Cek skill sudah masuk

```bash
hermes skills list | grep -E 'nft|web3|xurl|polymarket|blogwatcher'
```

Atau dari chat Hermes:

```text
/skills
/skill nft-auto-mint
/skill web3-ops
```

## 4. Cek script radar

```bash
ls -la ~/.hermes/scripts/*radar*
python3 -m py_compile \
  ~/.hermes/scripts/x_nft_mint_radar.py \
  ~/.hermes/scripts/x_nft_mint_radar_format.py \
  ~/.hermes/scripts/waypoint_hot_mint_radar.py
```

Test formatter tanpa dedupe:

```bash
~/.hermes/scripts/x_nft_mint_radar_format.py --mode wl --limit 1 --no-dedupe
~/.hermes/scripts/x_nft_mint_radar_format.py --mode general --limit 1 --no-dedupe
~/.hermes/scripts/waypoint_hot_mint_radar.py --preview --limit 1 --listen-seconds 8
```

Catatan:

- X radar butuh cookies/session X yang disimpan lokal di `~/.hermes/x-radar.env`.
- Waypoint radar pakai public WebSocket/API dan Blockscout/OpenSea public data.

## 5. Setup X radar credential

Buat file lokal:

```bash
nano ~/.hermes/x-radar.env
```

Isi manual di server kamu:

```bash
X_AUTH_TOKEN=isi_auth_token_x_kamu
X_CT0=isi_ct0_x_kamu
```

Kunci permission:

```bash
chmod 600 ~/.hermes/x-radar.env
```

Jangan commit file ini ke GitHub.

## 6. Skill yang biasa dipakai

Untuk NFT monitoring:

```text
nft-auto-mint
web3-ops
xurl
polymarket
blogwatcher
```

Untuk Hermes setup:

```text
hermes-agent
```

## 7. Next step

Lanjut ke:

```text
docs/03-telegram-gateway-and-cron.md
```
