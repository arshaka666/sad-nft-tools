# NFT Transfer Between Own Wallets

## Overview

Transfer NFTs between your own Ethereum wallets using `safeTransferFrom` or `transferFrom`. Common use case: consolidate NFTs from secondary wallets into a primary/main wallet after multi-wallet minting.

## Prerequisites

- Private key of the **source** wallet (or ability to derive it)
- RPC endpoint (mainnet)
- Token ID of the NFT to transfer

## Multi-Wallet Consolidation (Full Workflow)

After minting with many wallets (e.g. 10 wallets each minting 1 NFT), consolidate them back to the main wallet.

### Step 0 — Find the Main Wallet Private Key

The main wallet key is NOT always under a predictable env var name. The safest approach is to scan all `PRIVATE_KEY=` entries in `/root/.hermes/.env`, derive each address, and match against the known main address:

```python
from web3 import Web3
from eth_account import Account
from pathlib import Path
import re

MAIN = Web3.to_checksum_address("0xprimary...wallet")  # REPLACE

env_text = Path("/root/.hermes/.env").read_text()
for m in re.finditer(r'PRIVATE_KEY\s*[:=]\s*[\'"]?(0x?[0-9a-fA-F]{64})', env_text):
    pk = m.group(1)
    pk = '0x' + pk if not pk.startswith('0x') else pk
    addr = Web3.to_checksum_address(Account.from_key(pk).address)
    if addr == MAIN:
        MAIN_PK = pk
        break
```

**Why this pattern:** The `.env` file may have `MAIN_WALLET_ADDRESS=` and `W1_ADDRESS=` pointing to different addresses. The `PRIVATE_KEY` value may derive to a different address than `W1_ADDRESS`. Always derive+compare against the known main address.

### Step 1 — Discover Which Wallets Still Own NFTs

Use `balanceOf` + `tokenOfOwnerByIndex` for each wallet:

```python
CONTRACT = "0x30f9EAF281975f1913AbF0aA222ca8EA0D8EF96B"
checksum = Web3.to_checksum_address(CONTRACT)
contract = w3.eth.contract(address=checksum, abi=abi)

minters = {
    "W14": "0x25C31746f06b49e5eC4B8692714cb927DCFe5DAC",
}

for name, addr in minters.items():
    chk = Web3.to_checksum_address(addr)
    bal = contract.functions.balanceOf(chk).call()
    if bal == 0:
        continue
    token_ids = []
    for i in range(bal):
        tid = contract.functions.tokenOfOwnerByIndex(chk, i).call()
        token_ids.append(tid)
    print(f"{name}: {token_ids}")
```

**RPC fallback (no contract/ABI):** Use raw `eth_call`:

```python
# balanceOf(address)
data = '0x70a08231' + '0'*24 + addr[2:].lower()
r = w3.eth.call({'to': contract_addr, 'data': data})
balance = int(r.hex(), 16)

# tokenOfOwnerByIndex(address, index) = 0x2f745c59
data_idx = '0x2f745c59' + '0'*24 + addr[2:].lower() + format(index, 'x').zfill(64)
r = w3.eth.call({'to': contract_addr, 'data': data_idx})
token_id = int(r.hex(), 16)

# ownerOf(tokenId) = 0x6352211e
data_owner = '0x6352211e' + format(token_id, 'x').zfill(64)
r = w3.eth.call({'to': contract_addr, 'data': data_owner})
owner = '0x' + r.hex()[-40:]
```

### Step 2 — Check Balance & Fund Gas If Needed

After minting, source wallets often have tiny remaining balances. Compute gas need and top up from main wallet:

```python
base_fee = w3.eth.gas_price
max_fee = base_fee + w3.to_wei(0.03, 'gwei')
priority = w3.to_wei(0.03, 'gwei')

est = contract.functions.transferFrom(chk, MAIN, tid).estimate_gas({'from': chk})
gas_limit = int(est * 1.25) + 5000
need = gas_limit * max_fee
bal = w3.eth.get_balance(chk)

if bal < need:
    topup = need - bal + w3.to_wei(0.000005, 'ether')
    nonce = w3.eth.get_transaction_count(MAIN, 'latest')
    tx = {
        'from': MAIN, 'to': chk, 'value': topup, 'nonce': nonce,
        'maxFeePerGas': base_fee + w3.to_wei(0.02, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(0.03, 'gwei'),
        'gas': 21000, 'chainId': 1,
    }
    signed = main_acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    rc = w3.eth.wait_for_transaction_receipt(h, timeout=120)
```

