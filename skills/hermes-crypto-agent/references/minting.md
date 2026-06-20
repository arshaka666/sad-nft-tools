# Mint NFT

Cara mint NFT via direct contract call atau OpenSea Seaport drop.

## Daftar Isi

1. [Direct Contract Mint](#direct-contract-mint)
2. [OpenSea Seaport Drop (ERC721SeaDrop)](#opensea-seaport-drop-erc721seadrop)
3. [Hammer/Poll Auto-Mint](#hammerpoll-auto-mint)
4. [Safety Checklist](#safety-checklist)

---

## Direct Contract Mint

Untuk mint non-Seaport (contract biasa tanpa `onlyAllowedSeaDrop` modifier):

### Step 1: Deteksi Fungsi Mint

Gunakan web3.py `eth_call` untuk cek fungsi apa yang tersedia:

```python
from eth_utils import keccak

addr = w3.to_checksum_address(contract_addr)
wallet = w3.to_checksum_address(wallet_addr)

fungsi = [
    ('mint(uint256)', '0x1249c58b'),
    ('mint()', '0xefef39a1'),
    ('publicMint()', '0xd204c45e'),
    ('publicMint(uint256)', '0x3e169f07'),
    ('claim(uint256)', '0x3b4b1381'),
]

for name, sig in fungsi:
    try:
        result = w3.eth.call({'from': wallet, 'to': addr, 'data': sig + '0'*63+'1'})
        print(f'  {name}: exist')
    except:
        pass
```

### Step 2: Cek Harga & Supply

```python
# Cek balanceOf & totalSupply
bal = w3.eth.call({'to': addr, 'data': '0x70a08231' + wallet[2:].zfill(64)})
supply = w3.eth.call({'to': addr, 'data': '0x18160ddd'})

# Cek mint price — coba view functions
for name in ['mintPrice()', 'cost()', 'MINT_PRICE()', 'getMintPrice()']:
    sig = keccak(name.encode()).hex()[:8]
    try:
        result = w3.eth.call({'to': addr, 'data': '0x' + sig})
        price = w3.from_wei(int(result.hex(), 16), 'ether')
        print(f'{name}: {price} ETH')
    except:
        pass
```

### Step 3: Kirim TX

```python
tx = {
    'from': wallet,
    'to': addr,
    'data': mint_data,
    'value': w3.to_wei(mint_price_eth, 'ether'),
    'nonce': w3.eth.get_transaction_count(wallet),
    'gas': gas_limit,
    'gasPrice': w3.eth.gas_price,
    'chainId': w3.eth.chain_id,
}
signed = w3.eth.account.sign_transaction(tx, PK)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
```

---

## OpenSea Seaport Drop (ERC721SeaDrop)

Contract adalah ERC721SeaDrop proxy. Fungsi `mintSeaDrop(address,uint256)` punya modifier `onlyAllowedSeaDrop` (error code `0x15e26ff3`). GAK bisa dipanggil langsung — harus lewat OpenSea backend.

### Identifikasi

```python
sig = keccak(b'mintSeaDrop(address,uint256)').hex()[:8]
data = '0x' + sig + wallet[2:].zfill(64) + '0'*63 + '1'
try:
    w3.eth.call({'from': wallet, 'to': addr, 'data': data})
except Exception as e:
    if '15e26ff3' in str(e):
        print('Seaport drop (onlyAllowedSeaDrop)')
```

Ciri lain: fungsi `updatePublicDrop`, `updateAllowList`, `updateSignedMintValidationParams`.

### Workflow: OpenSea GraphQL (Zun2025 Method)

Dari artikel [@Zun2025](https://x.com/Zun2025/status/2037435538828063196):

```
[SIWE Auth] → cookies + x-app-id: os2-web
    ↓
[GraphQL swap(action:MINT)] → calldata + signature
    ↓
[Send tx langsung]
```

**Step 1: SIWE Auth**

```python
import requests, datetime

resp = requests.post('https://api.opensea.io/graphql/', json={
    'query': 'query { authSiweNonce { nonce } }'
}, headers={'x-app-id': 'os2-web', 'Content-Type': 'application/json'})
nonce = resp.json()['data']['authSiweNonce']['nonce']

# Sign message
message = f"opensea.io wants you to sign in with your account:\n{wallet}\n\n...\nURI: https://opensea.io/\nVersion: 1\nChain ID: 1\nNonce: {nonce}\nIssued At: {datetime.datetime.utcnow().isoformat()}Z"
signed = w3.eth.account.sign_message(encode_defunct(text=message), PK)

# Verify
verify_resp = requests.post('https://api.opensea.io/graphql/', json={
    'query': 'mutation { authSiweVerify(input: { message: "...", signature: "...", chainArch: "EVM", connectorId: "injected" }) { accessToken } }'
}, headers={'x-app-id': 'os2-web', 'Content-Type': 'application/json'})
```

**Kritis:**
- WAJIB header `x-app-id: os2-web`
- URI `https://opensea.io/` trailing slash
- Wallet lowercase, bukan checksum
- SIWE: `"wants you to sign in with your account:"` — BUKAN `"Ethereum account"`

**Step 2: swap(action: MINT)**

```graphql
query MintActionTimelineQuery {
  swap(input: { action: MINT, address: $address, chain: ETHEREUM, collectionSlug: $slug, quantity: 1 }) {
    transactionSubmissionData { target calldata value }
  }
}
```

Return: `target` (contract), `calldata`, `value`.

**Step 3: Batch Field Aliasing** — semua wallet dalam 1 query:

```graphql
query B {
  w0: swap(address: "0x...", collectionSlug: "...", quantity: 1) {
    transactionSubmissionData { target calldata value }
  }
  w1: swap(address: "0x...", ...) { ... }
}
```

1 HTTP round-trip, bukan N request.

### Timing Strategy (FCFS)

1. Polling `dropBySlug` tiap 30s — deteksi perubahan jadwal
2. Warm-up 5s before — pre-fetch nonce + chain ID + keepalive
3. Hammer endpoint 1.5s before — call `swap` sampai return data valid
4. Sign & send — cached nonce, jangan estimasi gas di hot path
5. Confirmation — `base_transactionStatus` (Unknown→Known→Preconfirmed)

**Region:** `gql.opensea.io` dan `mainnet-preconf.base.org` di Cloudflare IAD (Ashburn, VA). Dari AS: ~8ms ping. Dari Asia: 200-400ms — kalah.

---

## Hammer/Poll Auto-Mint

Untuk mint non-FCFS, poll sampe fungsi berhenti revert lalu fire tx langsung:

```python
while True:
    try:
        w3.eth.call({'from': wallet, 'to': addr, 'data': mint_data})
        # Mint open!
        gas_est = w3.eth.estimate_gas({'from': wallet, 'to': addr, 'data': mint_data})
        tx = {
            'from': wallet, 'to': addr, 'data': mint_data,
            'nonce': w3.eth.get_transaction_count(wallet),
            'gas': int(gas_est * 1.3), 'gasPrice': w3.eth.gas_price,
            'chainId': chain_id,
        }
        signed = w3.eth.account.sign_transaction(tx, PK)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        break
    except:
        time.sleep(3)
```

Update nonce & gas_price tiap 30s.

---

## Safety Checklist

- [ ] Verifikasi contract address
- [ ] Cek totalSupply vs maxSupply — jangan mint kalo sold out
- [ ] Cek balance wallet — cukup buat gas + mint price
- [ ] Simulasi `eth_call` dulu — jangan kirim tanpa test
- [ ] Hitung & tampilkan biaya gas
- [ ] Kalau `onlyAllowedSeaDrop` — jangan call mintSeaDrop langsung
- [ ] Gas limit: estimate * 1.3 buffer
- [ ] Tunggu receipt — `tx sent` ≠ success
