# 02 — Install NFT/Web3 Skills

Setelah Hermes jalan, install skill pack ini. Isi pack bukan cuma radar, tapi juga auto mint contract, SeaDrop/Seaport-style flow, universal minter, auto fill WL batch, batch ops, dan Web3 research/ops.

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
hermes skills list | grep -E 'nft|web3|xurl|polymarket|blogwatcher|batch|universal'
```

Atau dari chat Hermes:

```text
/skills
/skill nft-auto-mint
/skill universal-minter
/skill nft-wl-filler
/skill batch-ops
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
- Untuk eksekusi mint/contract write, agent tetap butuh wallet/RPC lokal yang valid dan harus inspect/simulate dulu.
- Untuk auto fill WL batch, simpan audit CSV/JSON supaya hasil 100 wallet atau lebih bisa dicek ulang.

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

Untuk radar / monitoring:

```text
xurl
nft-auto-mint
web3-ops
polymarket
blogwatcher
```

Untuk auto mint contract / marketplace flow:

```text
nft-auto-mint
universal-minter
web3-ops
hermes-crypto-agent
```

Untuk auto fill WL / allowlist batch:

```text
nft-wl-filler
batch-ops
xurl
```

Untuk Web3 batch ops dan riset on-chain:

```text
web3-ops
batch-ops
hermes-crypto-agent
```

Untuk Hermes setup:

```text
hermes-agent
```

## 7. Contoh request setelah install

```text
Mint NFT dari contract ini: 0xContractAddress
Cek ABI/source, mint function, price, max supply, wallet limit, simulate dulu, lalu eksekusi kalau aman.
```

```text
Cek mint/claim/listing NFT ini dari OpenSea/SeaDrop/Seaport flow.
Validasi order/contract/value/approval, simulate, lalu siapkan tx kalau aman.
```

```text
Isi WL form/site ini pakai 100 wallet.
Reverse engineer field/backend, generate username/comment/proof random kalau perlu, submit batch, lalu kasih audit CSV/JSON.
```

## 8. Next step

Lanjut ke:

```text
docs/03-telegram-gateway-and-cron.md
```