**CRITICAL nonce rule:** The child wallet receiving a topup does NOT change its nonce (it receives, it doesn't send). Always fetch the child's nonce *after* the topup confirms:

```python
# Wait for topup receipt, THEN get fresh nonce:
nonce_child = w3.eth.get_transaction_count(chk, 'latest')
```

Use `'latest'` (not `'pending'`) to avoid stale state from RPC nodes.

### Step 3 — Transfer the NFT

```python
nonce = w3.eth.get_transaction_count(chk)  # fresh nonce
tx = contract.functions.transferFrom(chk, MAIN, tid).build_transaction({
    'from': chk, 'nonce': nonce,
    'gas': gas_limit, 'chainId': 1,
    'maxFeePerGas': max_fee,
    'maxPriorityFeePerGas': w3.to_wei(0.03, 'gwei'),
})
signed = wallet_acct.sign_transaction(tx)
h = w3.eth.send_raw_transaction(signed.raw_transaction)
rc = w3.eth.wait_for_transaction_receipt(h, timeout=180)

if rc['status'] == 1:
    print(f"✅ Token #{tid} transferred! gasUsed={rc['gasUsed']}")
else:
    print(f"❌ Transfer failed!")
```

### Step 4 — Verify Ownership

```python
owner = contract.functions.ownerOf(tid).call()
if owner == MAIN:
    print(f"✅ Verified: token #{tid} at main wallet")
else:
    print(f"❌ Owner mismatch: {owner}")
```

**⚠️ RPC staleness:** Some public RPCs (publicnode.com) return stale data right after a block. If `ownerOf` returns the old address after a successful receipt, wait 1–2s and retry, or use a different RPC for verification.

### Step 5 — Final Count

```python
main_bal = contract.functions.balanceOf(MAIN).call()
print(f"Main wallet now owns {main_bal} tokens")
```

## Batch Processing Strategy

Scripts longer than ~2 minutes risk the 180s terminal timeout. When consolidating 10+ wallets, split into smaller batches:

1. **Run 1:** Check all balances + token IDs (fast eth_call only)
2. **Run 2:** Fund wallets needing topup (5-6 max per run)
3. **Run 3+:** Transfer NFTs (5-6 per run)

Each `wait_for_transaction_receipt` blocks ~12s+. For 10 wallets × 2 txs each (fund + transfer), wall time can exceed 240s. A single timeout kills all remaining unprocessed wallets.

**Recommended:** Separate funding from transfers across script runs.

## `transferFrom` vs `safeTransferFrom`

| Function | When to Use |
|----------|-------------|
| `safeTransferFrom(from, to, tokenId)` | Prefer this — checks receiver can handle ERC-721 |
| `transferFrom(from, to, tokenId)` | Fine for EOA-to-EOA consolidation |

## Sourcify API for ABI Fetching

```python
import requests, json
url = f'https://sourcify.dev/server/files/1/{CONTRACT}'
r = requests.get(url)
data = r.json()
for item in data:
    if item['name'] == 'metadata.json':
        meta = json.loads(item['content'])
        abi = meta['output']['abi']
        break
contract = w3.eth.contract(address=checksum, abi=abi)
```

Sourcify returns the full compilation metadata — parse `output.abi` from the `metadata.json` entry.

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ERC721IncorrectOwner` | Source wallet doesn't own token | Check `ownerOf(tokenId)` |
| `caller is not token owner or approved` | Wrong signing wallet | Use the wallet that OWNS the NFT |
| `Insufficient funds for gas * price + value` | Wallet ETH < gas cost | Send topup from main first (Step 2) |
| `Nonce too low` | Stale nonce from after topup | Fetch fresh nonce with 'latest' |
| ContractCustomError on `ownerOf()` | Token already transferred, or RPC stale | Use balanceOf instead or retry |

## Gas Costs

- Simple ERC-721 transfer: ~43k-48k gas
- Custom contracts (NodePunks, etc.): ~85k-100k gas
- At 0.15-0.20 gwei: ~$0.01-0.04 per transfer
- Topup (21000 gas flat): ~$0.006
